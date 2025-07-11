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

Based on your history, what is your next thought and action? If you have gathered enough information, your action should be to call the "finish" tool.
"""

class PlannerAgent(BaseAgent):
    def __init__(self, primitive_loader: PrimitiveLoader, model_name: str = "gemini-1.5-pro-latest"):
        super().__init__(model_name=model_name)
        self.primitive_loader = primitive_loader
        # Convert primitive manifests to Gemini-compatible tool schemas
        self.tools_schema = self._create_tools_schema()

    def _create_tools_schema(self) -> List[Dict[str, Any]]:
        # Logic to convert your action manifests into the OpenAPI schema Gemini expects.
        # For now, we can hardcode a few for the purpose of this implementation.
        return [
            {
                "name": "retrieve_knowledge",
                "description": "Retrieve chunks of curated knowledge documents relevant to a query.",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
            {
                "name": "web_search",
                "description": "Performs a web search.",
                "parameters": {"type": "object", "properties": {"query": {"type": "string"}}},
            },
            {
                "name": "finish",
                "description": "Call this when you have gathered all necessary information and are ready to finalize the PRP.",
                "parameters": {"type": "object", "properties": {"schema_choice": {"type": "string"}, "pattern_references": {"type": "array", "items": {"type": "string"}}}}
            }
        ]

    def run_planning_loop(self, user_goal: str, max_steps: int = 10) -> List[ReActStep]:
        history: List[ReActStep] = []
        for i in range(max_steps):
            prompt = REACT_PROMPT_TEMPLATE.format(
                user_goal=user_goal,
                tools_json_schema=json.dumps(self.tools_schema, indent=2),
                history="".join([
                    f"Thought: {s.thought.reasoning}\nObservation: {s.observation}\n" for s in history
                ])
            )
            # Make the API call with tool-calling enabled
            response = self.model.generate_content(prompt, tools=self.tools_schema)
            # Extract the function call from the response
            fc = response.candidates[0].content.parts[0].function_call
            # Parse the thought and action
            thought = Thought(
                reasoning=f"Step {i+1}",
                criticism="N/A",
                next_action=Action(tool_name=fc.name, arguments=dict(fc.args))
            )
            step = ReActStep(thought=thought)
            history.append(step)
            # If the agent decides to finish, break the loop
            if step.thought.next_action is not None and step.thought.next_action.tool_name == "finish":
                break
            # NOTE: We are NOT executing the action here. We are just yielding it.
            # The Orchestrator will execute it and feed the observation back in.
            # For this PRP, we will just return the history of decisions.
        return history
