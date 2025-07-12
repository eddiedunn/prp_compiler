import json
from typing import List, Dict, Any, Generator

from .base_agent import BaseAgent
from ..models import ReActStep, Thought, Action
from ..primitives import PrimitiveLoader

REACT_PROMPT_TEMPLATE = """
You are an expert AI engineering architect. Your goal is to gather all necessary information to create a comprehensive PRP for the user's goal.
You operate in a loop of Thought -> Action -> Observation.

1.  **Thought:** In your 'reasoning', analyze the user's goal and the history of your previous steps. In your 'criticism', critique your own reasoning to find flaws.
2.  **Action:** Based on your thought, choose one of the available tools to execute. When you have gathered enough context to build a complete PRP, you MUST call the "finish" tool.

You have access to the following tools:
{tools_json_schema}

Your history of thoughts, actions, and observations so far (the last entry is the most recent):
{history}

User's Goal: "{user_goal}"

Based on your history and the user's goal, what is your next thought and action? You must respond by calling one of the available tool functions.
"""

class PlannerAgent(BaseAgent):
    def __init__(self, primitive_loader: PrimitiveLoader, model_name: str = "gemini-1.5-pro-latest"):
        super().__init__(model_name=model_name)
        self.primitive_loader = primitive_loader
        self.tools_schema = self._create_tools_schema()

    def _create_tools_schema(self) -> List[Dict[str, Any]]:
        """Dynamically builds the tools schema from PrimitiveLoader action manifests for Gemini."""
        gemini_tools = []
        for action in self.primitive_loader.get_all('actions'):
            gemini_tools.append({
                "name": action['name'],
                "description": action['description'],
                "parameters": action.get('inputs_schema', {"type": "object", "properties": {}})
            })

        gemini_tools.append({
            "name": "finish",
            "description": "Call this when you have gathered all necessary information to write the PRP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "schema_choice": {"type": "string", "description": "The name of the final output schema to use."},
                    "pattern_references": {"type": "array", "items": {"type": "string"}, "description": "List of relevant pattern names to include as context."}
                },
                "required": ["schema_choice", "pattern_references"]
            }
        })
        return gemini_tools

    def run_planning_loop(self, user_goal: str, constitution: str, max_steps: int = 10) -> Generator[Action, str, dict]:
        """Drives the ReAct loop, yielding each action and receiving observations."""
        history = []
        for i in range(max_steps):
            prompt = constitution + "\n\n" + REACT_PROMPT_TEMPLATE.format(
                user_goal=user_goal,
                tools_json_schema=json.dumps(self.tools_schema, indent=2),
                history="\n".join(history)
            )

            response = self.model.generate_content(prompt, tools=self.tools_schema)
            fc_part = response.candidates[0].content.parts[0]

            if not hasattr(fc_part, 'function_call'):
                raise ValueError("Planner Agent did not return a function call.")

            fc = fc_part.function_call
            action_args = dict(fc.args) if hasattr(fc, 'args') else {}

            action = Action(tool_name=fc.name, arguments=action_args)
            
            # The 'finish' action terminates the loop and returns the final arguments.
            if action.tool_name == "finish":
                return action.arguments

            # Yield the action and wait for the orchestrator to send back the observation.
            observation = yield action
            history.append(f"Action: {action.tool_name}({action.arguments})\nObservation: {observation}")
        
        raise RuntimeError("Planner exceeded max steps without calling 'finish'.")
