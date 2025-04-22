import json
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import os

class InvestmentPreferences(BaseModel):
    """Model for investment-related user preferences"""
    investment_duration: str = Field(..., description="How long the user plans to keep money invested")
    risk_level: str = Field(..., description="User's risk tolerance for investment")
    compounding_frequency: str = Field(..., description="How frequently interest compounds")
    additional_contributions: str = Field(..., description="Whether user will make additional contributions")
    interest_rate_preference: str = Field(..., description="Whether user prefers fixed or fluctuating rates")
    withdrawal_strategy: str = Field(..., description="User's plan for withdrawals during investment period")
    output_preference: str = Field(..., description="How user wants to see the results")

class PreferenceManager:
    """Manages user preferences collection and storage"""
    
    def __init__(self, preferences_file: str = "user_preferences.json"):
        self.preferences_file = preferences_file
        self.preferences = self._load_preferences()
    
    def _load_preferences(self) -> Dict[str, Any]:
        """Load preferences from file or return empty dict if not exists"""
        if os.path.exists(self.preferences_file):
            try:
                with open(self.preferences_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading preferences: {e}")
                return {}
        return {}
    
    def _save_preferences(self):
        """Save preferences to file"""
        try:
            with open(self.preferences_file, 'w') as f:
                json.dump(self.preferences, f, indent=2)
        except Exception as e:
            print(f"Error saving preferences: {e}")
    
    def collect_investment_preferences(self) -> InvestmentPreferences:
        """Collect investment preferences from the user"""
        print("\n=== Investment Preference Collection ===")
        print("Please answer the following questions to personalize your investment calculations.\n")
        
        # 1. Investment Duration
        print("1. Investment Duration:")
        print("How long are you planning to keep your money invested?")
        print("   a) Less than 1 year")
        print("   b) 1–3 years")
        print("   c) 3–5 years")
        print("   d) More than 5 years")
        
        duration_map = {
            'a': "Less than 1 year",
            'b': "1–3 years",
            'c': "3–5 years",
            'd': "More than 5 years"
        }
        
        while True:
            choice = input("Your choice (a-d): ").lower()
            if choice in duration_map:
                investment_duration = duration_map[choice]
                break
            print("Invalid choice. Please select a, b, c, or d.")
        
        # 2. Risk Level
        print("\n2. Risk Level:")
        print("What's your risk tolerance for this investment?")
        print("   a) Low risk (I prefer stable returns)")
        print("   b) Medium risk (I'm open to some fluctuations)")
        print("   c) High risk (I'm okay with volatility for higher returns)")
        
        risk_map = {
            'a': "Low risk (stable returns)",
            'b': "Medium risk (some fluctuations)",
            'c': "High risk (volatility for higher returns)"
        }
        
        while True:
            choice = input("Your choice (a-c): ").lower()
            if choice in risk_map:
                risk_level = risk_map[choice]
                break
            print("Invalid choice. Please select a, b, or c.")
        
        # 3. Compounding Frequency
        print("\n3. Compounding Frequency:")
        print("How frequently would you like the interest to compound?")
        print("   a) Annually")
        print("   b) Quarterly")
        print("   c) Monthly")
        print("   d) Daily")
        
        frequency_map = {
            'a': "Annually",
            'b': "Quarterly",
            'c': "Monthly",
            'd': "Daily"
        }
        
        while True:
            choice = input("Your choice (a-d): ").lower()
            if choice in frequency_map:
                compounding_frequency = frequency_map[choice]
                break
            print("Invalid choice. Please select a, b, c, or d.")
        
        # 4. Additional Contributions
        print("\n4. Additional Contributions:")
        print("Will you be making additional contributions to the investment over time?")
        print("   a) Yes, I plan to contribute regularly")
        print("   b) Yes, but only occasionally")
        print("   c) No, it's a one-time investment")
        
        contributions_map = {
            'a': "Regular contributions",
            'b': "Occasional contributions",
            'c': "One-time investment"
        }
        
        while True:
            choice = input("Your choice (a-c): ").lower()
            if choice in contributions_map:
                additional_contributions = contributions_map[choice]
                break
            print("Invalid choice. Please select a, b, or c.")
        
        # 5. Interest Rate Preference
        print("\n5. Interest Rate Preference:")
        print("Would you prefer a fixed interest rate, or are you open to a fluctuating rate over time?")
        print("   a) Fixed rate")
        print("   b) Fluctuating rate")
        print("   c) I'm not sure yet")
        
        rate_map = {
            'a': "Fixed rate",
            'b': "Fluctuating rate",
            'c': "Undecided"
        }
        
        while True:
            choice = input("Your choice (a-c): ").lower()
            if choice in rate_map:
                interest_rate_preference = rate_map[choice]
                break
            print("Invalid choice. Please select a, b, or c.")
        
        # 6. Withdrawal Strategy
        print("\n6. Withdrawal Strategy:")
        print("Do you plan to withdraw any of the investment during the investment period?")
        print("   a) Yes, periodically (e.g., annually, quarterly)")
        print("   b) No, I plan to leave the investment intact")
        print("   c) I'm not sure")
        
        withdrawal_map = {
            'a': "Periodic withdrawals",
            'b': "No withdrawals",
            'c': "Undecided"
        }
        
        while True:
            choice = input("Your choice (a-c): ").lower()
            if choice in withdrawal_map:
                withdrawal_strategy = withdrawal_map[choice]
                break
            print("Invalid choice. Please select a, b, or c.")
        
        # 7. Output Preference
        print("\n7. Output Preference:")
        print("How would you like to see the results?")
        print("   a) A detailed breakdown of each compounding period")
        print("   b) A final amount at the end of the investment period")
        print("   c) A graph/chart showing growth over time")
        
        output_map = {
            'a': "Detailed breakdown",
            'b': "Final amount only",
            'c': "Growth chart"
        }
        
        while True:
            choice = input("Your choice (a-c): ").lower()
            if choice in output_map:
                output_preference = output_map[choice]
                break
            print("Invalid choice. Please select a, b, or c.")
        
        # Create and save preferences
        preferences = InvestmentPreferences(
            investment_duration=investment_duration,
            risk_level=risk_level,
            compounding_frequency=compounding_frequency,
            additional_contributions=additional_contributions,
            interest_rate_preference=interest_rate_preference,
            withdrawal_strategy=withdrawal_strategy,
            output_preference=output_preference
        )
        
        # Save to file
        self.preferences["investment"] = preferences.model_dump()
        self._save_preferences()
        
        print("\n=== Preferences Saved Successfully ===")
        return preferences
    
    def get_investment_preferences(self) -> Optional[InvestmentPreferences]:
        """Get investment preferences if they exist"""
        if "investment" in self.preferences:
            return InvestmentPreferences(**self.preferences["investment"])
        return None
    
    def format_preferences_for_prompt(self) -> str:
        """Format preferences for inclusion in LLM prompts"""
        if not self.preferences:
            return "No user preferences available."
        
        formatted = "User Preferences:\n"
        
        if "investment" in self.preferences:
            inv_prefs = self.preferences["investment"]
            formatted += "- Investment Duration: " + inv_prefs["investment_duration"] + "\n"
            formatted += "- Risk Level: " + inv_prefs["risk_level"] + "\n"
            formatted += "- Compounding Frequency: " + inv_prefs["compounding_frequency"] + "\n"
            formatted += "- Additional Contributions: " + inv_prefs["additional_contributions"] + "\n"
            formatted += "- Interest Rate Preference: " + inv_prefs["interest_rate_preference"] + "\n"
            formatted += "- Withdrawal Strategy: " + inv_prefs["withdrawal_strategy"] + "\n"
            formatted += "- Output Preference: " + inv_prefs["output_preference"] + "\n"
        
        return formatted 