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
        """
        Loads an action's template, fills its arguments, and resolves dynamic content.
        """
        try:
            # 1. Get the raw template content from the loader
            raw_template = self.primitive_loader.get_primitive_content(
                "actions", action.tool_name
            )

            # 2. Substitute arguments into the template (simple string replacement)
            # A more robust solution might use a proper templating engine
            context_with_args = raw_template
            for key, value in action.arguments.items():
                context_with_args = context_with_args.replace(
                    f"$ARGUMENTS[{key}]", str(value)
                )

            # 3. Resolve dynamic content like ! and @
            resolved_content = self._resolve_dynamic_content(context_with_args)
            return resolved_content
        except Exception as e:
            return f"[ERROR] Failed to execute action '{action.tool_name}': {e}"

        except (ImportError, AttributeError, TypeError, Exception) as e:
            return f"[ERROR] Failed to execute action '{action.tool_name}': {e}"

    def run(self, user_goal: str, constitution: str, max_steps: int = 10) -> Tuple[str, str]:
        """Drives the main ReAct loop and assembles the final context."""
        planner_gen = self.planner.run_planning_loop(
            user_goal, constitution, max_steps=max_steps
        )
        final_context_parts = []
        final_plan_args = None
        observation = "No observation yet. Start by thinking about the user's goal."

        next(planner_gen)  # Prime the generator to its first yield.

        while True:
            try:
                step = planner_gen.send(observation)

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
        return (schema_content, final_context)

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
