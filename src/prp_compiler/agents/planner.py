from typing import List
import json
from .base_agent import BaseAgent
from ..models import ExecutionPlan, ManifestItem

PLANNER_PROMPT_TEMPLATE = """
You are an expert AI engineering architect. Your task is to create an execution plan for building a comprehensive Product Requirement Prompt (PRP).

**User's Goal:**
"{user_goal}"

**Available Resources:**
- **Tools:** {tools_manifest}
- **Knowledge:** {knowledge_manifest}
- **Schemas:** {schemas_manifest}

**Instructions:**
Based on the user's goal and the available resources, create an execution plan. Your output **must** be a single, valid JSON object that adheres strictly to the following structure. Do not add any extra commentary or explanations outside of the JSON object.

**Required JSON Structure:**
```json
{{
    "tool_plan": [
        {{
            "command_name": "<name_of_tool_from_manifest>",
            "arguments": "<arguments_for_the_tool>"
        }}
    ],
    "knowledge_plan": [
        "<name_of_knowledge_doc_from_manifest>"
    ],
    "schema_choice": "<name_of_schema_from_manifest>"
}}
```

**Example:**
```json
{{
    "tool_plan": [
        {{
            "command_name": "file_lister",
            "arguments": "--directory /src/components"
        }}
    ],
    "knowledge_plan": [
        "prp_best_practices"
    ],
    "schema_choice": "standard_prp"
}}
```

Now, generate the JSON execution plan based on the user's goal.
"""


class PlannerAgent(BaseAgent):
    """Agent responsible for creating an execution plan."""

    def plan(
        self,
        user_goal: str,
        tools_manifest: List[ManifestItem],
        knowledge_manifest: List[ManifestItem],
        schemas_manifest: List[ManifestItem],
    ) -> ExecutionPlan:
        """
        Generates an execution plan by calling the LLM.
        """
        # Convert manifests to JSON strings for the prompt
        tools_json = json.dumps(
            [item.model_dump() for item in tools_manifest], indent=2
        )
        knowledge_json = json.dumps(
            [item.model_dump() for item in knowledge_manifest], indent=2
        )
        schemas_json = json.dumps(
            [item.model_dump() for item in schemas_manifest], indent=2
        )

        prompt = PLANNER_PROMPT_TEMPLATE.format(
            user_goal=user_goal,
            tools_manifest=tools_json,
            knowledge_manifest=knowledge_json,
            schemas_manifest=schemas_json,
        )

        response = self.model.generate_content(prompt)
        cleaned_response = self._clean_json_response(response.text)

        # Validate and parse the response into the Pydantic model
        execution_plan = ExecutionPlan.model_validate_json(cleaned_response)
        return execution_plan
