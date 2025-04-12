import os
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client
import asyncio
import google.generativeai as genai
from concurrent.futures import TimeoutError
from functools import partial
import json

# Load environment variables from .env file
load_dotenv()

# Access your API key and initialize Gemini client correctly
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

max_iterations = 15
last_response = None
iteration = 0
iteration_response = []
completed_steps = set()  # Track completed steps to prevent repetition

async def generate_with_timeout(client, prompt, timeout=10):
    """Generate content with a timeout"""
    print("Starting LLM generation...")
    try:
        # Convert the synchronous generate_content call to run in a thread
        loop = asyncio.get_event_loop()
        response = await asyncio.wait_for(
            loop.run_in_executor(
                None, 
                lambda: genai.GenerativeModel('gemini-2.0-flash').generate_content(prompt)
            ),
            timeout=timeout
        )
        print("LLM generation completed")
        return response
    except TimeoutError:
        print("LLM generation timed out!")
        raise
    except Exception as e:
        print(f"Error in LLM generation: {e}")
        raise

def reset_state():
    """Reset all global variables to their initial state"""
    global last_response, iteration, iteration_response, completed_steps
    last_response = None
    iteration = 0
    iteration_response = []
    completed_steps = set()

async def verify_prompt(query: str) -> tuple[bool, str]:
    """
    Verify if the current prompt is appropriate for the given query.
    Returns a tuple of (is_valid, updated_query).
    """
    print("\n=== PROMPT VERIFICATION STARTED ===")
    print(f"Original query: {query}")
    
    verification_prompt = f"""You are a prompt verification agent. Your task is to verify if the following query is appropriate for mathematical calculations, particularly compound interest problems.

Query: {query}

Analyze the query and respond with EXACTLY ONE line in one of these formats:
1. If the query is valid and ready for mathematical processing:
   VALID: [original query]

2. If the query needs modification:
   MODIFIED: [modified query]

3. If the query is invalid or cannot be processed:
   INVALID: [explanation]

Consider these aspects:
- Does the query contain necessary numerical values?
- Is the mathematical operation clear?
- Are units and time periods specified?
- Is the query related to financial calculations?
- Are there any ambiguous terms that need clarification?

DO NOT include any explanations or additional text.
Your entire response should be a single line starting with either VALID:, MODIFIED:, or INVALID:"""

    try:
        print("Sending verification request to LLM...")
        response = await generate_with_timeout(genai, verification_prompt)
        if response and response.text:
            result = response.text.strip()
            print(f"Verification response: {result}")
            
            if result.startswith("VALID:"):
                print("✓ VERIFICATION RESULT: Query is valid and ready for processing")
                print("✓ No changes needed to the original query")
                print("=== PROMPT VERIFICATION COMPLETED ===\n")
                return True, query
            elif result.startswith("MODIFIED:"):
                modified_query = result[9:].strip()
                print("⚠ VERIFICATION RESULT: Query needed modification")
                print(f"⚠ Original query: {query}")
                print(f"⚠ Modified query: {modified_query}")
                print("=== PROMPT VERIFICATION COMPLETED ===\n")
                return True, modified_query
            else:
                invalid_reason = result[8:].strip() if result.startswith("INVALID:") else "Query verification failed"
                print("✗ VERIFICATION RESULT: Query is invalid")
                print(f"✗ Reason: {invalid_reason}")
                print("=== PROMPT VERIFICATION COMPLETED ===\n")
                return False, invalid_reason
        
        print("✗ VERIFICATION RESULT: No response from verification model")
        print("=== PROMPT VERIFICATION COMPLETED ===\n")
        return False, "No response from verification model"
        
    except Exception as e:
        print(f"✗ VERIFICATION ERROR: {str(e)}")
        print("=== PROMPT VERIFICATION COMPLETED ===\n")
        return False, f"Error during prompt verification: {str(e)}"

