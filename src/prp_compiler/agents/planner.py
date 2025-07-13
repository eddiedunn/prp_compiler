import json
from typing import Any, Dict, List

from ..models import Action, ReActStep, Thought
from ..primitives import PrimitiveLoader
from .base_agent import BaseAgent

STRATEGY_SELECTION_PROMPT = """
You are an expert AI engineering architect. Your first task is to select the best strategy for generating a PRP based on the user's goal.

User's Goal: "{user_goal}"

Available Strategies:
{strategies_json_schema}

Based on the user's goal, which strategy is most appropriate? Call the `select_strategy` function with the name of your chosen strategy.
"""

REACT_PROMPT_TEMPLATE = """
You are an expert AI engineering architect. Your task is to build a context buffer by reasoning and acting in a loop.

**Your Overarching Strategy:**
---
{strategy_content}
---

**Your Goal:** "{user_goal}"

**Available Tools:**
{tools_json_schema}

**History (last entry is the most recent observation):**
{history}

Based on your strategy and the history, what is your next thought and action? You must respond by calling one of the available tool functions.
"""


class PlannerAgent(BaseAgent):
    def __init__(self, primitive_loader: PrimitiveLoader, model_name: str = "gemini-1.5-pro-latest"):
        super().__init__(model_name=model_name)
        self.primitive_loader = primitive_loader
        self.actions_schema = self._create_schema_for_type("actions")
        self.strategies_schema = self._create_schema_for_type("strategies", for_selection=True)

    def _create_schema_for_type(self, primitive_type: str, for_selection: bool = False) -> List[Dict[str, Any]]:
        primitives = self.primitive_loader.get_all(primitive_type)
        if for_selection:
            return [
                {
                    "name": "select_strategy",
                    "description": "Select the most appropriate strategy to achieve the user's goal.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_name": {
                                "type": "string",
                                "description": "The name of the chosen strategy.",
                                "enum": [p["name"] for p in primitives],
                            }
                        },
                        "required": ["strategy_name"],
                    },
                }
            ]

        actions = primitives
        actions.append(
            {
                "name": "finish",
                "description": "Call this when you have gathered all necessary information to write the PRP.",
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
                            "description": "List of relevant pattern names to include as context.",
                        },
                    },
                    "required": ["schema_choice", "pattern_references"],
                },
            }
        )

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
            schema = action.get("inputs_schema", {"type": "object", "properties": {}})
            thought_properties = {
                "reasoning": {
                    "type": "string",
                    "description": "Your detailed reasoning for choosing this action. Explain why this specific tool is the best choice right now.",
                },
                "criticism": {
                    "type": "string",
                    "description": "A critique of your own reasoning and plan. What are the flaws in your current approach? What could go wrong?",
                },
            }
            schema["properties"].update(thought_properties)
            if "required" not in schema:
                schema["required"] = []
            schema["required"].extend(["reasoning", "criticism"])
            gemini_tools.append({
                "name": action["name"],
                "description": action["description"],
                "parameters": schema,
            })
        return gemini_tools

    def select_strategy(self, user_goal: str, constitution: str) -> str:
        prompt = constitution + "\n\n" + STRATEGY_SELECTION_PROMPT.format(
            user_goal=user_goal,
            strategies_json_schema=json.dumps(self.strategies_schema, indent=2),
        )
        response = self.model.generate_content(prompt, tools=self.strategies_schema)
        fc = response.candidates[0].content.parts[0].function_call
        if fc.name != "select_strategy":
            raise ValueError("Planner failed to select a strategy.")
        return fc.args["strategy_name"]

    def plan_step(self, user_goal: str, constitution: str, strategy_content: str, history: List[str]) -> ReActStep:
        prompt = constitution + "\n\n" + REACT_PROMPT_TEMPLATE.format(
            user_goal=user_goal,
            strategy_content=strategy_content,
            tools_json_schema=json.dumps(self.actions_schema, indent=2),
            history="\n".join(history),
        )
        response = self.model.generate_content(prompt, tools=self.actions_schema)
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
