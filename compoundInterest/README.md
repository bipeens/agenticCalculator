# Mathematical Query System

A flexible and structured system for solving compound interest problems using LLMs and specialized financial calculation tools.

## Overview

This project implements a mathematical query system that allows Large Language Models (LLMs) to solve compound interest problems step-by-step. The system uses a client-server architecture where:

- The client (`mcp_client.py`) handles communication with the LLM and manages the conversation flow
- The server (`mcp_server.py`) provides a set of financial calculation tools and verifications

The system is designed to follow best practices for prompt engineering, ensuring that the LLM:
- Breaks down problems into logical steps
- Uses appropriate tools for each calculation
- Verifies calculations at key points
- Provides structured output
- Identifies reasoning types
- Performs internal self-checks
- Implements fallback strategies

## Features

- **Flexible Problem Solving**: The LLM can determine the most logical approach to solve compound interest problems
- **Structured Output**: Responses are formatted consistently for easy parsing
- **Verification Steps**: Built-in tools to verify calculations at key points
- **Extensible Tool Set**: Easy to add new financial calculation tools as needed
- **Timeout Handling**: Prevents LLM calls from hanging indefinitely
- **JSON Function Calls**: Structured function calls using JSON format
- **Internal Self-Checks**: Explicit verification steps for each calculation
- **Reasoning Type Identification**: Categorizes each step as arithmetic, reasoning, or lookup
- **Fallback Strategies**: Handles errors and uncertainty gracefully
- **Prompt Verification**: Validates system prompts against best practices using `prompt_of_prompts.md`

## Financial Calculation Tools

The system includes specialized tools for compound interest calculations:

### Interest Rate Tools
- Quarterly rate conversion
- Rate verification

### Compounding Tools
- Compounding period calculations
- Period verification

### Interest Calculation Tools
- Compound interest calculations
- Bonus calculations
- Calculation verification

## Prompt Engineering Features

The system implements several advanced prompt engineering techniques:

### Prompt Verification
The system verifies prompts against best practices defined in `prompt_of_prompts.md`, which includes criteria for:
- Explicit reasoning instructions
- Structured output format
- Separation of reasoning and tools
- Conversation loop support
- Instructional framing
- Internal self-checks
- Reasoning type awareness
- Error handling or fallbacks
- Overall clarity and robustness

### JSON Function Calls
Function calls are structured in JSON format, making them more readable and extensible:
```json
{
  "function": "calculate_quarterly_rate",
  "params": ["0.045"],
  "reasoning_type": "arithmetic",
  "self_check": "Converting annual rate to quarterly rate"
}
```

### Internal Self-Checks
Each calculation step includes an explicit self-check to verify the correctness of the operation:
- "Verifying that quarterly rate is less than annual rate"
- "Checking if the number of compounding periods is correct"
- "Confirming that the final amount is greater than the principal"

### Reasoning Type Identification
Each step is categorized by its reasoning type:
- **ARITHMETIC**: For numerical calculations (e.g., converting rates, calculating interest)
- **REASONING**: For logical decisions (e.g., determining which formula to use)
- **LOOKUP**: For retrieving or verifying information

### Fallback Strategies
The system includes strategies for handling errors and uncertainty:
- If a calculation seems incorrect, try an alternative approach
- If a verification fails, double-check the inputs and recalculate
- If uncertain about a step, break it down into smaller sub-steps

### Explicit Reasoning Instructions
The prompt includes clear instructions for breaking down problems and reasoning step-by-step.

## Setup

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Usage

Run the client to start solving compound interest problems:

```
python mcp_client.py
```

The system will:
1. Connect to the MCP server
2. Initialize the session
3. Verify the system prompt against best practices
4. Send the financial query to the LLM
5. Process the LLM's response
6. Call the appropriate tools
7. Return the results

## Example Query

```
Calculate the final amount after 5 years if you invest $10,000 in a savings account with an annual interest rate of 4.5%, compounded quarterly. The bank also offers a bonus of 0.5% on the initial deposit. Please show all your work and verify your calculations at each step.
```

## Architecture

The system uses a client-server architecture:

- **Client (`mcp_client.py`)**: 
  - Manages communication with the LLM
  - Handles the conversation flow
  - Processes tool calls and responses
  - Implements timeout handling
  - Parses JSON function calls
  - Tracks reasoning types and self-checks
  - Verifies system prompts against best practices

- **Server (`mcp_server.py`)**: 
  - Provides financial calculation tools
  - Handles tool execution
  - Returns results to the client

## Extending the System

To add new financial calculation tools:

1. Add a new function to `mcp_server.py` with the `@mcp.tool()` decorator
2. Define the function parameters and return type
3. Implement the function logic
4. The tool will automatically be available to the LLM

