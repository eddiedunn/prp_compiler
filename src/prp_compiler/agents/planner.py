import json
from typing import Any, Dict, List

from ..models import Action, ReActStep, Thought
from ..primitives import PrimitiveLoader
from .base_agent import BaseAgent

# This is the new, more sophisticated prompt for the ReAct loop.
REACT_PROMPT_TEMPLATE = """
You are an expert AI engineering architect. Your goal is to gather all necessary
information to create a comprehensive PRP for the user's goal.
You operate in a loop of Thought -> Action -> Observation.

1.  **Thought:** Think about the user's goal, your plan so far, and critique
    your own reasoning.
    Record both your reasoning and any self-criticism.
2.  **Action:** Choose one of the available tools to execute.
    When you have enough information, call the "finish" tool.

You MUST include your reasoning and criticism as fields in the arguments
of every function call (including finish).

You have access to the following tools:
{tools_json_schema}

Your history of thoughts, actions, and observations so far:
{history}

User's Goal: "{user_goal}"

Based on your history, what is your next thought and action?
Respond with a single function call, with reasoning and 
criticism included in the arguments.
"""


class PlannerAgent(BaseAgent):
    def __init__(
        self,
        primitive_loader: PrimitiveLoader,
        model_name: str = "gemini-1.5-pro-latest",
    ):
        super().__init__(model_name=model_name)
        self.primitive_loader = primitive_loader
        # Convert primitive manifests to Gemini-compatible tool schemas
        self.tools_schema = self._create_tools_schema()

    def _create_tools_schema(self) -> List[Dict[str, Any]]:
        # Dynamically build the tools schema from PrimitiveLoader action manifests
        gemini_tools = []
        for action in self.primitive_loader.get_all("actions"):
            gemini_tools.append(
                {
                    "name": action["name"],
                    "description": action["description"],
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": action.get("arguments", ""),
                            },
                            "reasoning": {
                                "type": "string",
                                "description": (
                                    "Your reasoning for choosing this action. "
                                    "Please provide a clear explanation."
                                ),
                            },
                            "criticism": {
                                "type": "string",
                                "description": (
                                    "Self-criticism or uncertainty about this step. "
                                    "Please provide any concerns or doubts."
                                ),
                            },
                        },
                        "required": ["query", "reasoning", "criticism"],
                    },
                }
            )
        # Add the mandatory finish tool
        gemini_tools.append(
            {
                "name": "finish",
                "description": (
                    "Call this when you have gathered all necessary information. "
                    "Please ensure you have completed all required steps."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "reasoning": {
                            "type": "string",
                            "description": (
                                "Your final reasoning for why the context is "
                                "complete."
                            ),
                        },
                        "criticism": {
                            "type": "string",
                            "description": "Any final self-criticism or uncertainties.",
                        },
                        "schema_choice": {
                            "type": "string",
                            "description": (
                                "The name of the final output schema to use."
                            ),
                        },
                        "pattern_references": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "List of pattern names to include as context."
                            ),
                        },
                    },
                    "required": [
                        "reasoning",
                        "criticism",
                        "schema_choice",
                        "pattern_references",
                    ],
                },
            }
        )
        return gemini_tools

    def run_planning_loop(self, user_goal: str, max_steps: int = 10):
        """
        Generator-based ReAct loop. Yields each Action (with Thought),
        expects observation via .send().
        Terminates when the "finish" tool is chosen or max_steps is reached.
        """
        history: List[ReActStep] = []
        observation = None
        for i in range(max_steps):
            prompt = REACT_PROMPT_TEMPLATE.format(
                user_goal=user_goal,
                tools_json_schema=json.dumps(self.tools_schema, indent=2),
                history="".join(
                    [
                        (f"Thought: {s.thought.reasoning}\n"
 f"Action: {s.thought.next_action.tool_name}\n"
 f"Observation: {s.observation}\n")
                        for s in history
                    ]
                ),
            )
            response = self.model.generate_content(prompt, tools=self.tools_schema)
            fc_part = response.candidates[0].content.parts[0]
            if not hasattr(fc_part, "function_call") or fc_part.function_call is None:
                raise ValueError("Planner Agent did not return a function call.")
            fc = fc_part.function_call
            # Parse the thought and action
            # Parse reasoning and criticism from function call arguments
            fc_args = fc.args if hasattr(fc, "args") else fc.parameters
            reasoning = fc_args.get("reasoning", "")
            criticism = fc_args.get("criticism", "")
            # Remove reasoning/criticism from arguments passed to the tool
            action_args = {
                k: v for k, v in fc_args.items() if k not in ("reasoning", "criticism")
            }
            thought = Thought(
                reasoning=reasoning,
                criticism=criticism,
                next_action=Action(tool_name=fc.name, arguments=action_args),
            )
            step = ReActStep(thought=thought, observation=observation)
            # Yield the action for execution, expect observation via .send()
            observation = yield step
            history.append(ReActStep(thought=thought, observation=observation))
            if thought.next_action.tool_name == "finish":
                break
        # Optionally yield the final step
        return
