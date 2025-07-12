import importlib

from pathlib import Path
from typing import Tuple

from .agents.planner import Action, PlannerAgent
from .config import ALLOWED_SHELL_COMMANDS
from .knowledge import KnowledgeStore
from .primitives import PrimitiveLoader


def load_constitution(root_path: Path) -> str:
    """Loads the constitution from CLAUDE.md at the project root."""
    constitution_path = root_path / "CLAUDE.md"
    if constitution_path.is_file():
        return constitution_path.read_text()
    return ""


class Orchestrator:
    """
    Drives the agentic workflow, from planning to context assembly.
    """

    def __init__(
        self, primitive_loader: PrimitiveLoader, knowledge_store: KnowledgeStore
    ):
        self.primitive_loader = primitive_loader
        self.knowledge_store = knowledge_store
        self.planner = PlannerAgent(self.primitive_loader)

    def execute_action(self, action: Action) -> str:
        """Dynamically loads and executes an action primitive."""
        try:
            # Get the entrypoint module and function from the primitive's manifest
            module_str, function_str = self.primitive_loader.get_action_entrypoint(
                action.tool_name
            )

            # Get the manifest to construct the full import path
            action_manifest = self.primitive_loader.primitives.get("actions", {}).get(
                action.tool_name
            )
            if not action_manifest:
                raise ValueError(f"Manifest for action '{action.tool_name}' not found.")

            version = action_manifest["version"]
            module_name = module_str.replace(".py", "")

            # Construct the full, correct import path for the action module
            # e.g., prp_compiler.primitives.actions.web_search.1_0_0.web_search
            import_path = (
                f"prp_compiler.primitives.actions.{action.tool_name}.v{version.replace('.', '_')}.{module_name}"
            )

            # Dynamically import the module
            action_module = importlib.import_module(import_path)

            # Get the function from the module
            action_function = getattr(action_module, function_str)

            # Execute the function with its arguments and return the result as a string
            result = action_function(**action.arguments)

            return str(result)
        except Exception as e:
            return f"[ERROR] Failed to execute action '{action.tool_name}': {e}"

    def run(self, user_goal: str, constitution: str, max_steps: int = 10) -> Tuple[str, str]:
        """Drives the main ReAct loop and assembles the final context."""
        planner_gen = self.planner.run_planning_loop(
            user_goal, constitution, max_steps=max_steps
        )
        final_context_parts = []
        final_plan_args = None
        observation = "No observation yet. Start by thinking about the user's goal."

        step = None
        while True:
            try:
                # The first call to send() must be None.
                # Subsequent calls send the observation.
                current_observation = observation if step else None
                step = planner_gen.send(current_observation)

                thought_text = (
                    f"Thought: {step.thought.reasoning}\n"
                    f"Critique: {step.thought.criticism}"
                )
                final_context_parts.append(thought_text)

                action = step.thought.next_action
                action_text = f"Action: {action.tool_name}({action.arguments})"
                final_context_parts.append(action_text)

                if action.tool_name == "finish":
                    final_plan_args = action.arguments
                    break

                observation = self.execute_action(action)
                final_context_parts.append(f"Observation: {observation}")

            except StopIteration as e:
                final_plan_args = e.value
                break
            except Exception as e:
                return (
                    "",
                    f"[ERROR] Exception in Orchestrator.run: {e}\n\n"
                    + "\n\n".join(final_context_parts),
                )

        # After the loop, assemble the final context
        if not final_plan_args:
            return (
                "",
                "[ERROR] Planner did not finish with a final plan.\n\n"
                + "\n\n".join(final_context_parts),
            )

        schema_choice = final_plan_args.get("schema_choice", "")
        schema_content = self.primitive_loader.get_primitive_content("schemas", schema_choice)
        final_context_parts.append(f"Schema: {schema_choice}\n{schema_content}")

        for pattern_ref in final_plan_args.get("pattern_references", []):
            pattern_content = self.primitive_loader.get_primitive_content(
                "patterns", pattern_ref
            )
            final_context_parts.append(
                f"Pattern: {pattern_ref}\n{pattern_content}"
            )

        final_context = "\n\n".join(final_context_parts)
        # Return the schema *name* and the assembled context.
        # The Synthesizer will use the name to load the schema itself.
        return (schema_choice, final_context)

        return (
            "",
            "[ERROR] Planner did not finish within max_steps.\n\n"
            + "\n\n".join(final_context_parts),
        )

