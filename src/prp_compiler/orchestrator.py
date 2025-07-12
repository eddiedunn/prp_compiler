import importlib
import re
import shlex
import subprocess
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
        """Dynamically loads and executes an action based on the primitive manifest."""
        try:
            try:
                # Try to fetch manifest from primitives dict
                action_primitive = (
                    self.primitive_loader.primitives.get("actions", {})
                    .get(action.tool_name)
                )

                if not action_primitive:
                    return (
                        f"[ERROR] Action '{action.tool_name}' not found in manifest."
                    )
                entrypoint = action_primitive["entrypoint"]
            except Exception as e:
                return (
                    f"[ERROR] Could not fetch action primitive for "
                    f"'{action.tool_name}': {e}"
                )
            parts = entrypoint.split(":")
            module_path = parts[0]

            action_function = None

            # Case 1: Entrypoint is a method on a class (e.g.,
            # 'module:ClassName:method_name'). This is a simplification.
            # A real implementation would need a more robust way to map
            # class names to the correct instance.
            if len(parts) == 3:
                class_name, method_name = parts[1], parts[2]
                if class_name == "KnowledgeStore":
                    instance = self.knowledge_store
                    action_function = getattr(instance, method_name)
                else:
                    # If other classes with actions are added, they need
                    # to be handled here.
                    return (
                        f"[ERROR] Unknown class '{class_name}' in entrypoint "
                        "for action '{action.tool_name}'. "
                        "This error indicates that the class is not properly "
                        "handled in this code. "
                        "Please add a handler for this class."
                    )

            # Case 2: Entrypoint is a standalone function (e.g., 'module:function_name')
            elif len(parts) == 2:
                function_name = parts[1]
                action_module = importlib.import_module(module_path)
                action_function = getattr(action_module, function_name)

            else:
                return (
                    f"[ERROR] Invalid entrypoint format for action "
                    f"'{action.tool_name}'."
                )

            if not action_function:
                return (
                    f"[ERROR] Could not resolve action function for "
                    f"'{action.tool_name}'."
                )

            # Execute the action
            result = action_function(**action.arguments)
            return str(result)

        except (ImportError, AttributeError, TypeError, Exception) as e:
            return f"[ERROR] Failed to execute action '{action.tool_name}': {e}"

    def run(self, user_goal: str, max_steps: int = 10) -> Tuple[str, str]:
        """Drives the main ReAct loop and assembles the final context."""
        planner_gen = self.planner.run_planning_loop(user_goal, max_steps=max_steps)
        final_context_parts = []
        final_plan_args = None
        observation = "No observation yet. Start by thinking about the user's goal."

        try:
            # Prime the generator to get the first step
            step = next(planner_gen)

            for _ in range(max_steps):
                thought_text = (
                    f"Thought: {step.thought.reasoning}\n"
                    f"Critique: {step.thought.criticism}"
                )
                final_context_parts.append(thought_text)
                # logging.info(thought_text)

                action = step.thought.next_action
                action_text = f"Action: {action.tool_name}({action.arguments})"
                final_context_parts.append(action_text)
                # logging.info(action_text)

                # Execute the action and send observation back
                observation = self.execute_action(action)
                step = planner_gen.send(observation)

            # After the loop, assemble the final context
            if not final_plan_args:
                return (
                    "",
                    "[ERROR] Planner did not finish with a final plan.\n\n"
                    + "\n\n".join(final_context_parts),
                )

            schema_choice = final_plan_args.get("schema_choice", "")
            _ = self.primitive_loader.get_primitive_content("schemas", schema_choice)
            for pattern_ref in final_plan_args.get("pattern_references", []):
                pattern_content = self.primitive_loader.get_primitive_content(
                    "patterns", pattern_ref
                )
                final_context_parts.append(
                    f"Pattern: {pattern_ref}\n{pattern_content}"
                )
            final_context = "\n\n".join(final_context_parts)
            return (final_context, "")

        except Exception as e:
            return (
                "",
                f"[ERROR] Exception in Orchestrator.run: {e}\n\n"
                + "\n\n".join(final_context_parts),
            )

        return (
            "",
            "[ERROR] Planner did not finish within max_steps.\n\n"
            + "\n\n".join(final_context_parts),
        )

    def _resolve_callback(self, match: re.Match) -> str:
        """
        Callback function for re.sub to handle dynamic content resolution.
        """
        prefix = match.group(1)
        command_or_path = match.group(2).strip()

        if prefix == "!":
            try:
                # Split command to avoid shell=True
                command_parts = shlex.split(command_or_path)

                # SECURITY: Check if the command is in the allowlist
                if (
                    not command_parts
                    or command_parts[0] not in ALLOWED_SHELL_COMMANDS
                ):
                    return (
                        f"[ERROR: Command '{command_parts[0] if command_parts else ''}' "
                        "is not in the allowlist.\n"
                        "This error indicates that the command is not properly "
                        f"configured for '{command_parts[0] if command_parts else ''}'.\n"
                        "Please add the command to the allowlist.\n"
                        f"The command was: {command_or_path}"
                    )
                print(f"Executing command: {command_parts}")
                result = subprocess.run(
                    command_parts,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30,
                )
                return result.stdout.strip()
            except Exception as e:
                return f"[ERROR: Command '{command_or_path}' failed: {e}]"
        elif prefix == "@":
            file_path = Path(command_or_path)
            try:
                if not file_path.is_file():
                    return f"[ERROR: File not found at '{command_or_path}']"
                return file_path.read_text()
            except Exception as e:
                return f"[ERROR: Could not read file at '{command_or_path}': {e}]"

    def _resolve_dynamic_content(self, raw_context: str) -> str:
        """
        Resolves dynamic content placeholders in a string.
        - `!command` is replaced by the stdout of the executed shell command.
        - `@path/to/file` is replaced by the content of the file.
        """
        # It captures the prefix (! or @) and the command/path.
        pattern = re.compile(r"([!@])\s*([^\n]+)")
        return pattern.sub(self._resolve_callback, raw_context)
