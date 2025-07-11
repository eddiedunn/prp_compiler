import re
import shlex
import subprocess
from pathlib import Path

from typing import List, Tuple
from .config import ALLOWED_SHELL_COMMANDS
from .models import ManifestItem, ExecutionPlan


def load_constitution(root_path: Path) -> str:
    """Loads the constitution from CLAUDE.md at the project root."""
    constitution_path = root_path / "CLAUDE.md"
    if constitution_path.is_file():
        return constitution_path.read_text()
    return ""


class Orchestrator:
    """
    Orchestrates the execution of tasks, including resolving dynamic content.
    """

    def __init__(
        self,
        tools_manifest: List[ManifestItem],
        knowledge_manifest: List[ManifestItem],
        schemas_manifest: List[ManifestItem],
    ):
        """Initializes the Orchestrator with manifests for lookup."""
        self.tools_manifest = {item.name: item for item in tools_manifest}
        self.knowledge_manifest = {item.name: item for item in knowledge_manifest}
        self.schemas_manifest = {item.name: item for item in schemas_manifest}

    def assemble_context(self, plan: ExecutionPlan) -> Tuple[str, str]:
        """
        Assembles the context from the execution plan by reading the full content
        of all specified files, concatenating them, and resolving dynamic content.

        Returns the schema template and the fully resolved context string.
        """
        # 1. Find and read the content of the chosen schema file.
        if not plan.schema_choice or plan.schema_choice not in self.schemas_manifest:
            raise ValueError(f"Schema '{plan.schema_choice}' not found in manifest.")
        schema_item = self.schemas_manifest[plan.schema_choice]
        schema_template = Path(schema_item.file_path).read_text()

        context_parts = []

        # 2. Iterate through the knowledge_plan and read file content.
        for knowledge_name in plan.knowledge_plan:
            if knowledge_name in self.knowledge_manifest:
                knowledge_item = self.knowledge_manifest[knowledge_name]
                context_parts.append(Path(knowledge_item.file_path).read_text())
            else:
                print(f"[WARNING] Knowledge '{knowledge_name}' not found in manifest.")

        # 3. Iterate through the tool_plan and read file content.
        for tool_plan_item in plan.tool_plan:
            command_name = tool_plan_item.command_name
            if command_name in self.tools_manifest:
                tool_item = self.tools_manifest[command_name]
                context_parts.append(Path(tool_item.file_path).read_text())
            else:
                print(f"[WARNING] Tool '{command_name}' not found in manifest.")

        # 4. Concatenate all content into a single string.
        assembled_context = "\n\n---\n\n".join(context_parts)

        # 5. Resolve any dynamic content (e.g., !commands or @files) in the combined string.
        resolved_context = self._resolve_dynamic_content(assembled_context)

        # 6. Return the schema and the resolved context.
        return schema_template, resolved_context

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
                if not command_parts or command_parts[0] not in ALLOWED_SHELL_COMMANDS:
                    return f"[ERROR: Command '{command_parts[0] if command_parts else ''}' is not in the allowlist.]"
                print(f"Executing command: {command_parts}")
                result = subprocess.run(
                    command_parts,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30,
                )
                return result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
                return f"[ERROR: Command '{command_or_path}' failed: {e}]"
        elif prefix == "@":
            try:
                # Read file content
                file_path = Path(command_or_path)
                return file_path.read_text().strip()
            except FileNotFoundError:
                return f"[ERROR: File not found at '{command_or_path}']"
            except IOError as e:
                return f"[ERROR: Could not read file at '{command_or_path}': {e}]"

        return match.group(0)  # Should not happen with the given regex

    def _resolve_dynamic_content(self, raw_context: str) -> str:
        """
        Resolves dynamic content placeholders in a string.
        - `!command` is replaced by the stdout of the executed shell command.
        - `@path/to/file` is replaced by the content of the file.
        """
        # It captures the prefix (! or @) and the command/path.
        pattern = re.compile(r"([!@])\s*([^\n]+)")
        return pattern.sub(self._resolve_callback, raw_context)