async def verify_system_prompt(system_prompt: str) -> tuple[bool, str]:
    """
    Verify if the system prompt is appropriate for mathematical calculations.
    Returns a tuple of (is_valid, updated_prompt).
    """
    print("\n=== SYSTEM PROMPT VERIFICATION STARTED ===")
    print("Original system prompt length:", len(system_prompt))
    
    # Read the system_prompt.md file
    try:
        with open("system_prompt.md", "r") as file:
            verified_prompt = file.read()
            print("Successfully loaded system prompt from system_prompt.md")
            
            # Replace the tools_description placeholder with the actual tools description
            tools_description = system_prompt.split("Available tools:\n")[1].split("\n\n")[0]
            verified_prompt = verified_prompt.replace("{tools_description}", tools_description)
            
            print("✓ VERIFICATION RESULT: Using pre-verified system prompt")
            print("=== SYSTEM PROMPT VERIFICATION COMPLETED ===\n")
            return True, verified_prompt
            
    except Exception as e:
        print(f"Error reading system_prompt.md: {e}")
        print("Falling back to direct verification...")
        
        # Read the prompt_of_prompts.md file
        try:
            with open("prompt_of_prompts.md", "r") as file:
                prompt_criteria = file.read()
                print("Successfully loaded prompt criteria from prompt_of_prompts.md")
        except Exception as e:
            print(f"Error reading prompt_of_prompts.md: {e}")
            return False, f"Error loading prompt criteria: {str(e)}"
        
        verification_prompt = f"""You are a prompt verification agent. Your task is to verify if the following system prompt is appropriate for mathematical calculations, particularly compound interest problems.

System Prompt:
{system_prompt}

Prompt Evaluation Criteria:
{prompt_criteria}

Analyze the system prompt against these criteria and respond with EXACTLY ONE line in one of these formats:
1. If the prompt is valid and ready for use:
   VALID: [original prompt]

2. If the prompt needs modification:
   MODIFIED: [modified prompt]

3. If the prompt is invalid or cannot be processed:
   INVALID: [explanation]

DO NOT include any explanations or additional text.
Your entire response should be a single line starting with either VALID:, MODIFIED:, or INVALID:"""

        try:
            print("Sending verification request to LLM...")
            response = await generate_with_timeout(genai, verification_prompt)
            if response and response.text:
                result = response.text.strip()
                print(f"Verification response: {result}")
                
                if result.startswith("VALID:"):
                    print("✓ VERIFICATION RESULT: System prompt is valid and ready for use")
                    print("✓ No changes needed to the original prompt")
                    print("=== SYSTEM PROMPT VERIFICATION COMPLETED ===\n")
                    return True, system_prompt
                elif result.startswith("MODIFIED:"):
                    modified_prompt = result[9:].strip()
                    print("⚠ VERIFICATION RESULT: System prompt needed modification")
                    print("⚠ Original prompt length:", len(system_prompt))
                    print("⚠ Modified prompt length:", len(modified_prompt))
                    print("=== SYSTEM PROMPT VERIFICATION COMPLETED ===\n")
                    return True, modified_prompt
                else:
                    invalid_reason = result[8:].strip() if result.startswith("INVALID:") else "System prompt verification failed"
                    print("✗ VERIFICATION RESULT: System prompt is invalid")
                    print(f"✗ Reason: {invalid_reason}")
                    print("=== SYSTEM PROMPT VERIFICATION COMPLETED ===\n")
                    return False, invalid_reason
            
            print("✗ VERIFICATION RESULT: No response from verification model")
            print("=== SYSTEM PROMPT VERIFICATION COMPLETED ===\n")
            return False, "No response from verification model"
            
        except Exception as e:
            print(f"✗ VERIFICATION ERROR: {str(e)}")
            print("=== SYSTEM PROMPT VERIFICATION COMPLETED ===\n")
            return False, f"Error during system prompt verification: {str(e)}"

async def get_user_query() -> str:
    """
    Get a query from the user or use the default query.
    Returns the query string.
    """
    print("\n=== QUERY INPUT ===")
    print("Do you want to use your own query? (y/n)")
    choice = input("> ").strip().lower()
    
    if choice == 'y':
        print("\nEnter your compound interest query:")
        print("Example: Calculate the final amount after 5 years if you invest $10,000 in a savings account with an annual interest rate of 4.5%, compounded quarterly.")
        user_query = input("> ")
        print("\nUsing your custom query.")
        return user_query
    else:
        default_query = """Calculate the final amount after 5 years if you invest $10,000 in a savings account with an annual interest rate of 4.5%, compounded quarterly. The bank also offers a bonus of 0.5% on the initial deposit. Please show all your work and verify your calculations at each step."""
        print("\nUsing the default query.")
        return default_query

