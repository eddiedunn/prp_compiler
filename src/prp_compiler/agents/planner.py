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



def _convert_schema_to_gemini(data: Any) -> Any:
    """Recursively converts a standard JSON schema dict to the Gemini format."""
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if k == 'default':
                continue  # Gemini's schema doesn't support 'default'

            new_key = k
            if k == 'type':
                new_key = 'type_'
                if isinstance(v, str):
                    v = v.upper()  # "object" -> "OBJECT"
            new_dict[new_key] = _convert_schema_to_gemini(v)
        return new_dict
    if isinstance(data, list):
        return [_convert_schema_to_gemini(item) for item in data]
    return data


class PlannerAgent(BaseAgent):
    def __init__(self, primitive_loader: PrimitiveLoader, model_name: str = "gemini-1.5-pro-latest"):
        super().__init__(model_name=model_name)
        self.primitive_loader = primitive_loader
        self.actions_schema = self._create_schema_for_type("actions")
        self.strategies_schema = self._create_schema_for_type("strategies", for_selection=True)

    def _create_schema_for_type(self, primitive_type: str, for_selection: bool = False) -> List[Dict[str, Any]]:
        primitives = self.primitive_loader.get_all(primitive_type).copy()
        if for_selection:
            # For strategy selection, format for Gemini API function calling
            return [
                {
                    "function_declarations": [
                        {
                            "name": "select_strategy",
                            "description": "Select the most appropriate strategy to achieve the user's goal.",
                            "parameters": {
                                "type_": "OBJECT",
                                "properties": {
                                    "strategy_name": {
                                        "type_": "STRING",
                                        "description": "The name of the chosen strategy.",
                                        "enum": [p["name"] for p in primitives if "name" in p],
                                    },
                                    "reasoning": {
                                        "type_": "STRING",
                                        "description": "Your detailed reasoning for choosing this strategy.",
                                    },
                                    "criticism": {
                                        "type_": "STRING",
                                        "description": "A critique of your own reasoning and plan.",
                                    },
                                },
                                "required": ["strategy_name", "reasoning", "criticism"],
                            },
                        }
                    ]
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
            try:
                # 1. Load the standard JSON schema from the manifest
                schema = action.get("inputs_schema", {"type": "object", "properties": {}})

                # 2. Add the standard 'thought' properties to it
                if "properties" not in schema:
                    schema["properties"] = {}
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

                for prop in ["reasoning", "criticism"]:
                    if prop not in schema["required"]:
                        schema["required"].append(prop)

                # 3. Convert the entire, modified schema to the Gemini format
                gemini_schema = _convert_schema_to_gemini(schema)

                # 4. Create the final tool definition with the converted schema
                tool = {
                    "name": action.get("name", ""),
                    "description": action.get("description", ""),
                    "parameters": gemini_schema,
                }
                
                # Validate required fields
                if not tool["name"]:
                    print(f"Warning: Action is missing a name, skipping")
                    continue
                    
                gemini_tools.append(tool)
                
            except Exception as e:
                print(f"Error processing action {action.get('name', 'unknown')}: {str(e)}")
                print(f"Action data: {action}")
                continue
                
        print(f"\n=== DEBUG: Generated {len(gemini_tools)} tools for Gemini API ===")
        for i, tool in enumerate(gemini_tools):
            print(f"Tool {i+1}: {tool.get('name', 'unnamed')}")
            print(f"  Description: {tool.get('description', 'No description')}")
            print(f"  Parameters: {json.dumps(tool.get('parameters', {}), indent=2)}\n")
            
        return gemini_tools

    def select_strategy(self, user_goal: str, constitution: str) -> str:
        try:
            print("\n=== DEBUG: Starting select_strategy ===")
            print(f"User goal: {user_goal}")
            
            # Format the prompt
            prompt = constitution + "\n\n" + STRATEGY_SELECTION_PROMPT.format(
                user_goal=user_goal,
                strategies_json_schema=json.dumps(self.strategies_schema, indent=2).replace("{", "{{").replace("}", "}}"),
            )
            
            print("\n=== DEBUG: Sending prompt to Gemini API ===")
            print(f"Prompt length: {len(prompt)} characters")
            print(f"First 500 chars: {prompt[:500]}...")
            
            print("\n=== DEBUG: Sending tools to Gemini API ===")
            print(f"Tools schema: {json.dumps(self.strategies_schema, indent=2)}")
            
            # Call the parent's generate_content method
            response = super().generate_content(prompt, tools=self.strategies_schema)
            
            print("\n=== DEBUG: Received response from Gemini API ===")
            print(f"Response type: {type(response)}")
            
            # Debug the response structure
            if not hasattr(response, 'candidates') or not response.candidates:
                raise ValueError("No candidates in response")
                
            print(f"Number of candidates: {len(response.candidates)}")
            
            candidate = response.candidates[0]
            if not hasattr(candidate, 'content') or not hasattr(candidate.content, 'parts') or not candidate.content.parts:
                raise ValueError("Invalid response format: missing content or parts")
                
            print(f"Number of parts: {len(candidate.content.parts)}")
            
            part = candidate.content.parts[0]
            if not hasattr(part, 'function_call'):
                print(f"\n=== DEBUG: Part attributes ===")
                print(f"Part type: {type(part)}")
                print(f"Part attributes: {dir(part)}")
                if hasattr(part, 'text'):
                    print(f"Part text: {part.text}")
                raise ValueError("No function call in response")
                
            fc = part.function_call
            print(f"\n=== DEBUG: Function call details ===")
            print(f"Function name: {getattr(fc, 'name', 'N/A')}")
            print(f"Function args: {getattr(fc, 'args', {})}")
            
            if fc.name != "select_strategy":
                raise ValueError(f"Unexpected function call: {fc.name}")
                
            if not hasattr(fc, 'args') or 'strategy_name' not in fc.args:
                print(f"\n=== DEBUG: Function call args ===")
                print(f"Args: {getattr(fc, 'args', 'No args')}")
                raise ValueError("No strategy_name in function call arguments")
                
            strategy_name = fc.args["strategy_name"]
            print(f"\n=== DEBUG: Selected strategy ===")
            print(f"Strategy name: {strategy_name}")
            
            return strategy_name
            
        except Exception as e:
            print(f"\n=== DEBUG: Error in select_strategy ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("\n=== DEBUG: Full traceback ===")
            import traceback
            traceback.print_exc()
            print("==========================\n")
            raise

    def plan_step(
        self,
        user_goal: str,
        constitution: str,
        strategy_content: str,
        history: List[str],
    ) -> ReActStep:
        """Perform a single ReAct planning step using the provided strategy template."""
        # Provide the agent with a list of available patterns and schemas to prevent hallucination.
        patterns = self.primitive_loader.get_all("patterns")
        
        # Debug: Print available patterns
        print("\n=== DEBUG: Available Patterns ===")
        for p in patterns:
            print(f"- {p['name']}: {p.get('description', 'No description')}")
        
        formatted_patterns = json.dumps(
            [{"name": p["name"], "description": p["description"]} for p in patterns],
            indent=2,
        ).replace("{", "{{").replace("}", "}}")
        
        # Get available schemas for the agent to choose from
        schemas = self.primitive_loader.get_all("schemas")
        
        # Debug: Print available schemas
        print("\n=== DEBUG: Available Schemas ===")
        for s in schemas:
            print(f"- {s['name']}: {s.get('description', 'No description')}")
            
        formatted_schemas = json.dumps(
            [{"name": s["name"], "description": s.get("description", "No description available")} for s in schemas],
            indent=2,
        ).replace("{", "{{").replace("}", "}}")
        
        # Debug: Print actions schema
        print("\n=== DEBUG: Actions Schema ===")
        print(json.dumps(self.actions_schema, indent=2))

        variables = {
            "user_goal": user_goal,
            "tools_json_schema": json.dumps(self.actions_schema, indent=2).replace("{", "{{").replace("}", "}}"),
            "patterns_json_schema": formatted_patterns,
            "schemas_json_schema": formatted_schemas,
            "history": "\n".join(history),
        }
        try:
            strategy_prompt = strategy_content.format(**variables)
        except KeyError as e:
            raise ValueError(f"Missing template variable {e} in strategy template")
        prompt = constitution + "\n\n" + strategy_prompt

        # Debug: Print the prompt being sent to the model
        print("\n=== DEBUG: Sending prompt to Gemini API ===")
        print(prompt[:1000] + "..." if len(prompt) > 1000 else prompt)
        print("=== END PROMPT ===\n")

        try:
            # Use the parent class's generate_content method to ensure debug logging
            response = super().generate_content(prompt, tools=self.actions_schema)
            
            # Debug: Print the raw response
            print("\n=== DEBUG: Raw response from Gemini API ===")
            print(f"Response type: {type(response)}")
            print(f"Response dir: {dir(response)}")
            if hasattr(response, 'candidates'):
                print(f"Number of candidates: {len(response.candidates) if response.candidates else 0}")
                if response.candidates:
                    print(f"First candidate type: {type(response.candidates[0])}")
                    print(f"First candidate dir: {dir(response.candidates[0])}")
                    if hasattr(response.candidates[0], 'content'):
                        print(f"Content type: {type(response.candidates[0].content)}")
                        print(f"Content dir: {dir(response.candidates[0].content)}")
                        if hasattr(response.candidates[0].content, 'parts'):
                            print(f"Number of parts: {len(response.candidates[0].content.parts) if response.candidates[0].content.parts else 0}")
                            if response.candidates[0].content.parts:
                                print(f"First part type: {type(response.candidates[0].content.parts[0])}")
                                print(f"First part dir: {dir(response.candidates[0].content.parts[0])}")
            print("=== END RESPONSE ===\n")

            if not hasattr(response, 'candidates') or not response.candidates:
                raise ValueError("No candidates in response from Gemini API")
                
            # Find the part that contains the function call, as it may not be the first one.
            fc_part = None
            for part in response.candidates[0].content.parts:
                if part.function_call and part.function_call.name:
                    fc_part = part
                    break

            if not fc_part:
                # Debug: Print the actual content of the part to help diagnose the issue
                print("\n=== DEBUG: No function_call in response part ===")
                for i, p in enumerate(response.candidates[0].content.parts):
                    print(f"Part {i}: {p}")
                print("=== END DEBUG ===\n")
                raise ValueError("Planner Agent did not return a function call. Check the debug output for the actual response.")
                
            fc = fc_part.function_call
            
            # Debug: Print the function call details
            print("\n=== DEBUG: Function call details ===")
            print(f"Function call object type: {type(fc)}")
            print(f"Function call attributes: {dir(fc)}")
            print(f"Function name: {getattr(fc, 'name', 'N/A')}")
            print(f"Function args type: {type(getattr(fc, 'args', {}))}")
            print(f"Function args: {getattr(fc, 'args', {})}")
            print("=== END DEBUG ===\n")
            
            # Extract function name and arguments with better error handling
            try:
                func_name = getattr(fc, 'name', None)
                if not func_name:
                    raise ValueError("Function name not found in function call")
                
                action_args = dict(getattr(fc, 'args', {}))
                reasoning = action_args.pop("reasoning", "")
                criticism = action_args.pop("criticism", "")
                
                # Debug: Print the action and thought before creating objects
                print("\n=== DEBUG: Creating Action and Thought objects ===")
                print(f"Action - tool_name: {func_name}, arguments: {action_args}")
                print(f"Thought - reasoning: {reasoning}, criticism: {criticism}")
                print("=== END DEBUG ===\n")
                
                # Create the Action and Thought objects
                action = Action(tool_name=func_name, arguments=action_args)
                thought = Thought(reasoning=reasoning, criticism=criticism, next_action=action)
                
                # Debug: Print the ReActStep before returning
                print("\n=== DEBUG: Created ReActStep ===")
                print(f"ReActStep - thought: {thought}")
                print("=== END DEBUG ===\n")
                
                return ReActStep(thought=thought)
                
            except Exception as e:
                print("\n=== DEBUG: Error creating Action/Thought ===")
                print(f"Error type: {type(e).__name__}")
                print(f"Error message: {str(e)}")
                print("=== END DEBUG ===\n")
                raise
            
        except Exception as e:
            # Debug: Print the full error details
            print("\n=== DEBUG: Error in plan_step ===")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print("=== END DEBUG ===\n")
            raise  # Re-raise the exception after logging
