# Agentic AI Framework

A modular framework for building agentic AI systems with perception, memory, decision-making, and action capabilities.

## Overview

This framework provides a structured approach to building AI agents with the following components:

1. **Perception**: Understanding user input and sending it to an LLM for processing
2. **Memory**: Storing and retrieving information using JSON-based persistence
3. **Decision-Making**: Determining the next action based on current input and memory
4. **Action**: Executing MCP tools based on decisions

## Features

- **Modular Architecture**: Each component is designed to be independent and replaceable
- **Pydantic Models**: Type safety and validation for all inputs and outputs
- **Prompt Validation**: Safety checks to prevent harmful inputs
- **Persistent Memory**: JSON-based storage for agent memory
- **User Preferences**: Customizable agent behavior
- **MCP Tool Integration**: Seamless integration with MCP tools
- **Asynchronous Operations**: Better performance with async/await
- **LLM-Driven Decision Making**: The LLM determines the sequence of tool calls based on context and results
- **Result Feedback Loop**: Tool results are sent back to the LLM to inform the next decision
- **Preference-Based Personalization**: Collects user preferences before starting the agentic flow
- **Prompt Testing**: Comprehensive testing of system prompts and user queries

## Requirements

- Python 3.8+
- Dependencies listed in `requirements.txt`

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with the following variables:
   ```
   GOOGLE_API_KEY=your_google_api_key
   MCP_API_KEY=your_mcp_api_key
   MCP_BASE_URL=https://api.mcp.ai  # Optional
   ```

## Usage

Run the agent:

```
python main.py
```

The agent will:
1. Ask for your preferences (agent name, personality, response style, memory retention)
2. Collect domain-specific preferences (e.g., investment duration, risk level, compounding frequency)
3. Start processing your inputs
4. Use MCP tools as needed
5. Maintain memory of interactions
6. Provide responses based on your preferences

### User Preference Collection

Before starting the agentic flow, the system collects domain-specific preferences from the user. For example, in the investment calculator:

1. **Investment Duration**:
   - Less than 1 year
   - 1–3 years
   - 3–5 years
   - More than 5 years

2. **Risk Level**:
   - Low risk (stable returns)
   - Medium risk (some fluctuations)
   - High risk (volatility for higher returns)

3. **Compounding Frequency**:
   - Annually
   - Quarterly
   - Monthly
   - Daily

4. **Additional Contributions**:
   - Regular contributions
   - Occasional contributions
   - One-time investment

5. **Interest Rate Preference**:
   - Fixed rate
   - Fluctuating rate
   - Undecided

6. **Withdrawal Strategy**:
   - Periodic withdrawals
   - No withdrawals
   - Undecided

7. **Output Preference**:
   - Detailed breakdown
   - Final amount only
   - Growth chart

These preferences are incorporated into the prompts sent to the LLM, allowing it to tailor its responses and calculations to the user's specific needs and preferences.

### Commands

- `exit`: Quit the agent
- `reset`: Reset the agent state (keeps memory)

## Project Structure

- `models.py`: Pydantic models for type safety and validation
- `perception.py`: Input processing and LLM communication
- `memory.py`: JSON-based memory storage and retrieval
- `decision_making.py`: Action planning based on perception and memory
- `action.py`: MCP tool execution
- `main.py`: Orchestration of the agent components
- `example.py`: Example implementation of the framework for compound interest calculations
- `preferences.py`: User preference collection and management
- `prompt_test.py`: Testing and validation of system prompts and user queries
- `system_prompt.md`: System prompt for the LLM
- `prompt_of_prompts.md`: Criteria for prompt evaluation
- `agent_memory.json`: Persistent storage for agent memory
- `user_preferences.json`: Storage for user preferences

## How It Works

### User Preference Collection

1. Before starting the agentic flow, the system collects domain-specific preferences from the user
2. These preferences are stored in the user's profile and memory
3. The preferences are incorporated into the prompts sent to the LLM
4. The LLM uses these preferences to tailor its responses and calculations

### Tool Execution Flow

1. The LLM decides which tool to call next based on the current context, memory, and user preferences
2. The tool is executed, and its result is stored in memory
3. In the next iteration, the memory (including the tool result) is passed back to the LLM
4. The LLM uses this information to decide the next tool to call
5. This cycle continues until the calculation is complete

### Calculation Completion

The system determines that a calculation is complete when:

1. **LLM Decision**: The LLM decides no further actions are needed (returns `None` for `tool_name`)
2. **All Steps Completed**: All required calculation steps have been completed (verified by checking the calculation history)
3. **Maximum Iterations**: The maximum number of iterations has been reached (safety mechanism)

This approach allows the LLM to determine when the calculation is complete based on its understanding of the problem and the results so far, while also providing a safety mechanism to prevent infinite loops.

## Extending the Framework

### Adding New Tools

To add new MCP tools, update the `_simulate_tool_execution` method in `action.py` with your new tool implementations.

### Customizing Memory

The memory system can be extended by modifying the `Memory` class in `memory.py`.

### Changing LLM Provider

To use a different LLM provider, update the `Perception` and `DecisionMaking` classes.

### Adding New User Preferences

To add new user preferences, update the `preferences.py` file with the new preference categories and options.

### Testing Prompts

Use `prompt_test.py` to validate system prompts and user queries against the criteria defined in `prompt_of_prompts.md`.

## License

MIT
