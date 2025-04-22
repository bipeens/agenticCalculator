import asyncio
from models import UserPreference, PerceptionInput, DecisionInput, ActionInput
from perception import Perception
from memory import Memory
from decision_making import DecisionMaking
from action import Action
from preferences import PreferenceManager
import json
import os
from dotenv import load_dotenv
import hashlib
import argparse  # Add argparse for command line arguments

# Load environment variables
load_dotenv()

async def run_example(force_new_preferences: bool = False):
    """Run a simple example of the agentic framework"""
    print("Running Agentic AI Framework Example")
    print("=====================================")
    
    # Create a user preference
    user_preference = UserPreference(
        agent_name="CompoundInterestAgent",
        personality="precise and methodical",
        response_style="formal",
        memory_retention=10
    )
    
    # Initialize components
    print("Initializing components...")
    perception = Perception()
    await perception.initialize()  # Initialize the MCP server
    memory = Memory(user_preference)
    decision_making = DecisionMaking(user_preference)
    action = Action()
    
    # Initialize action component
    print("Initializing action component...")
    await action.initialize()
    
    # Initialize preference manager
    preference_manager = PreferenceManager()
    
    # Check if we already have investment preferences
    investment_preferences = preference_manager.get_investment_preferences()
    
    # If not, or if force_new_preferences is True, collect them
    if not investment_preferences or force_new_preferences:
        if force_new_preferences:
            print("\nForcing new preference collection...")
        else:
            print("\nNo investment preferences found. Let's collect them first.")
        investment_preferences = preference_manager.collect_investment_preferences()
    else:
        print("\nUsing existing investment preferences.")
        print(preference_manager.format_preferences_for_prompt())
    
    # Example user inputs
    example_inputs = [
        "Calculate the final amount after 5 years if you invest $10,000 in a savings account with an annual interest rate of 4.5%, compounded quarterly. The bank also offers a bonus of 0.5% on the initial deposit. Please show all your work and verify your calculations at each step."
    ]
    
    # Process each input
    for i, user_input in enumerate(example_inputs):
        print(f"\nExample {i+1}: '{user_input}'")
        print("-" * 50)
        
        # 1. Initial Perception
        print("\n=== PERCEPTION PHASE ===")
        perception_input = PerceptionInput(
            user_input=user_input,
            context={
                **memory.get_context(),
                "user_preferences": preference_manager.format_preferences_for_prompt()
            }
        )
        perception_output = await perception.process_input(perception_input)
        print(f"Perception: {perception_output.intent} (confidence: {perception_output.confidence})")
        print(f"Entities: {json.dumps(perception_output.entities, indent=2)}")
        print("=== PERCEPTION PHASE COMPLETED ===\n")
        
        # 2. Initial Memory
        memory.add_entry(
            interaction_type="user_input",
            content={
                "input": user_input,
                "perception": perception_output.model_dump(),
                "preferences": preference_manager.format_preferences_for_prompt()
            }
        )
        
        # Continue the calculation process until completion
        calculation_complete = False
        iteration = 0
        max_iterations = 10  # Prevent infinite loops
        
        # Track completed steps and their results to prevent duplication
        completed_steps = {}  # Dictionary to store tool calls and their results
        calculation_history = []  # Track the calculation history
        required_steps = [
            "calculate_bonus",
            "calculate_quarterly_rate",
            "verify_quarterly_rate",
            "calculate_compounding_periods",
            "verify_compounding_periods",
            "calculate_compound_interest",
            "verify_calculation"
        ]
        completed_required_steps = set()  # Track which required steps are completed
        final_result = None  # Store the final calculation result
        
        while not calculation_complete and iteration < max_iterations:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            # Check if we have completed all required steps
            if len(completed_required_steps) >= len(required_steps):
                calculation_complete = True
                print("\n=== CALCULATION COMPLETE ===")
                print("All calculation steps completed successfully!")
                
                # Print the final result
                if final_result and "final_amount" in final_result:
                    final_amount = final_result["final_amount"]
                    bonus_amount = 50.0  # We know this from calculate_bonus
                    total_amount = final_amount
                    
                    print("\n" + "="*80)
                    print("🎯 FINAL ANSWER:")
                    print("-"*80)
                    print(f"The final amount after all calculations is: ${total_amount:.2f}")
                    print(f"This includes:")
                    print(f"- Principal amount: $10,000.00")
                    print(f"- Compound interest over 5 years at 4.5% annual rate, compounded quarterly")
                    print(f"- Initial bonus of 0.5% on the principal: ${bonus_amount:.2f}")
                    print("-"*80)
                    print("="*80 + "\n")
                break
            
            # 3. Decision Making
            print("\n=== DECISION MAKING PHASE ===")
            decision_input = DecisionInput(
                perception=perception_output,
                memory=memory.memory,
                available_tools=list(action.available_tools.keys())
            )
            decision_output = await decision_making.make_decision(decision_input)
            
            # Check if we're done
            if decision_output.tool_name is None:
                print("No further actions needed.")
                break
                
            print(f"Decision: {decision_output.next_action}")
            print(f"Tool: {decision_output.tool_name}")
            print(f"Tool Args: {json.dumps(decision_output.tool_args, indent=2)}")
            print(f"Reasoning: {decision_output.reasoning}")
            print("=== DECISION MAKING PHASE COMPLETED ===\n")
            
            # Generate a unique key for this tool call
            tool_key = f"{decision_output.tool_name}:{json.dumps(decision_output.tool_args, sort_keys=True)}"
            
            # Check if we've already executed this exact tool call
            if tool_key in completed_steps:
                print(f"⚠️ Skipping duplicate tool call: {decision_output.tool_name}")
                print(f"Previous result: {json.dumps(completed_steps[tool_key], indent=2)}")
                
                # Update memory with the cached result
                memory.add_entry(
                    interaction_type="action",
                    content={
                        "decision": decision_output.model_dump(),
                        "result": completed_steps[tool_key],
                        "cached": True
                    }
                )
                continue
            
            # 4. Action
            print("\n=== ACTION PHASE ===")
            action_input = ActionInput(
                decision=decision_output,
                context=memory.get_context()
            )
            action_output = await action.execute(action_input)
            
            if action_output.success:
                print(f"Action Result: {json.dumps(action_output.result, indent=2)}")
                
                # Store the result in our completed steps
                completed_steps[tool_key] = action_output.result
                
                # Track the completed step
                if decision_output.tool_name in required_steps:
                    completed_required_steps.add(decision_output.tool_name)
                
                # Store final result if this is the compound interest calculation
                if decision_output.tool_name == "calculate_compound_interest":
                    final_result = action_output.result
                
                # Add to calculation history
                if isinstance(action_output.result, dict):
                    step_info = {
                        "function": decision_output.tool_name,
                        "args": decision_output.tool_args,
                        "result": action_output.result
                    }
                    calculation_history.append(step_info)
                    
                    # Update the perception output with the calculation history
                    if isinstance(perception_output.entities, dict):
                        perception_output.entities["calculation_history"] = calculation_history
            else:
                print(f"Action Error: {action_output.error}")
            print("=== ACTION PHASE COMPLETED ===\n")
            
            # Update memory with the action result
            memory.add_entry(
                interaction_type="action",
                content={
                    "decision": decision_output.model_dump(),
                    "result": action_output.result
                }
            )
        
        print("-" * 50)
    
    print("\nExample completed!")

if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Run the agentic AI framework example')
    parser.add_argument('--new-preferences', action='store_true', 
                      help='Force collection of new preferences even if they exist')
    args = parser.parse_args()
    
    # Run the example with the command line arguments
    asyncio.run(run_example(force_new_preferences=args.new_preferences)) 