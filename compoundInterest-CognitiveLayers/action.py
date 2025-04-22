from typing import Dict, Any, List, Optional
from models import ActionInput, ActionOutput
import mcp
from mcp import ClientSession, types
from mcp.server.fastmcp import FastMCP
import os
from dotenv import load_dotenv
import asyncio
import json
import threading
import time
import uvicorn

load_dotenv()

# Create MCP server instance
mcp_server = FastMCP("CompoundInterestAgent", debug=True)

# Define tools
@mcp_server.tool()
def calculate_quarterly_rate(annual_rate: float) -> float:
    """Calculate the quarterly interest rate from annual rate"""
    return float(annual_rate / 4)

@mcp_server.tool()
def calculate_compounding_periods(years: int) -> int:
    """Calculate the number of compounding periods for quarterly compounding"""
    return int(years * 4)

@mcp_server.tool()
def calculate_compound_interest(principal: float, rate: float, periods: int) -> float:
    """Calculate compound interest using the formula A = P(1 + r)^n"""
    # The formula for compound interest is A = P(1 + r)^n
    # where A is the final amount, P is the principal, r is the rate per period, and n is the number of periods
    result = principal * (1 + rate) ** periods
    print(f"Compound interest calculation: {principal} * (1 + {rate})^{periods} = {result}")
    return float(result)

@mcp_server.tool()
def calculate_bonus(principal: float, bonus_rate: float) -> float:
    """Calculate bonus amount on principal"""
    return float(principal * bonus_rate)

@mcp_server.tool()
def verify_calculation(final_amount: float, principal: float) -> bool:
    """Verify that the final amount is greater than the principal"""
    return bool(final_amount > principal)

@mcp_server.tool()
def verify_quarterly_rate(quarterly_rate: float, annual_rate: float) -> bool:
    """Verify that quarterly rate is less than annual rate"""
    return bool(quarterly_rate < annual_rate)

@mcp_server.tool()
def verify_compounding_periods(periods: int, years: int) -> bool:
    """Verify that the number of compounding periods is correct"""
    return bool(periods == years * 4)

