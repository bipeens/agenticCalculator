# basic import 
from mcp.server.fastmcp import FastMCP, Image
from mcp.server.fastmcp.prompts import base
from mcp.types import TextContent
from mcp import types
from PIL import Image as PILImage
import math
import sys
import pyautogui
import time
import subprocess
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# instantiate an MCP server client
mcp = FastMCP("CompoundInterestAgent")

# DEFINE TOOLS

@mcp.tool()
def calculate_quarterly_rate(annual_rate: float) -> float:
    """Calculate the quarterly interest rate from annual rate"""
    print("CALLED: calculate_quarterly_rate(annual_rate: float) -> float:")
    return float(annual_rate / 4)

@mcp.tool()
def calculate_compounding_periods(years: int) -> int:
    """Calculate the number of compounding periods for quarterly compounding"""
    print("CALLED: calculate_compounding_periods(years: int) -> int:")
    return int(years * 4)

@mcp.tool()
def calculate_compound_interest(principal: float, rate: float, periods: int) -> float:
    """Calculate compound interest using the formula A = P(1 + r)^n"""
    print("CALLED: calculate_compound_interest(principal: float, rate: float, periods: int) -> float:")
    return float(principal * (1 + rate) ** periods)

@mcp.tool()
def calculate_bonus(principal: float, bonus_rate: float) -> float:
    """Calculate bonus amount on principal"""
    print("CALLED: calculate_bonus(principal: float, bonus_rate: float) -> float:")
    return float(principal * bonus_rate)

@mcp.tool()
def verify_calculation(final_amount: float, principal: float) -> bool:
    """Verify that the final amount is greater than the principal"""
    print("CALLED: verify_calculation(final_amount: float, principal: float) -> bool:")
    return bool(final_amount > principal)

@mcp.tool()
def verify_quarterly_rate(quarterly_rate: float, annual_rate: float) -> bool:
    """Verify that quarterly rate is less than annual rate"""
    print("CALLED: verify_quarterly_rate(quarterly_rate: float, annual_rate: float) -> bool:")
    return bool(quarterly_rate < annual_rate)

@mcp.tool()
def verify_compounding_periods(periods: int, years: int) -> bool:
    """Verify that the number of compounding periods is correct"""
    print("CALLED: verify_compounding_periods(periods: int, years: int) -> bool:")
    return bool(periods == years * 4)

# DEFINE RESOURCES

# Add a dynamic greeting resource
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    print("CALLED: get_greeting(name: str) -> str:")
    return f"Hello, {name}!"


# DEFINE AVAILABLE PROMPTS
@mcp.prompt()
def review_code(code: str) -> str:
    return f"Please review this code:\n\n{code}"
    print("CALLED: review_code(code: str) -> str:")


@mcp.prompt()
def debug_error(error: str) -> list[base.Message]:
    return [
        base.UserMessage("I'm seeing this error:"),
        base.UserMessage(error),
        base.AssistantMessage("I'll help debug that. What have you tried so far?"),
    ]

if __name__ == "__main__":
    # Check if running with mcp dev command
    print("STARTING")
    if len(sys.argv) > 1 and sys.argv[1] == "dev":
        mcp.run()  # Run without transport for dev server
    else:
        mcp.run(transport="stdio")  # Run with stdio for direct execution
