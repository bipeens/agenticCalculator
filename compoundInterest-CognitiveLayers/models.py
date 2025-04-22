from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum

class UserPreference(BaseModel):
    """User preferences for the agent's behavior"""
    agent_name: str = Field(..., description="Name of the agent")
    personality: str = Field(..., description="Personality traits of the agent")
    response_style: str = Field(..., description="Style of responses (formal, casual, etc.)")
    memory_retention: int = Field(..., description="Number of previous interactions to remember", ge=1, le=100)

class MemoryEntry(BaseModel):
    """Single entry in the agent's memory"""
    timestamp: str = Field(..., description="ISO format timestamp of the memory")
    interaction_type: str = Field(..., description="Type of interaction (user_input, tool_call, etc.)")
    content: Dict[str, Any] = Field(..., description="Content of the memory")
    importance: int = Field(..., description="Importance score of the memory", ge=1, le=10)

class AgentMemory(BaseModel):
    """Complete memory state of the agent"""
    entries: List[MemoryEntry] = Field(default_factory=list)
    current_context: Dict[str, Any] = Field(default_factory=dict)

class PerceptionInput(BaseModel):
    """Input for the perception module"""
    user_input: str = Field(..., description="Raw user input")
    context: Dict[str, Any] = Field(default_factory=dict)

class PerceptionOutput(BaseModel):
    """Output from the perception module"""
    processed_input: str = Field(..., description="Processed user input")
    intent: str = Field(..., description="Detected intent of the user")
    entities: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(..., description="Confidence score of the perception", ge=0.0, le=1.0)

class DecisionInput(BaseModel):
    """Input for the decision-making module"""
    perception: PerceptionOutput
    memory: AgentMemory
    available_tools: List[str] = Field(..., description="List of available MCP tools")

class DecisionOutput(BaseModel):
    """Output from the decision-making module"""
    next_action: str = Field(..., description="Next action to take")
    tool_name: Optional[str] = Field(None, description="Name of the tool to use if applicable")
    tool_args: Dict[str, Any] = Field(default_factory=dict)
    reasoning: str = Field(..., description="Reasoning behind the decision")

class ActionInput(BaseModel):
    """Input for the action module"""
    decision: DecisionOutput
    context: Dict[str, Any] = Field(default_factory=dict)

class ActionOutput(BaseModel):
    """Output from the action module"""
    success: bool = Field(..., description="Whether the action was successful")
    result: Dict[str, Any] = Field(..., description="Result of the action")
    error: Optional[str] = Field(None, description="Error message if action failed") 