class Action:
    def __init__(self):
        # For local development, use a default key if not provided
        self.api_key = os.getenv("MCP_API_KEY", "local_dev_key")
        self.base_url = os.getenv("MCP_BASE_URL", "http://localhost:8000")  # Default to local server
        self.client = None
        self.available_tools = {}
        self.is_local = self.base_url.startswith("http://localhost") or self.base_url.startswith("http://127.0.0.1")
        
    async def initialize(self):
        """Initialize the MCP client and get available tools"""
        try:
            # Initialize the MCP client
            if self.is_local:
                print(f"Connecting to local MCP server...")
            else:
                print(f"Connecting to MCP server at {self.base_url}")
                
            print("Getting available tools...")
            # Get available tools directly from the MCP server
            self.available_tools = {
                tool.name: tool.description
                for tool in await mcp_server.list_tools()
            }
            print("Successfully connected to MCP server")
            return True
                
        except Exception as e:
            print(f"Error initializing MCP client: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            await self.cleanup()
            return False
            
    async def cleanup(self):
        """Cleanup resources"""
        try:
            if self.client:
                await self.client.close()
        except Exception as e:
            print(f"Error during cleanup: {e}")
            
    def __del__(self):
        """Cleanup when the object is destroyed"""
        try:
            if self.client:
                # Create a new event loop for cleanup
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.cleanup())
                loop.close()
        except Exception as e:
            print(f"Error during cleanup in __del__: {e}")
            
    async def _get_available_tools(self) -> Dict[str, Any]:
        """Get list of available MCP tools and their descriptions"""
        try:
            # Get the actual tools from the MCP server
            tools = await mcp_server.list_tools()
            return {tool.name: tool.description for tool in tools}
        except Exception as e:
            print(f"Error getting available tools: {e}")
            return {}
        
    async def execute(self, input_data: ActionInput) -> ActionOutput:
        """
        Execute the decided action using MCP tools
        """
        try:
            if not input_data.decision.tool_name:
                return ActionOutput(
                    success=True,
                    result={"message": "No tool execution needed"},
                    error=None
                )
            
            # Check if the tool exists
            if input_data.decision.tool_name not in self.available_tools:
                return ActionOutput(
                    success=False,
                    result={},
                    error=f"Tool '{input_data.decision.tool_name}' not found"
                )
            
            # Execute the tool with the provided arguments using the MCP server
            print(f"Executing tool: {input_data.decision.tool_name} with args: {input_data.decision.tool_args}")
            
            # Convert tool args to the format expected by MCP
            tool_args = {}
            for key, value in input_data.decision.tool_args.items():
                # Convert string values to appropriate types
                if isinstance(value, str):
                    try:
                        # Try to convert to float first
                        tool_args[key] = float(value)
                    except ValueError:
                        try:
                            # Try to convert to int
                            tool_args[key] = int(value)
                        except ValueError:
                            # Keep as string if conversion fails
                            tool_args[key] = value
                else:
                    tool_args[key] = value
            
            # Special handling for calculate_compound_interest
            if input_data.decision.tool_name == "calculate_compound_interest":
                try:
                    calculation_history = []
                    
                    # First calculate the quarterly rate
                    print("Calculating quarterly rate...")
                    # Convert interest rate from percentage to decimal if needed
                    annual_rate = tool_args.get("interest_rate", tool_args.get("annual_rate", 0))
                    if annual_rate > 1:  # If rate is in percentage form
                        annual_rate = annual_rate / 100
                    
                    # If rate is already provided in the tool_args, use it directly
                    if "rate" in tool_args:
                        quarterly_rate = float(tool_args["rate"])
                        print(f"Using provided quarterly rate: {quarterly_rate}")
                    else:
                        # Otherwise calculate it from the annual rate
                        quarterly_rate_result = await mcp_server.call_tool(
                            name="calculate_quarterly_rate",
                            arguments={"annual_rate": annual_rate}
                        )
                        quarterly_rate = float(quarterly_rate_result[0].text)
                        print(f"Quarterly rate calculated: {quarterly_rate}")
                    
                    calculation_history.append({
                        "function": "calculate_quarterly_rate",
                        "args": {"annual_rate": annual_rate},
                        "result": quarterly_rate
                    })
                    
                    # Verify quarterly rate
                    print("Verifying quarterly rate...")
                    verify_rate_result = await mcp_server.call_tool(
                        name="verify_quarterly_rate",
                        arguments={
                            "quarterly_rate": quarterly_rate,
                            "annual_rate": annual_rate
                        }
                    )
                    calculation_history.append({
                        "function": "verify_quarterly_rate",
                        "args": {
                            "quarterly_rate": quarterly_rate,
                            "annual_rate": annual_rate
                        },
                        "result": bool(verify_rate_result[0].text)
                    })
                    
                    # Then calculate the total number of periods
                    print("Calculating compounding periods...")
                    
                    # If periods is already provided in the tool_args, use it directly
                    if "periods" in tool_args:
                        periods = int(tool_args["periods"])
                        print(f"Using provided periods: {periods}")
                    else:
                        # Otherwise calculate it from the years
                        years = tool_args.get("years", tool_args.get("compounding_periods", 0) // 4)
                        periods_result = await mcp_server.call_tool(
                            name="calculate_compounding_periods",
                            arguments={"years": years}
                        )
                        periods = int(periods_result[0].text)
                        print(f"Compounding periods calculated: {periods}")
                    
                    calculation_history.append({
                        "function": "calculate_compounding_periods",
                        "args": {"years": tool_args.get("years", tool_args.get("compounding_periods", 0) // 4)},
                        "result": periods
                    })
                    
                    # Verify compounding periods
                    print("Verifying compounding periods...")
                    verify_periods_result = await mcp_server.call_tool(
                        name="verify_compounding_periods",
                        arguments={
                            "periods": periods,
                            "years": tool_args.get("years", tool_args.get("compounding_periods", 0) // 4)
                        }
                    )
                    calculation_history.append({
                        "function": "verify_compounding_periods",
                        "args": {
                            "periods": periods,
                            "years": tool_args.get("years", tool_args.get("compounding_periods", 0) // 4)
                        },
                        "result": bool(verify_periods_result[0].text)
                    })
                    
                    # Now call calculate_compound_interest with the correct arguments
                    print("Calculating compound interest...")
                    result = await mcp_server.call_tool(
                        name="calculate_compound_interest",
                        arguments={
                            "principal": tool_args.get("principal", 0),
                            "rate": quarterly_rate,
                            "periods": periods
                        }
                    )
                    final_amount = float(result[0].text)
                    print(f"Compound interest calculated: {final_amount}")
                    calculation_history.append({
                        "function": "calculate_compound_interest",
                        "args": {
                            "principal": tool_args.get("principal", 0),
                            "rate": quarterly_rate,
                            "periods": periods
                        },
                        "result": final_amount
                    })
                    
                    # Verify the calculation
                    print("Verifying calculation...")
                    verify_calc_result = await mcp_server.call_tool(
                        name="verify_calculation",
                        arguments={
                            "final_amount": final_amount,
                            "principal": tool_args.get("principal", 0)
                        }
                    )
                    calculation_history.append({
                        "function": "verify_calculation",
                        "args": {
                            "final_amount": final_amount,
                            "principal": tool_args.get("principal", 0)
                        },
                        "result": bool(verify_calc_result[0].text)
                    })

                    # Calculate bonus if requested
                    bonus_amount = 0
                    if "bonus_rate" in tool_args:
                        print("Calculating bonus...")
                        # Convert bonus rate from percentage to decimal if needed
                        bonus_rate = tool_args.get("bonus_rate", 0)
                        if bonus_rate > 1:  # If rate is in percentage form
                            bonus_rate = bonus_rate / 100
                        bonus_result = await mcp_server.call_tool(
                            name="calculate_bonus",
                            arguments={
                                "principal": tool_args.get("principal", 0),
                                "bonus_rate": bonus_rate
                            }
                        )
                        bonus_amount = float(bonus_result[0].text)
                        print(f"Bonus calculated: {bonus_amount}")
                        calculation_history.append({
                            "function": "calculate_bonus",
                            "args": {
                                "principal": tool_args.get("principal", 0),
                                "bonus_rate": bonus_rate
                            },
                            "result": bonus_amount
                        })
                        result = {
                            "final_amount": final_amount,
                            "bonus_amount": bonus_amount,
                            "total_amount": final_amount + bonus_amount,
                            "calculation_history": calculation_history
                        }
                    else:
                        result = {
                            "final_amount": final_amount,
                            "calculation_history": calculation_history
                        }
                    print(f"Final result: {result}")
                except Exception as e:
                    import traceback
                    error_details = traceback.format_exc()
                    print(f"Detailed error in compound interest calculation: {error_details}")
                    raise Exception(f"Error in compound interest calculation: {str(e)}\n{error_details}")
            else:
                # Execute other tools normally
                # Extract years from time_period if it's in the format "X years"
                if "time_period" in tool_args and isinstance(tool_args["time_period"], str):
                    try:
                        years = int(tool_args["time_period"].split()[0])
                        tool_args["years"] = years
                        del tool_args["time_period"]
                    except (ValueError, IndexError):
                        pass
                
                # Remove any arguments that are not expected by the tool
                result_obj = await mcp_server.call_tool(
                    name=input_data.decision.tool_name,
                    arguments=tool_args
                )
                
                # Extract the actual value from the TextContent object
                if isinstance(result_obj, list) and len(result_obj) > 0:
                    result = {"result": result_obj[0].text}
                else:
                    result = {"result": result_obj}
            
            print(f"Tool execution result: {result}")
            return ActionOutput(
                success=True,
                result=result,
                error=None
            )
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Detailed error executing tool: {error_details}")
            return ActionOutput(
                success=False,
                result={},
                error=f"{str(e)}\n{error_details}"
            )
    
    async def _simulate_tool_execution(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate the execution of an MCP tool"""
        # This is a placeholder - in a real implementation, you would
        # use the MCP client to execute the actual tool
        if tool_name == "calculate_quarterly_rate":
            annual_rate = tool_args.get("annual_rate", 0)
            return {"quarterly_rate": annual_rate / 4}
        
        elif tool_name == "calculate_compounding_periods":
            years = tool_args.get("years", 0)
            return {"periods": years * 4}
        
        elif tool_name == "calculate_compound_interest":
            principal = tool_args.get("principal", 0)
            rate = tool_args.get("rate", 0)
            periods = tool_args.get("periods", 0)
            return {"final_amount": principal * (1 + rate) ** periods}
        
        elif tool_name == "calculate_bonus":
            principal = tool_args.get("principal", 0)
            bonus_rate = tool_args.get("bonus_rate", 0)
            return {"bonus_amount": principal * bonus_rate}
        
        elif tool_name == "verify_calculation":
            final_amount = tool_args.get("final_amount", 0)
            principal = tool_args.get("principal", 0)
            return {"is_correct": abs(final_amount - principal) > 0}
        
        elif tool_name == "verify_quarterly_rate":
            quarterly_rate = tool_args.get("quarterly_rate", 0)
            annual_rate = tool_args.get("annual_rate", 0)
            return {"is_correct": abs(quarterly_rate - annual_rate / 4) < 0.0001}
        
        elif tool_name == "verify_compounding_periods":
            periods = tool_args.get("periods", 0)
            years = tool_args.get("years", 0)
            return {"is_correct": periods == years * 4}
        
        else:
            return {"message": f"Tool '{tool_name}' executed with args: {tool_args}"} 