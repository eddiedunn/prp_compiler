from pydantic import BaseModel, Field
from typing import List


class ManifestItem(BaseModel):
    name: str
    description: str
    arguments: str | None = None
    keywords: List[str] = Field(default_factory=list)
    file_path: str


class ToolPlanItem(BaseModel):
    command_name: str
    arguments: str


class ExecutionPlan(BaseModel):
    tool_plan: List[ToolPlanItem]
    knowledge_plan: List[str]
    schema_choice: str


class Action(BaseModel):
    tool_name: str = Field(description="The name of the tool/action to be executed.")
    arguments: dict = Field(description="The arguments for the tool, as a dictionary.")

class Thought(BaseModel):
    reasoning: str = Field(description="The agent's reasoning for choosing the current action.")
    criticism: str = Field(description="Self-criticism of the plan.")
    next_action: Action | None = Field(description="The next action to take, or null if the plan is complete.")

class ReActStep(BaseModel):
    thought: Thought
    observation: str | None = None  # Result from the executed action
