import os
import asyncio
import google.generativeai as genai
from dotenv import load_dotenv
import json
import logging
from typing import Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure the Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize the model
model = genai.GenerativeModel('gemini-1.5-pro')

def load_criteria() -> str:
    """
    Load evaluation criteria from prompt_of_prompts.md
    """
    try:
        with open("prompt_of_prompts.md", "r") as f:
            content = f.read()
            # Extract the criteria section (everything between "Evaluate the prompt on the following criteria:" and "---")
            criteria_start = content.find("Evaluate the prompt on the following criteria:")
            criteria_end = content.find("---", criteria_start)
            if criteria_start != -1 and criteria_end != -1:
                criteria = content[criteria_start:criteria_end].strip()
                return criteria
            else:
                logger.error("Could not find criteria section in prompt_of_prompts.md")
                return None
    except FileNotFoundError:
        logger.error("prompt_of_prompts.md not found")
        return None
    except Exception as e:
        logger.error(f"Error loading criteria: {str(e)}")
        return None

async def verify_system_prompt() -> Tuple[bool, Optional[str]]:
    """
    Verify the system prompt against specific criteria.
    Returns a tuple of (is_valid, modified_prompt).
    """
    try:
        # Try to read system_prompt.md first
        try:
            with open("system_prompt.md", "r") as f:
                system_prompt = f.read()
        except FileNotFoundError:
            # Fall back to prompt_of_prompts.md
            try:
                with open("prompt_of_prompts.md", "r") as f:
                    system_prompt = f.read()
            except FileNotFoundError:
                logger.error("No system prompt file found")
                return False, None

        # Load criteria from prompt_of_prompts.md
        criteria = load_criteria()
        if not criteria:
            logger.error("Failed to load criteria from prompt_of_prompts.md")
            return False, None

        # Create verification prompt
        verification_prompt = f"""
        Please verify the following system prompt against these criteria:
        {criteria}

        System Prompt:
        {system_prompt}

        Analyze the prompt and respond with one of these options:
        1. VALID - if the prompt meets all criteria
        2. MODIFIED:<modified_prompt> - if the prompt needs minor adjustments
        3. INVALID - if the prompt fails to meet critical criteria

        Provide a brief explanation for your decision.
        """

        # Send verification request to the model
        response = await model.generate_content_async(verification_prompt)
        result = response.text.strip().upper()

        if result.startswith("VALID"):
            logger.info("System prompt verification successful")
            return True, system_prompt
        elif result.startswith("MODIFIED:"):
            modified_prompt = result.split("MODIFIED:", 1)[1].strip()
            logger.info("System prompt needs modification")
            return True, modified_prompt
        else:
            logger.error("System prompt verification failed")
            return False, None

    except Exception as e:
        logger.error(f"Error during system prompt verification: {str(e)}")
        return False, None

async def verify_prompt(query: str) -> Tuple[bool, str]:
    """
    Verify if the query is appropriate for mathematical calculations.
    Returns a tuple of (is_valid, updated_query).
    """
    try:
        verification_prompt = f"""
        Verify if this query is appropriate for mathematical calculations:
        {query}

        Respond with:
        VALID - if the query is appropriate
        MODIFIED:<updated_query> - if the query needs clarification
        INVALID - if the query is not appropriate for calculations
        """

        response = await model.generate_content_async(verification_prompt)
        result = response.text.strip().upper()

        if result.startswith("VALID"):
            return True, query
        elif result.startswith("MODIFIED:"):
            updated_query = result.split("MODIFIED:", 1)[1].strip()
            return True, updated_query
        else:
            return False, query

    except Exception as e:
        logger.error(f"Error during prompt verification: {str(e)}")
        return False, query

async def main():
    # First verify the system prompt
    is_valid, system_prompt = await verify_system_prompt()
    if not is_valid:
        logger.error("System prompt verification failed. Please check the prompt files.")
        return

    # Example queries to test
    test_queries = [
        "Calculate compound interest for $10000 at 4.5% for 5 years",
        "What's the bonus for a $10000 investment with 0.5% rate?",
        "Calculate quarterly rate for 4.5% annual rate",
        "Verify if 20 compounding periods is correct for 5 years",
        "Calculate final amount for $10000 with quarterly rate 0.01125 for 20 periods"
    ]

    for query in test_queries:
        logger.info(f"\nTesting query: {query}")
        is_valid, updated_query = await verify_prompt(query)
        
        if is_valid:
            logger.info(f"Query is valid. Updated query: {updated_query}")
        else:
            logger.warning(f"Query is not appropriate for calculations: {query}")

if __name__ == "__main__":
    asyncio.run(main()) 