import json
from typing import Any, Dict, List

from ..models import Action, ReActStep, Thought
from ..primitives import PrimitiveLoader
from .base_agent import BaseAgent

REACT_PROMPT_TEMPLATE = """
You are an expert AI engineering architect. Your task is to build a context buffer by reasoning and acting in a loop to gather all necessary information to create a comprehensive PRP for the user's goal.

Your process is as follows:
1.  **Examine History:** Review the history of your previous thoughts, actions, and their resulting observations.
2.  **Think:** Based on the history and the user's goal, formulate a thought. Your thought must include `reasoning` (why this is the next logical step) and `criticism` (what are the flaws or risks of this step).
3.  **Act:** Choose one of the available tools to execute.

If you have gathered enough information to build a complete PRP, you MUST call the "finish" tool. Otherwise, continue choosing tools to build the context.

You have access to the following tools:
{tools_json_schema}

History (last entry is the most recent observation):
{history}

User's Goal: "{user_goal}"

Based on the full history above and the user's goal, what is your next thought and action? You must respond by calling one of the available tool functions.
"""

class PlannerAgent(BaseAgent):
    def __init__(
        self, primitive_loader: PrimitiveLoader, model_name: str = "gemini-1.5-pro-latest"
    ):
        super().__init__(model_name=model_name)
        self.primitive_loader = primitive_loader
        self.tools_schema = self._create_tools_schema()

    def _create_tools_schema(self) -> List[Dict[str, Any]]:
        """Dynamically builds the tools schema from PrimitiveLoader action manifests."""
        actions = self.primitive_loader.get_all('actions')

        # Add the static 'finish' action to the list of actions to be processed
        actions.append(
            {
                "name": "finish",
                "description": (
                    "Call this when you have gathered all necessary information to write the PRP."
                ),
                "inputs_schema": {
                    "type": "object",
                    "properties": {
                        "schema_choice": {
                            "type": "string",
                            "description": "The name of the final output schema.",
                        },
                        "pattern_references": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": (
                                "List of relevant pattern names to include as context."
                            ),
                        },
                    },
                    "required": ["schema_choice", "pattern_references"],
                },
            }
        )

        # Provide a built-in action for retrieving information from the
        # KnowledgeStore. This does not rely on any primitives on disk so the
        # planner always has access to it.
        actions.append(
            {
                "name": "retrieve_knowledge",
                "description": "Search the knowledge store for relevant information.",
                "inputs_schema": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query to retrieve information for.",
                        }
                    },
                    "required": ["query"],
                },
            }
        )

        gemini_tools = []
        for action in actions:
            # Start with the base schema from the manifest
            schema = action.get('inputs_schema', {'type': 'object', 'properties': {}})

            # Define the standard ReAct thought properties
            thought_properties = {
                "reasoning": {
                    "type": "string",
                    "description": (
                        "Your detailed reasoning for choosing this action. Explain why "
                        "this specific tool is the best choice right now."
                    ),
                },
                "criticism": {
                    "type": "string",
                    "description": (
                        "A critique of your own reasoning and plan. What are the flaws "
                        "in your current approach? What could go wrong?"
                    ),
                },
            }

            # Inject thought properties into the schema
            schema['properties'].update(thought_properties)

            # Ensure 'reasoning' and 'criticism' are required
            if 'required' not in schema:
                schema['required'] = []
            schema['required'].extend(["reasoning", "criticism"])

            gemini_tools.append({
                "name": action['name'],
                "description": action['description'],
                "parameters": schema
            })

        return gemini_tools

    def plan_step(
        self, user_goal: str, constitution: str, history: List[str]
    ) -> ReActStep:
        """Performs a single step of reasoning to produce a thought and an action."""
        prompt = constitution + "\n\n" + REACT_PROMPT_TEMPLATE.format(
            user_goal=user_goal,
            tools_json_schema=json.dumps(self.tools_schema, indent=2),
            history="\n".join(history),
        )

        response = self.model.generate_content(prompt, tools=self.tools_schema)
        fc_part = response.candidates[0].content.parts[0]

        if not hasattr(fc_part, "function_call"):
            raise ValueError("Planner Agent did not return a function call.")

        fc = fc_part.function_call
        action_args = dict(fc.args) if hasattr(fc, "args") else {}

        reasoning = action_args.pop("reasoning", "")
        criticism = action_args.pop("criticism", "")

        action = Action(tool_name=fc.name, arguments=action_args)

        thought = Thought(reasoning=reasoning, criticism=criticism, next_action=action)
        return ReActStep(thought=thought)
