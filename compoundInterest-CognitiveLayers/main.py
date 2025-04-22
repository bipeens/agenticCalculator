import asyncio
from typing import Dict, Any, Optional
from models import UserPreference, PerceptionInput
from perception import Perception
from memory import Memory
from decision_making import DecisionMaking
from action import Action
import os
from dotenv import load_dotenv
import json
import sys

# Load environment variables
load_dotenv()

async def get_user_preferences() -> UserPreference:
    """Get user preferences before starting the agent"""
    print("Welcome! Let's set up your agent preferences.")
    
    # Check if preferences are already saved
    if os.path.exists("user_preferences.json"):
        try:
            with open("user_preferences.json", "r") as f:
                saved_prefs = json.load(f)
                use_saved = input("Found saved preferences. Would you like to use them? (y/n): ")
                if use_saved.lower() == "y":
                    return UserPreference(**saved_prefs)
        except Exception as e:
            print(f"Error loading saved preferences: {e}")
    
    # Get new preferences
    agent_name = input("What would you like to name your agent? ")
    personality = input("What personality should the agent have? (e.g., friendly, professional, creative) ")
    response_style = input("What response style do you prefer? (e.g., formal, casual, technical) ")
    
    while True:
        try:
            memory_retention = int(input("How many previous interactions should the agent remember? (1-100) "))
            if 1 <= memory_retention <= 100:
                break
            print("Please enter a number between 1 and 100.")
        except ValueError:
            print("Please enter a valid number.")
    
    preferences = UserPreference(
        agent_name=agent_name,
        personality=personality,
        response_style=response_style,
        memory_retention=memory_retention
    )
    
    # Save preferences
    try:
        with open("user_preferences.json", "w") as f:
            json.dump(preferences.model_dump(), f, indent=2)
    except Exception as e:
        print(f"Error saving preferences: {e}")
    
    return preferences

class Agent:
    def __init__(self, user_preference: UserPreference):
        self.user_preference = user_preference
        self.perception = Perception()
        self.memory = Memory(user_preference)
        self.decision_making = DecisionMaking(user_preference)
        self.action = Action()
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize the agent components"""
        if self.is_initialized:
            return True
        
        try:
            # Initialize the action component
            action_initialized = await self.action.initialize()
            if not action_initialized:
                print("Warning: Failed to initialize action component.")
            
            self.is_initialized = True
            return True
        except Exception as e:
            print(f"Error initializing agent: {e}")
            return False
        
    async def save_preferences(self):
        """Save user preferences to a file"""
        try:
            with open("user_preferences.json", "w") as f:
                json.dump(self.user_preference.model_dump(), f, indent=2)
            print("✓ User preferences saved successfully")
        except Exception as e:
            print(f"✗ Error saving user preferences: {e}")

    async def process_input(self, user_input: str) -> Dict[str, Any]:
        """Process user input through the agent's components"""
        try:
            # Get perception
            perception_output = await self.perception.process_input(user_input)
            
            # Get decision
            decision_input = DecisionInput(
                perception=perception_output,
                memory=self.memory,
                available_tools=self.action.available_tools
            )
            decision_output = await self.decision_making.make_decision(decision_input)
            
            # Execute action
            action_input = ActionInput(
                perception=perception_output,
                decision=decision_output,
                memory=self.memory
            )
            action_output = await self.action.execute(action_input)
            
            # Update memory
            self.memory.add_entry(
                interaction_type="user_input",
                content={
                    "perception": perception_output.model_dump()
                }
            )
            
            # Return results
            return {
                "perception": perception_output.model_dump(),
                "decision": decision_output.model_dump(),
                "result": action_output.model_dump()
            }
            
        except Exception as e:
            print(f"Error processing input: {e}")
            return {
                "error": str(e),
                "perception": perception_output.model_dump() if 'perception_output' in locals() else {},
                "decision": decision_output.model_dump() if 'decision_output' in locals() else {},
                "action": action_output.model_dump() if 'action_output' in locals() else {}
            }
    
    def reset(self):
        """Reset the agent state"""
        self.decision_making.reset_state()
        # Don't reset memory as it's part of the agent's knowledge

async def main():
    # Check for required environment variables
    required_vars = ["GOOGLE_API_KEY", "MCP_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file or environment.")
        sys.exit(1)
    
    # Get user preferences
    user_preference = await get_user_preferences()
    
    # Initialize agent
    agent = Agent(user_preference)
    await agent.initialize()
    
    print(f"\n{user_preference.agent_name} is ready! Type 'exit' to quit, 'reset' to reset the agent state.")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'reset':
            agent.reset()
            print("Agent state reset.")
            continue
            
        result = await agent.process_input(user_input)
        
        # Print the agent's response
        print(f"\n{user_preference.agent_name}: {result['result'].get('message', '')}")
        if result['error']:
            print(f"Error: {result['error']}")

if __name__ == "__main__":
    asyncio.run(main()) 