import google.generativeai as genai
from typing import List, Dict, Any, Tuple
from models import DecisionInput, DecisionOutput, UserPreference
import os
from dotenv import load_dotenv
import json
import asyncio
from concurrent.futures import TimeoutError

load_dotenv()

class DecisionMaking:
    def __init__(self, user_preference: UserPreference):
        self.user_preference = user_preference
        self.api_key = os.getenv("GEMINI_API_KEY")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.max_iterations = 15
        self.iteration = 0
        self.completed_steps = set()
        self.execution_plan = []
        self.current_step_index = 0
        
    async def make_decision(self, input_data: DecisionInput) -> DecisionOutput:
        """
        Make a decision based on perception and memory
        """
        # Increment iteration counter
        self.iteration += 1
        
        # Check if we've reached the maximum number of iterations
        if self.iteration > self.max_iterations:
            return DecisionOutput(
                next_action="max_iterations_reached",
                tool_name=None,
                tool_args={},
                reasoning="Maximum number of iterations reached. Stopping to prevent infinite loops."
            )
        
        # Special handling for compound interest calculations
        if "compound interest" in input_data.perception.processed_input.lower():
            # If we don't have an execution plan yet, create one
            if not self.execution_plan:
                # Extract parameters from the input
                entities = input_data.perception.entities
                if isinstance(entities, dict):
                    # Get the values from entities with defaults
                    principal = entities.get("principal", 10000.0)
                    interest_rate = entities.get("interest_rate", 0.045)
                    years = entities.get("years", 5)
                    bonus_rate = entities.get("bonus_rate", 0.005)
                    
                    # Create a structured execution plan
                    self.execution_plan = [
                        {
                            "step": "calculate_quarterly_rate",
                            "tool": "calculate_quarterly_rate",
                            "args": {"annual_rate": interest_rate},
                            "reasoning": "Starting compound interest calculation by determining the quarterly rate."
                        },
                        {
                            "step": "verify_quarterly_rate",
                            "tool": "verify_quarterly_rate",
                            "args": {"quarterly_rate": None, "annual_rate": interest_rate},
                            "reasoning": "Verifying the quarterly rate calculation."
                        },
                        {
                            "step": "calculate_compounding_periods",
                            "tool": "calculate_compounding_periods",
                            "args": {"years": years},
                            "reasoning": "Calculating the number of compounding periods."
                        },
                        {
                            "step": "verify_compounding_periods",
                            "tool": "verify_compounding_periods",
                            "args": {"periods": None, "years": years},
                            "reasoning": "Verifying the compounding periods calculation."
                        },
                        {
                            "step": "calculate_compound_interest",
                            "tool": "calculate_compound_interest",
                            "args": {"principal": principal, "rate": None, "periods": None},
                            "reasoning": "Calculating the compound interest with the verified quarterly rate and periods."
                        },
                        {
                            "step": "verify_calculation",
                            "tool": "verify_calculation",
                            "args": {"final_amount": None, "principal": principal},
                            "reasoning": "Verifying the compound interest calculation."
                        }
                    ]
                    
                    # Add bonus calculation if applicable
                    if "bonus_rate" in entities:
                        self.execution_plan.append({
                            "step": "calculate_bonus",
                            "tool": "calculate_bonus",
                            "args": {"principal": principal, "bonus_rate": bonus_rate},
                            "reasoning": "Calculating the bonus amount on the principal."
                        })
                    
                    # Print the execution plan
                    print("\n=== EXECUTION PLAN ===")
                    for i, step in enumerate(self.execution_plan):
                        print(f"{i+1}. {step['step']}: {step['reasoning']}")
                    print("=====================\n")
            
            # If we have a calculation history, update our execution plan
            if "calculation_history" in input_data.perception.entities:
                history = input_data.perception.entities["calculation_history"]
                if isinstance(history, list):
                    # Update the execution plan with the results from the history
                    for entry in history:
                        function_name = entry["function"]
                        result = entry["result"]
                        
                        # Find the corresponding step in the execution plan
                        for step in self.execution_plan:
                            if step["tool"] == function_name:
                                # Update the args for the next steps that depend on this result
                                if function_name == "calculate_quarterly_rate":
                                    # Update verify_quarterly_rate and calculate_compound_interest
                                    for next_step in self.execution_plan:
                                        if next_step["tool"] == "verify_quarterly_rate":
                                            next_step["args"]["quarterly_rate"] = result
                                        elif next_step["tool"] == "calculate_compound_interest":
                                            next_step["args"]["rate"] = result
                                elif function_name == "calculate_compounding_periods":
                                    # Update verify_compounding_periods and calculate_compound_interest
                                    for next_step in self.execution_plan:
                                        if next_step["tool"] == "verify_compounding_periods":
                                            next_step["args"]["periods"] = result
                                        elif next_step["tool"] == "calculate_compound_interest":
                                            next_step["args"]["periods"] = result
                                elif function_name == "calculate_compound_interest":
                                    # Update verify_calculation
                                    for next_step in self.execution_plan:
                                        if next_step["tool"] == "verify_calculation":
                                            next_step["args"]["final_amount"] = result
                                elif function_name == "calculate_bonus":
                                    # This is the last step, no need to update anything
                                    pass
            
            # Execute the next step in the plan
            if self.current_step_index < len(self.execution_plan):
                next_step = self.execution_plan[self.current_step_index]
                
                # Check if we've already completed this step
                step_key = f"{next_step['tool']}_{json.dumps(next_step['args'], sort_keys=True)}"
                if step_key in self.completed_steps:
                    # Skip to the next step
                    self.current_step_index += 1
                    if self.current_step_index < len(self.execution_plan):
                        next_step = self.execution_plan[self.current_step_index]
                    else:
                        # We've completed all steps
                        return DecisionOutput(
                            next_action="calculation_complete",
                            tool_name=None,
                            tool_args={},
                            reasoning="All calculation steps have been completed."
                        )
                
                # Add the step to completed steps
                self.completed_steps.add(step_key)
                
                # Return the decision for the next step
                return DecisionOutput(
                    next_action=next_step["step"],
                    tool_name=next_step["tool"],
                    tool_args=next_step["args"],
                    reasoning=next_step["reasoning"]
                )
            else:
                # We've completed all steps
                return DecisionOutput(
                    next_action="calculation_complete",
                    tool_name=None,
                    tool_args={},
                    reasoning="All calculation steps have been completed."
                )
        
        # For non-compound interest calculations, use the LLM
        # Prepare the prompt for the LLM
        prompt = f"""
        As {self.user_preference.agent_name}, with a {self.user_preference.personality} personality,
        analyze the following situation and decide the next action.

        Current Perception:
        - Processed Input: {input_data.perception.processed_input}
        - Intent: {input_data.perception.intent}
        - Entities: {input_data.perception.entities}
        - Confidence: {input_data.perception.confidence}

        Recent Memory Context:
        {self._format_memory_context(input_data.memory)}

        Available Tools:
        {self._format_available_tools(input_data.available_tools)}

        Previous Steps Completed:
        {', '.join(self.completed_steps) if self.completed_steps else 'None'}

        Based on the current perception and memory context, what should be the next action?
        You must respond with EXACTLY ONE line starting with "FUNCTION_CALL:" followed by a valid JSON object.
        The JSON object must have these exact keys: "function", "params", "reasoning_type", and "self_check".
        The "params" value must be an array of strings representing the parameters in the correct order.

        Here are examples of valid responses:

        FUNCTION_CALL: {{"function": "calculate_quarterly_rate", "params": ["0.045"], "reasoning_type": "calculating quarterly interest rate from annual rate", "self_check": "verify the quarterly rate is less than the annual rate"}}

        FUNCTION_CALL: {{"function": "calculate_bonus", "params": ["10000", "0.005"], "reasoning_type": "calculating bonus amount on principal", "self_check": "verify bonus is 0.5% of principal"}}

        FUNCTION_CALL: {{"function": "verify_calculation", "params": ["12507.50", "10000"], "reasoning_type": "verifying final amount is greater than principal", "self_check": "confirm the calculation shows growth"}}

        Remember:
        1. Your response must be EXACTLY ONE line
        2. The line must start with "FUNCTION_CALL:"
        3. The JSON must be valid with no formatting/indentation
        4. All numbers must be passed as strings in the params array
        5. The function name must match one of the available tools
        """
        
        try:
            # Get response from LLM with timeout
            response = await self.generate_with_timeout(prompt)
            response_text = response.text
            
            # Parse the response to extract the function call
            try:
                # Find the FUNCTION_CALL line in the response
                for line in response_text.split('\n'):
                    line = line.strip()
                    if line.startswith("FUNCTION_CALL:"):
                        function_info = line.split(":", 1)[1].strip()
                        result = json.loads(function_info)
                        break
                else:
                    raise ValueError("No FUNCTION_CALL found in response")
                
                # Convert the function call format to DecisionOutput format
                tool_args = {}
                if len(result.get("params", [])) > 0:
                    # For compound interest calculation
                    if result["function"] == "calculate_quarterly_rate":
                        tool_args["annual_rate"] = float(result["params"][0])
                    elif result["function"] == "verify_quarterly_rate":
                        tool_args["quarterly_rate"] = float(result["params"][0])
                        tool_args["annual_rate"] = float(result["params"][1])
                    elif result["function"] == "calculate_compounding_periods":
                        tool_args["years"] = int(result["params"][0])
                    elif result["function"] == "verify_compounding_periods":
                        tool_args["periods"] = int(result["params"][0])
                        tool_args["years"] = int(result["params"][1])
                    elif result["function"] == "calculate_compound_interest":
                        tool_args["principal"] = float(result["params"][0])
                        tool_args["rate"] = float(result["params"][1])
                        tool_args["periods"] = int(result["params"][2])
                    elif result["function"] == "verify_calculation":
                        tool_args["final_amount"] = float(result["params"][0])
                        tool_args["principal"] = float(result["params"][1])
                    elif result["function"] == "calculate_bonus":
                        tool_args["principal"] = float(result["params"][0])
                        tool_args["bonus_rate"] = float(result["params"][1])
                
                # Add the action to completed steps
                action_key = f"{result['function']}_{','.join(result['params'])}"
                self.completed_steps.add(action_key)
                
                return DecisionOutput(
                    next_action=result["reasoning_type"],
                    tool_name=result["function"],
                    tool_args=tool_args,
                    reasoning=result["self_check"]
                )
                
            except Exception as e:
                print(f"Error parsing LLM response: {e}")
                # Create a basic result
                return DecisionOutput(
                    next_action="error_handling",
                    tool_name=None,
                    tool_args={},
                    reasoning=f"Error parsing LLM response: {str(e)}"
                )
            
        except Exception as e:
            # In case of error, return a basic decision output
            return DecisionOutput(
                next_action="error_handling",
                tool_name=None,
                tool_args={},
                reasoning=f"Error in decision making: {str(e)}"
            )
    
    def _format_memory_context(self, memory) -> str:
        """Format memory context for the prompt"""
        recent_entries = memory.entries[-5:] if memory.entries else []
        context_str = "\n".join([
            f"- {entry.timestamp}: {entry.interaction_type} - {entry.content}"
            for entry in recent_entries
        ])
        return context_str if context_str else "No recent memory entries."
    
    def _format_available_tools(self, tools: List[str]) -> str:
        """Format available tools for the prompt"""
        if not tools:
            return "No tools available."
        
        return "\n".join([f"- {tool}" for tool in tools])
    
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
    
    def reset_state(self):
        """Reset the decision-making state"""
        self.iteration = 0
        self.completed_steps = set()
        self.execution_plan = []
        self.current_step_index = 0 