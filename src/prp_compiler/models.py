from pydantic import BaseModel, Field
from typing import List, Dict, Any


class ManifestItem(BaseModel):
    name: str
    description: str
    arguments: str | None = None
    keywords: List[str] = Field(default_factory=list)
    file_path: str


class Action(BaseModel):
    tool_name: str = Field(description="The name of the tool/action to be executed.")
    arguments: dict = Field(description="The arguments for the tool, as a dictionary.")

class Thought(BaseModel):
    reasoning: str = Field(description="The agent's reasoning for choosing the current action.")
    criticism: str = Field(description="Self-criticism of the plan.")
    next_action: Action

class ReActStep(BaseModel):
    thought: Thought
    observation: str | None = None  # Result from the executed action

class PRPOutput(BaseModel):
    goal: str = Field(description="The high-level goal of the PRP.")
    why: str = Field(description="The justification and business value.")
    what: Dict[str, Any] = Field(description="The technical requirements and success criteria.")
    context: Dict[str, Any] = Field(description="All assembled context, including documentation references and code patterns.")
    implementation_blueprint: Dict[str, Any] = Field(description="The step-by-step implementation plan.")
    validation_loop: Dict[str, Any] = Field(description="The validation gates for the agent to use.")