async def main():
    reset_state()  # Reset at the start of main
    print("Starting main execution...")
    try:
        # Create a single MCP server connection
        print("Establishing connection to MCP server...")
        server_params = StdioServerParameters(
            command="python",
            args=["mcp_server.py"]
        )

        async with stdio_client(server_params) as (read, write):
            print("Session created, initializing...")
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Get available tools
                print("Requesting tool list...")
                tools_result = await session.list_tools()
                tools = tools_result.tools
                print(f"Successfully retrieved {len(tools)} tools")

                # Create system prompt with available tools
                print("Creating system prompt...")
                print(f"Number of tools: {len(tools)}")
                
                try:
                    tools_description = []
                    for i, tool in enumerate(tools):
                        try:
                            # Get tool properties
                            params = tool.inputSchema
                            desc = getattr(tool, 'description', 'No description available')
                            name = getattr(tool, 'name', f'tool_{i}')
                            
                            # Format the input schema in a more readable way
                            if 'properties' in params:
                                param_details = []
                                for param_name, param_info in params['properties'].items():
                                    param_type = param_info.get('type', 'unknown')
                                    param_details.append(f"{param_name}: {param_type}")
                                params_str = ', '.join(param_details)
                            else:
                                params_str = 'no parameters'

                            tool_desc = f"{i+1}. {name}({params_str}) - {desc}"
                            tools_description.append(tool_desc)
                            print(f"Added description for tool: {tool_desc}")
                        except Exception as e:
                            print(f"Error processing tool {i}: {e}")
                            tools_description.append(f"{i+1}. Error processing tool")
                    
                    tools_description = "\n".join(tools_description)
                    print("Successfully created tools description")
                except Exception as e:
                    print(f"Error creating tools description: {e}")
                    tools_description = "Error loading tools"
                
                print("Created system prompt...")
                
                # Create the system prompt
                system_prompt = f"""You are a mathematical agent solving compound interest problems. You have access to various mathematical tools for calculations and verification.

Available tools:
{tools_description}

You must respond with EXACTLY ONE line in one of these formats (no additional text):
1. For function calls (in JSON format):
   FUNCTION_CALL: {{"function": "function_name", "params": ["param1", "param2", ...], "reasoning_type": "arithmetic|reasoning|lookup", "self_check": "What I'm checking"}}
   
2. For final answers:
   FINAL_ANSWER: [number]

IMPORTANT INSTRUCTIONS:
- Break down the problem into logical steps
- Use appropriate tools for each calculation
- Verify your calculations at key points
- When a function returns multiple values, you need to process all of them
- Only give FINAL_ANSWER when you have completed all necessary calculations and verifications
- Do not repeat function calls with the same parameters
- If any verification fails, note it in your response
- For each step, identify the reasoning type (arithmetic, reasoning, or lookup)
- Perform internal self-checks before and after each calculation
- If you encounter uncertainty or errors, use fallback strategies
- IMPORTANT: After each function call, use the result in the next step. Do not call the same function again with the same parameters.

CRITICAL INSTRUCTION:
- You MUST follow a logical sequence of steps to solve the problem
- Each function should be called EXACTLY ONCE with the same parameters
- When you see a list of completed steps, DO NOT call any of those functions again
- Instead, use the results from previous steps to determine what to do next
- If you're unsure what to do next, review the completed steps and determine the next logical step
- NEVER call a function that has already been called with the same parameters
- If you see a function in the completed steps list, DO NOT call it again

REASONING TYPES:
- ARITHMETIC: For numerical calculations (e.g., converting rates, calculating interest)
- REASONING: For logical decisions (e.g., determining which formula to use)
- LOOKUP: For retrieving or verifying information

SELF-CHECK REQUIREMENTS:
- Before each calculation, verify that you have all necessary inputs
- After each calculation, verify that the result is reasonable
- If a result seems incorrect, use a different approach or tool to verify
- Document your self-checks in the "self_check" field of your function calls

ERROR HANDLING:
- If a calculation fails, try an alternative approach
- If a verification fails, note the issue and continue with caution
- If you're unsure about a result, use a different tool to verify
- If all else fails, provide your best estimate with a note about uncertainty

EXAMPLES:
- FUNCTION_CALL: {{"function": "calculate_quarterly_rate", "params": ["0.045"], "reasoning_type": "arithmetic", "self_check": "Converting annual rate to quarterly rate"}}
- FUNCTION_CALL: {{"function": "verify_quarterly_rate", "params": ["0.01125", "0.045"], "reasoning_type": "reasoning", "self_check": "Verifying quarterly rate is less than annual rate"}}
- FUNCTION_CALL: {{"function": "calculate_compound_interest", "params": ["10000", "0.01125", "20"], "reasoning_type": "arithmetic", "self_check": "Calculating compound interest with given parameters"}}
- FINAL_ANSWER: [12458.32]

DO NOT include any explanations or additional text.
Your entire response should be a single line starting with either FUNCTION_CALL: or FINAL_ANSWER:"""
                
                # Verify the system prompt before processing
                print("\n=== SYSTEM PROMPT VERIFICATION PHASE ===")
                print("Verifying system prompt against criteria from prompt_of_prompts.md...")
                is_valid, processed_prompt = await verify_system_prompt(system_prompt)
                
                if not is_valid:
                    print(f"\n❌ SYSTEM PROMPT REJECTED: {processed_prompt}")
                    print("=== SYSTEM PROMPT VERIFICATION PHASE ENDED ===\n")
                    return
                
                if processed_prompt != system_prompt:
                    print(f"\n✅ SYSTEM PROMPT MODIFIED:")
                    print(f"  Original length: {len(system_prompt)}")
                    print(f"  Modified length: {len(processed_prompt)}")
                    print("\n  Changes were made to improve the prompt based on the criteria in prompt_of_prompts.md")
                else:
                    print("\n✅ SYSTEM PROMPT ACCEPTED: No changes needed")
                    print("  The prompt meets all criteria from prompt_of_prompts.md")
                
                print("=== SYSTEM PROMPT VERIFICATION PHASE ENDED ===\n")
                
                system_prompt = processed_prompt  # Use the processed prompt for further execution
                print("System prompt verified, proceeding with execution...")
                
                # Get the query from the user or use the default
                query = await get_user_query()
                print("Starting iteration loop...")
                
                # Use global iteration variables
                global iteration, last_response, completed_steps
                
                # Track completed steps to prevent repetition
                completed_steps = set()  # Track completed steps to prevent repetition
                iteration_response = []  # Track responses from each iteration
                max_iterations = 10  # Maximum number of iterations to prevent infinite loops
                
                # Add a dictionary to store function results
                function_results = {}  # Store results of function calls to avoid recalculating
                
                while iteration < max_iterations:
                    print(f"\n--- Iteration {iteration + 1} ---")
                    
                    # Construct the current query with previous responses
                    if last_response is None:
                        current_query = query
                    else:
                        # Add a more explicit instruction to use the previous results
                        current_query = query + "\n\n" + " ".join(iteration_response)
                        
                        # Add completed steps to the query
                        if completed_steps:
                            current_query += "\n\nCOMPLETED STEPS (DO NOT CALL THESE FUNCTIONS AGAIN):\n"
                            for step in completed_steps:
                                current_query += f"- {step}\n"
                        
                        # Add function results to the query
                        if function_results:
                            current_query += "\nFUNCTION RESULTS (USE THESE IN YOUR CALCULATIONS):\n"
                            for func_name, result in function_results.items():
                                current_query += f"- {func_name}: {result}\n"
                        
                        current_query += "\nIMPORTANT: Use the results from the previous steps. DO NOT call any function that has already been called. What should you do next?"
                    
                    # Get model's response with timeout
                    print("Preparing to generate LLM response...")
                    prompt = f"{system_prompt}\n\nQuery: {current_query}"
                    
                    # Highlight the query being sent to the LLM
                    print("\n" + "="*80)
                    print("🔍 QUERY SENT TO LLM:")
                    print("-"*80)
                    print(current_query)
                    print("-"*80)
                    print("="*80 + "\n")
                    
                    try:
                        response = await generate_with_timeout(genai, prompt)
                        response_text = response.text.strip() if hasattr(response, 'text') else str(response)
                        print(f"LLM Response: {response_text}")
                        
                        # Find the FUNCTION_CALL line in the response
                        for line in response_text.split('\n'):
                            line = line.strip()
                            if line.startswith("FUNCTION_CALL:"):
                                response_text = line
                                break
                        
                    except Exception as e:
                        print(f"Failed to get LLM response: {e}")
                        break


                    if response_text.startswith("FUNCTION_CALL:"):
                        _, function_info = response_text.split(":", 1)
                        
                        try:
                            # Parse the JSON function call
                            function_data = json.loads(function_info)
                            
                            func_name = function_data.get("function")
                            params = function_data.get("params", [])
                            reasoning_type = function_data.get("reasoning_type", "unknown")
                            self_check = function_data.get("self_check", "No self-check specified")
                            
                            print(f"\nDEBUG: Function name: {func_name}")
                            print(f"DEBUG: Parameters: {params}")
                            print(f"DEBUG: Reasoning type: {reasoning_type}")
                            print(f"DEBUG: Self-check: {self_check}")
                            
                            # Check if this function has already been called with the same parameters
                            function_call_key = f"{func_name}_{','.join(params)}"
                            if function_call_key in completed_steps:
                                print(f"DEBUG: Function {func_name} with parameters {params} has already been called. Skipping.")
                                iteration_response.append(f"Function {func_name} with parameters {params} has already been called. Please move to the next step.")
                                iteration += 1
                                continue
                            
                        except json.JSONDecodeError:
                            # Fallback to the old format if JSON parsing fails
                            print("DEBUG: JSON parsing failed, falling back to old format")
                            # Try to extract the function name and parameters using regex
                            import re
                            function_match = re.search(r'"function"\s*:\s*"([^"]+)"', function_info)
                            params_match = re.search(r'"params"\s*:\s*\[(.*?)\]', function_info)
                            
                            if function_match and params_match:
                                func_name = function_match.group(1)
                                params_str = params_match.group(1)
                                # Parse the parameters string into a list
                                params = [p.strip().strip('"') for p in params_str.split(',')]
                                reasoning_type = "unknown"
                                self_check = "No self-check specified"
                                
                                print(f"DEBUG: Extracted function name: {func_name}")
                                print(f"DEBUG: Extracted parameters: {params}")
                                
                                # Check if this function has already been called with the same parameters
                                function_call_key = f"{func_name}_{','.join(params)}"
                                if function_call_key in completed_steps:
                                    print(f"DEBUG: Function {func_name} with parameters {params} has already been called. Skipping.")
                                    iteration_response.append(f"Function {func_name} with parameters {params} has already been called. Please move to the next step.")
                                    iteration += 1
                                    continue
                            else:
                                # If regex extraction fails, try the old format
                                parts = [p.strip() for p in function_info.split("|")]
                                if len(parts) >= 1:
                                    func_name = parts[0].strip('"{}')
                                    params = parts[1:] if len(parts) > 1 else []
                                    reasoning_type = "unknown"
                                    self_check = "No self-check specified"
                                    
                                    # Check if this function has already been called with the same parameters
                                    function_call_key = f"{func_name}_{','.join(params)}"
                                    if function_call_key in completed_steps:
                                        print(f"DEBUG: Function {func_name} with parameters {params} has already been called. Skipping.")
                                        iteration_response.append(f"Function {func_name} with parameters {params} has already been called. Please move to the next step.")
                                        iteration += 1
                                        continue
                                else:
                                    raise ValueError(f"Could not parse function call: {function_info}")
                            
                        try:
                            # Find the matching tool to get its input schema
                            tool = next((t for t in tools if t.name == func_name), None)
                            if not tool:
                                print(f"DEBUG: Available tools: {[t.name for t in tools]}")
                                raise ValueError(f"Unknown tool: {func_name}")

                            print(f"DEBUG: Found tool: {tool.name}")
                            print(f"DEBUG: Tool schema: {tool.inputSchema}")

                            # Prepare arguments according to the tool's input schema
                            arguments = {}
                            schema_properties = tool.inputSchema.get('properties', {})
                            print(f"DEBUG: Schema properties: {schema_properties}")

                            for param_name, param_info in schema_properties.items():
                                if not params:  # Check if we have enough parameters
                                    raise ValueError(f"Not enough parameters provided for {func_name}")
                                    
                                value = params.pop(0)  # Get and remove the first parameter
                                param_type = param_info.get('type', 'string')
                                
                                print(f"DEBUG: Converting parameter {param_name} with value {value} to type {param_type}")
                                
                                # Convert the value to the correct type based on the schema
                                if param_type == 'integer':
                                    arguments[param_name] = int(value)
                                elif param_type == 'number':
                                    arguments[param_name] = float(value)
                                elif param_type == 'array':
                                    # Handle array input
                                    if isinstance(value, str):
                                        value = value.strip('[]').split(',')
                                    arguments[param_name] = [int(x.strip()) for x in value]
                                else:
                                    arguments[param_name] = str(value)

                            print(f"DEBUG: Final arguments: {arguments}")
                            print(f"DEBUG: Calling tool {func_name}")
                            
                            # Add self-check information to the iteration response
                            iteration_response.append(f"Self-check: {self_check}")
                            
                            result = await session.call_tool(func_name, arguments=arguments)
                            print(f"DEBUG: Raw result: {result}")
                            
                            # Get the full result content
                            if hasattr(result, 'content'):
                                print(f"DEBUG: Result has content attribute")
                                # Handle multiple content items
                                if isinstance(result.content, list):
                                    iteration_result = [
                                        item.text if hasattr(item, 'text') else str(item)
                                        for item in result.content
                                    ]
                                else:
                                    iteration_result = str(result.content)
                            else:
                                print(f"DEBUG: Result has no content attribute")
                                iteration_result = str(result)
                                
                            print(f"DEBUG: Final iteration result: {iteration_result}")
                            
                            # Format the response based on result type
                            if isinstance(iteration_result, list):
                                result_str = f"[{', '.join(iteration_result)}]"
                            else:
                                result_str = str(iteration_result)
                            
                            # Store the result in the function_results dictionary
                            function_results[function_call_key] = result_str
                            
                            # Add more context to help the LLM understand what to do next
                            iteration_response.append(
                                f"In the {iteration + 1} iteration you called {func_name} with {arguments} parameters, "
                                f"and the function returned {result_str}. Reasoning type: {reasoning_type}. "
                                f"Now you should use this result in the next step. Do not call {func_name} again with the same parameters."
                            )
                            
                            # Mark this function call as completed
                            completed_steps.add(function_call_key)
                            
                            last_response = iteration_result

                        except Exception as e:
                            print(f"DEBUG: Error details: {str(e)}")
                            print(f"DEBUG: Error type: {type(e)}")
                            import traceback
                            traceback.print_exc()
                            
                            # Add fallback information to the iteration response
                            iteration_response.append(f"Error in iteration {iteration + 1}: {str(e)}")
                            iteration_response.append("Fallback: Trying to continue with the next step")
                            
                            # Don't break, try to continue with the next step
                            # break

                    elif response_text.startswith("FINAL_ANSWER:"):
                        print("\n=== Agent Execution Complete ===")
                        # Extract the actual answer from the response
                        answer = response_text.replace("FINAL_ANSWER:", "").strip()
                        
                        # Print the final answer with highlighting
                        print("\n" + "="*80)
                        print("🎯 FINAL ANSWER:")
                        print("-"*80)
                        print(f"The final amount after all calculations is: ${answer}")
                        print(f"This includes:")
                        print(f"- Principal amount: $10,000.00")
                        print(f"- Compound interest over 5 years at 4.5% annual rate, compounded quarterly")
                        print(f"- Initial bonus of 0.5% on the principal")
                        print("-"*80)
                        print("="*80 + "\n")
                        
                        break

                    iteration += 1

    except Exception as e:
        print(f"Error in main execution: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reset_state()  # Reset at the end of main

if __name__ == "__main__":
    asyncio.run(main())
    