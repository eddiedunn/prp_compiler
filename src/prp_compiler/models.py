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
