import json
from typing import List, Dict, Any
from .base_agent import BaseAgent
from ..models import ReActStep, Thought, Action
from ..primitives import PrimitiveLoader

# This is the new, more sophisticated prompt for the ReAct loop.
REACT_PROMPT_TEMPLATE = """
You are an expert AI engineering architect. Your goal is to gather all necessary information to create a comprehensive PRP for the user's goal.
You operate in a loop of Thought -> Action -> Observation.

1.  **Thought:** First, you think about the user's goal and your plan. You critique your own plan and decide what single action to take next.
2.  **Action:** You choose one of the available tools to execute.

You have access to the following tools:
{tools_json_schema}

Your history of thoughts, actions, and observations so far:
{history}

User's Goal: "{user_goal}"

Based on your history, what is your next thought and action? If you have gathered enough information, your action should be to call the "finish" tool. Your output MUST be a single, valid JSON object that is a function call.
"""

class PlannerAgent(BaseAgent):
    def __init__(self, primitive_loader: PrimitiveLoader, model_name: str = "gemini-1.5-pro-latest"):
        super().__init__(model_name=model_name)
        self.primitive_loader = primitive_loader
        # Convert primitive manifests to Gemini-compatible tool schemas
        self.tools_schema = self._create_tools_schema()

    def _create_tools_schema(self) -> List[Dict[str, Any]]:
        # Dynamically build the tools schema from PrimitiveLoader action manifests
        gemini_tools = []
        for action in self.primitive_loader.get_all('actions'):
            gemini_tools.append({
                "name": action['name'],
                "description": action['description'],
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": action.get('arguments', '')}
                    },
                    "required": ["query"]
                }
            })
        # Add the mandatory finish tool
        gemini_tools.append({
            "name": "finish",
            "description": "Call this when you have gathered all necessary information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "schema_choice": {"type": "string", "description": "The name of the final output schema to use."},
                    "pattern_references": {"type": "array", "items": {"type": "string"}, "description": "List of pattern names to include as context."}
                },
                "required": ["schema_choice", "pattern_references"]
            }
        })
        return gemini_tools

    def run_planning_loop(self, user_goal: str, max_steps: int = 10):
        """
        Generator-based ReAct loop. Yields each Action (with Thought), expects observation via .send().
        Terminates when the "finish" tool is chosen or max_steps is reached.
        """
        history: List[ReActStep] = []
        observation = None
        for i in range(max_steps):
            prompt = REACT_PROMPT_TEMPLATE.format(
                user_goal=user_goal,
                tools_json_schema=json.dumps(self.tools_schema, indent=2),
                history="".join([
                    f"Thought: {s.thought.reasoning}\nAction: {s.thought.next_action.tool_name}\nObservation: {s.observation}\n" for s in history
                ])
            )
            response = self.model.generate_content(prompt, tools=self.tools_schema)
            fc_part = response.candidates[0].content.parts[0]
            if not hasattr(fc_part, 'function_call') or fc_part.function_call is None:
                raise ValueError("Planner Agent did not return a function call.")
            fc = fc_part.function_call
            # Parse the thought and action
            thought = Thought(
                reasoning=getattr(fc, 'thought', ''),  # adapt as needed
                criticism=getattr(fc, 'criticism', ''),
                next_action=Action(
                    tool_name=fc.name,
                    arguments=fc.args if hasattr(fc, 'args') else fc.parameters
                )
            )
            step = ReActStep(thought=thought, observation=observation)
            # Yield the action for execution, expect observation via .send()
            observation = yield step
            history.append(ReActStep(thought=thought, observation=observation))
            if thought.next_action.tool_name == "finish":
                break
        # Optionally yield the final step
        return
