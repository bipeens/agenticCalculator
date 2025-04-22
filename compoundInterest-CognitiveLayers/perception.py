import google.generativeai as genai
from typing import Dict, Any, Tuple
from models import PerceptionInput, PerceptionOutput
import os
from dotenv import load_dotenv
import json
import asyncio
from concurrent.futures import TimeoutError
import re

load_dotenv()

class Perception:
    def __init__(self):
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.mcp_server = None
        
    async def initialize(self):
        """Initialize the MCP server"""
        try:
            from mcp.server.fastmcp import FastMCP
            self.mcp_server = FastMCP("CompoundInterestAgent", debug=True)
            return True
        except Exception as e:
            print(f"Error initializing MCP server: {e}")
            return False
        
    async def process_input(self, input_data: PerceptionInput) -> PerceptionOutput:
        """
        Process user input and generate perception output using LLM
        """
        # First, verify the prompt
        is_valid, validation_message = await self.verify_prompt(input_data.user_input)
        
        if not is_valid:
            return PerceptionOutput(
                processed_input=input_data.user_input,
                intent="invalid_input",
                entities={"error": validation_message},
                confidence=0.0
            )
        
        # Special handling for compound interest calculations
        if "compound interest" in input_data.user_input.lower():
            # Extract parameters from the input
            
            # Extract principal amount
            principal_match = re.search(r'\$?(\d+(?:,\d{3})*(?:\.\d{2})?)', input_data.user_input)
            principal = float(principal_match.group(1).replace(',', '')) if principal_match else 10000.0
            
            # Extract interest rate
            rate_match = re.search(r'(\d+(?:\.\d+)?)%', input_data.user_input)
            interest_rate = float(rate_match.group(1))/100 if rate_match else 0.045
            
            # Extract years
            years_match = re.search(r'(\d+)\s*years?', input_data.user_input)
            years = int(years_match.group(1)) if years_match else 5
            
            # Extract bonus rate
            bonus_match = re.search(r'bonus\s*of\s*(\d+(?:\.\d+)?)%', input_data.user_input)
            bonus_rate = float(bonus_match.group(1))/100 if bonus_match else 0.005
            
            # Print extracted values for debugging
            print(f"Extracted values: principal={principal}, interest_rate={interest_rate}, years={years}, bonus_rate={bonus_rate}")
            
            return PerceptionOutput(
                processed_input=input_data.user_input,
                intent="calculate_compound_interest",
                entities={
                    "principal": principal,
                    "interest_rate": interest_rate,
                    "years": years,
                    "bonus_rate": bonus_rate
                },
                confidence=1.0
            )
        
        # Prepare the prompt for the LLM
        prompt = f"""
        Analyze the following user input and provide:
        1. The processed/cleaned input
        2. The user's intent
        3. Any important entities mentioned
        4. Your confidence in this analysis (0.0 to 1.0)

        User input: {input_data.user_input}
        Context: {input_data.context}

        Respond in the following JSON format:
        {{
            "processed_input": "cleaned input text",
            "intent": "main intent of the user",
            "entities": {{"entity_type": "value"}},
            "confidence": 0.95
        }}
        """
        
        try:
            # Get response from LLM with timeout
            response = await self.generate_with_timeout(prompt)
            response_text = response.text
            
            # Parse the response (assuming it's in JSON format)
            try:
                result = json.loads(response_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, try to extract JSON from the text
                try:
                    # Find JSON-like structure in the text
                    start_idx = response_text.find('{')
                    end_idx = response_text.rfind('}') + 1
                    if start_idx >= 0 and end_idx > start_idx:
                        json_str = response_text[start_idx:end_idx]
                        result = json.loads(json_str)
                    else:
                        raise ValueError("No JSON found in response")
                except Exception as e:
                    print(f"Error parsing LLM response: {e}")
                    # Create a basic result
                    result = {
                        "processed_input": input_data.user_input,
                        "intent": "unknown",
                        "entities": {},
                        "confidence": 0.5
                    }
            
            return PerceptionOutput(
                processed_input=result["processed_input"],
                intent=result["intent"],
                entities=result["entities"],
                confidence=result["confidence"]
            )
            
        except Exception as e:
            # In case of error, return a basic perception output
            return PerceptionOutput(
                processed_input=input_data.user_input,
                intent="unknown",
                entities={"error": str(e)},
                confidence=0.0
            )
    
    async def verify_prompt(self, query: str) -> Tuple[bool, str]:
        """
        Verify if the prompt is valid and safe to process
        """
        try:
            # Check for empty or too short queries
            if not query or len(query.strip()) < 3:
                return False, "Query is too short. Please provide more details."
            
            # Check for potentially harmful content
            harmful_keywords = ["delete", "drop", "remove", "kill", "crash", "hack", "exploit"]
            for keyword in harmful_keywords:
                if keyword in query.lower():
                    return False, f"Query contains potentially harmful keyword: '{keyword}'"
            
            # Check for system commands
            if query.startswith("!") or query.startswith("/"):
                return False, "System commands are not allowed in this context."
            
            # If all checks pass, the prompt is valid
            return True, "Prompt is valid."
            
        except Exception as e:
            return False, f"Error verifying prompt: {str(e)}"
    
    async def generate_with_timeout(self, prompt: str, timeout: int = 10) -> Any:
        """Generate content with a timeout"""
        try:
            # Convert the synchronous generate_content call to run in a thread
            loop = asyncio.get_event_loop()
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None, 
                    lambda: self.model.generate_content(prompt)
                ),
                timeout=timeout
            )
            return response
        except TimeoutError:
            print("LLM generation timed out!")
            raise
        except Exception as e:
            print(f"Error in LLM generation: {e}")
            raise 

    async def execute(self, input_data: PerceptionInput) -> PerceptionOutput:
        """
        Execute the decided action using MCP tools
        """
        try:
            if not self.mcp_server:
                await self.initialize()
                if not self.mcp_server:
                    return PerceptionOutput(
                        processed_input=input_data.user_input,
                        intent="error",
                        entities={"error": "MCP server not initialized"},
                        confidence=0.0
                    )
            
            if not input_data.decision.tool_name:
                return PerceptionOutput(
                    processed_input=input_data.user_input,
                    intent="no_action",
                    entities={},
                    confidence=1.0
                )
            
            # Execute the tool with the provided arguments
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
                calculation_history = []
                
                # First calculate the quarterly rate
                print("Calculating quarterly rate...")
                quarterly_rate_result = await self.mcp_server.call_tool(
                    name="calculate_quarterly_rate",
                    arguments={"annual_rate": tool_args.get("interest_rate", tool_args.get("annual_rate", 0))}
                )
                quarterly_rate = float(quarterly_rate_result[0].text)
                print(f"Quarterly rate calculated: {quarterly_rate}")
                calculation_history.append({
                    "function": "calculate_quarterly_rate",
                    "args": {"annual_rate": tool_args.get("interest_rate", tool_args.get("annual_rate", 0))},
                    "result": quarterly_rate
                })
                
                # Verify quarterly rate
                print("Verifying quarterly rate...")
                verify_rate_result = await self.mcp_server.call_tool(
                    name="verify_quarterly_rate",
                    arguments={
                        "quarterly_rate": quarterly_rate,
                        "annual_rate": tool_args.get("interest_rate", tool_args.get("annual_rate", 0))
                    }
                )
                calculation_history.append({
                    "function": "verify_quarterly_rate",
                    "args": {
                        "quarterly_rate": quarterly_rate,
                        "annual_rate": tool_args.get("interest_rate", tool_args.get("annual_rate", 0))
                    },
                    "result": bool(verify_rate_result[0].text)
                })
                
                # Then calculate the total number of periods
                print("Calculating compounding periods...")
                periods_result = await self.mcp_server.call_tool(
                    name="calculate_compounding_periods",
                    arguments={"years": tool_args.get("years", tool_args.get("compounding_periods", 0) // 4)}
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
                verify_periods_result = await self.mcp_server.call_tool(
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
                result = await self.mcp_server.call_tool(
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
                verify_calc_result = await self.mcp_server.call_tool(
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
                    bonus_result = await self.mcp_server.call_tool(
                        name="calculate_bonus",
                        arguments={
                            "principal": tool_args.get("principal", 0),
                            "bonus_rate": tool_args.get("bonus_rate", 0)
                        }
                    )
                    bonus_amount = float(bonus_result[0].text)
                    print(f"Bonus calculated: {bonus_amount}")
                    calculation_history.append({
                        "function": "calculate_bonus",
                        "args": {
                            "principal": tool_args.get("principal", 0),
                            "bonus_rate": tool_args.get("bonus_rate", 0)
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
                
                return PerceptionOutput(
                    processed_input=input_data.user_input,
                    intent="calculate_compound_interest",
                    entities=result,
                    confidence=1.0
                )
            else:
                # Execute other tools normally
                result_obj = await self.mcp_server.call_tool(
                    name=input_data.decision.tool_name,
                    arguments=tool_args
                )
                
                # Extract the actual value from the TextContent object
                if isinstance(result_obj, list) and len(result_obj) > 0:
                    result = {"result": result_obj[0].text}
                else:
                    result = {"result": result_obj}
                
                return PerceptionOutput(
                    processed_input=input_data.user_input,
                    intent=input_data.decision.tool_name,
                    entities=result,
                    confidence=1.0
                )
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Detailed error executing tool: {error_details}")
            return PerceptionOutput(
                processed_input=input_data.user_input,
                intent="error",
                entities={"error": str(e), "details": error_details},
                confidence=0.0
            )