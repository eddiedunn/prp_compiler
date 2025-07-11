import re
import subprocess
from pathlib import Path

from typing import List, Dict, Tuple
from .models import ManifestItem, ExecutionPlan

class Orchestrator:
    """
    Orchestrates the execution of tasks, including resolving dynamic content.
    """
    def __init__(self, 
                 tools_manifest: List[ManifestItem], 
                 knowledge_manifest: List[ManifestItem], 
                 schemas_manifest: List[ManifestItem]):
        """Initializes the Orchestrator with manifests for lookup."""
        self.tools_manifest = {item.name: item for item in tools_manifest}
        self.knowledge_manifest = {item.name: item for item in knowledge_manifest}
        self.schemas_manifest = {item.name: item for item in schemas_manifest}

    def assemble_context(self, plan: ExecutionPlan) -> Tuple[str, str]:
        """
        Assembles the context from the execution plan.
        Returns the schema template and the assembled context string.
        """
        # 1. Get the schema template from the chosen schema
        schema_item = self.schemas_manifest.get(plan.schema_choice)
        if not schema_item:
            raise ValueError(f"Schema '{plan.schema_choice}' not found in manifest.")
        schema_template = Path(schema_item.file_path).read_text()

        # 2. Assemble context from the knowledge plan
        assembled_knowledge = []
        for knowledge_name in plan.knowledge_plan:
            knowledge_item = self.knowledge_manifest.get(knowledge_name)
            if knowledge_item:
                raw_content = Path(knowledge_item.file_path).read_text()
                # Resolve any dynamic content within the knowledge file
                resolved_content = self._resolve_dynamic_content(raw_content)
                assembled_knowledge.append(f"--- KNOWLEDGE: {knowledge_name} ---\n{resolved_content}")
            else:
                assembled_knowledge.append(f"[WARNING: Knowledge '{knowledge_name}' not found in manifest.]")
        
        # 3. For now, we will just use the tool descriptions in the context.
        # A more advanced implementation would execute the tools and use their output.
        tool_descriptions = []
        for tool_plan_item in plan.tool_plan:
            tool_item = self.tools_manifest.get(tool_plan_item.command_name)
            if tool_item:
                tool_descriptions.append(f"--- TOOL: {tool_item.name} ---\nDescription: {tool_item.description}")
            else:
                tool_descriptions.append(f"[WARNING: Tool '{tool_plan_item.command_name}' not found in manifest.]")

        # Combine all parts into a single context string
        final_context = "\n\n".join(assembled_knowledge + tool_descriptions)
        
        return schema_template, final_context

    def _resolve_callback(self, match: re.Match) -> str:
        """
        Callback function for re.sub to handle dynamic content resolution.
        """
        prefix = match.group(1)
        command_or_path = match.group(2).strip()

        if prefix == '!':
            try:
                # Execute shell command
                # Using shell=True can be a security risk. In a real-world scenario,
                # we would want to sanitize inputs or avoid shell=True.
                result = subprocess.run(
                    command_or_path,
                    shell=True,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                # In case of error, return a descriptive string
                return f"[ERROR: Command '{command_or_path}' failed: {e}]"
        elif prefix == '@':
            try:
                # Read file content
                file_path = Path(command_or_path)
                return file_path.read_text().strip()
            except FileNotFoundError:
                return f"[ERROR: File not found at '{command_or_path}']"
            except IOError as e:
                return f"[ERROR: Could not read file at '{command_or_path}': {e}]"
        
        return match.group(0) # Should not happen with the given regex

    def _resolve_dynamic_content(self, raw_context: str) -> str:
        """
        Resolves dynamic content placeholders in a string.
        - `!command` is replaced by the stdout of the executed shell command.
        - `@path/to/file` is replaced by the content of the file.
        """
        # This regex finds patterns like `!command` or `@file/path`
        # It captures the prefix ('!' or '@') and the rest of the line.
        pattern = re.compile(r'([!@])(.+)')
        return pattern.sub(self._resolve_callback, raw_context)
