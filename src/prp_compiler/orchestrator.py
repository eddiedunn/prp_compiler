import importlib
from pathlib import Path
from typing import Tuple

from .agents.planner import Action, PlannerAgent
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
        """Dynamically loads and executes an action primitive from its file path."""
        try:
            # Built-in retrieval bypasses the primitive loader and directly
            # queries the KnowledgeStore.
            if action.tool_name == "retrieve_knowledge":
                query = action.arguments.get("query", "")
                chunks = self.knowledge_store.retrieve(query)
                return "\n".join(chunks)

            actions = self.primitive_loader.primitives.get("actions", {})
            action_manifest = actions.get(action.tool_name)
            if not action_manifest:
                raise ValueError(f"Action '{action.tool_name}' not found in manifest.")

            # The entrypoint is now 'module.py:function'
            module_str, function_str = action_manifest["entrypoint"].split(":")
            # The base_path from the manifest gives us the versioned directory
            entrypoint_path = Path(action_manifest["base_path"]) / module_str

            # Use importlib.util to load the module from its path
            spec = importlib.util.spec_from_file_location(
                action.tool_name, entrypoint_path
            )
            if not spec or not spec.loader:
                raise ImportError(f"Could not create module spec for {entrypoint_path}")

            action_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(action_module)

            action_function = getattr(action_module, function_str)

            # Execute the function with its arguments and return the result as a string
            result = action_function(**action.arguments)

            return str(result)
        except Exception as e:
            return f"[ERROR] Failed to execute action '{action.tool_name}': {e}"

    def run(
        self, user_goal: str, constitution: str, max_steps: int = 10
    ) -> Tuple[str, str]:
        """Drives the main ReAct loop and assembles the final context."""
        history = [
            "Observation: No observation yet. Start by thinking about the user's goal."
        ]
        final_context_parts = list(history)
        final_plan_args = None

        for i in range(max_steps):
            try:
                step = self.planner.plan_step(user_goal, constitution, history)

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
                observation_text = f"Observation: {observation}"
                final_context_parts.append(observation_text)

                # Update history for the next step
                history.append(thought_text)
                history.append(action_text)
                history.append(observation_text)

            except Exception as e:
                return (
                    "",
                    f"[ERROR] Exception in Orchestrator.run: {e}\n\n"
                    + "\n\n".join(final_context_parts),
                )
        else:  # This 'else' belongs to the 'for' loop
            return (
                "",
                "[ERROR] Planner did not finish within max_steps.\n\n"
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
        schema_content = self.primitive_loader.get_primitive_content(
            "schemas", schema_choice
        )
        final_context_parts.append(f"Schema: {schema_choice}\n{schema_content}")

        for pattern_ref in final_plan_args.get("pattern_references", []):
            pattern_content = self.primitive_loader.get_primitive_content(
                "patterns", pattern_ref
            )
            final_context_parts.append(
                f"Pattern: {pattern_ref}\n{pattern_content}"
            )

        final_context = "\n\n".join(final_context_parts)
        return (schema_choice, final_context)

