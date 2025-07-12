import re
import shlex
import subprocess
from pathlib import Path
from typing import Tuple
from .config import ALLOWED_SHELL_COMMANDS
from .models import ExecutionPlan
from .agents.planner import PlannerAgent, Action

def load_constitution(root_path: Path) -> str:
    """Loads the constitution from CLAUDE.md at the project root."""
    constitution_path = root_path / "CLAUDE.md"
    if constitution_path.is_file():
        return constitution_path.read_text()
    return ""



class Orchestrator:
    """
    Orchestrates the execution of tasks, including resolving dynamic content and driving the ReAct loop.
    Supports both legacy (manifest-based) and new (primitive_loader/knowledge_store) initialization for backward compatibility.
    """

    def __init__(self, *args, **kwargs):
        # Legacy: (tools_manifest, knowledge_manifest, schemas_manifest)
        # New: (primitive_loader, knowledge_store)
        if len(args) == 3 and all(isinstance(arg, list) for arg in args):
            # Legacy manifest-based init
            tools_manifest, knowledge_manifest, schemas_manifest = args
            self.tools_manifest = {item.name: item for item in tools_manifest}
            self.knowledge_manifest = {item.name: item for item in knowledge_manifest}
            self.schemas_manifest = {item.name: item for item in schemas_manifest}
            self.legacy_mode = True
        elif len(args) == 2:
            # New ReAct init
            self.primitive_loader = args[0]
            self.knowledge_store = args[1]
            self.planner = PlannerAgent(self.primitive_loader)
            self.legacy_mode = False
        else:
            raise TypeError("Orchestrator must be initialized with either (tools_manifest, knowledge_manifest, schemas_manifest) or (primitive_loader, knowledge_store)")

    def execute_action(self, action: Action) -> str:
        """Executes a single action from the planner and returns the observation."""
        if action.tool_name == "retrieve_knowledge":
            query = action.arguments.get("query", "")
            results = self.knowledge_store.retrieve(query)
            return f"Retrieved {len(results)} knowledge chunks for query: '{query}'\nContent:\n" + "\n".join(results)
        # Here you would add logic for other tools like web_search
        # For now, we return a placeholder for any other tool
        else:
            return f"Observation: Executed tool '{action.tool_name}' with args {action.arguments}. [Mocked Result]"

    def run(self, user_goal: str) -> Tuple[str, str]:
        """Drives the main ReAct loop and assembles the final context using the new Planner generator interface."""
        max_steps = 10
        planner_gen = self.planner.run_planning_loop(user_goal, max_steps=max_steps)
        final_context_parts = []
        final_plan = None
        try:
            step = next(planner_gen)
            while True:
                action = step.thought.next_action
                if action.tool_name == "finish":
                    final_plan = action.arguments
                    break
                observation = self.execute_action(action)
                final_context_parts.append(f"Thought: {step.thought.reasoning}\nAction: {action.tool_name}\nObservation: {observation}")
                step = planner_gen.send(observation)
        except StopIteration:
            pass
        if final_plan:
            schema_template = self.primitive_loader.primitives['schemas'][final_plan['schema_choice']]['content']
            for pattern_name in final_plan.get('pattern_references', []):
                final_context_parts.append(self.primitive_loader.primitives['patterns'][pattern_name]['content'])
            return schema_template, "\n---\n".join(final_context_parts)
        raise RuntimeError("Planner failed to finish within max steps.")

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
            except Exception as e:
                return f"[ERROR: Command '{command_or_path}' failed: {e}]"

    def _resolve_dynamic_content(self, raw_context: str) -> str:
        """
        Resolves dynamic content placeholders in a string.
        - `!command` is replaced by the stdout of the executed shell command.
        - `@path/to/file` is replaced by the content of the file.
        """
        # It captures the prefix (! or @) and the command/path.
        pattern = re.compile(r"([!@])\s*([^\n]+)")
        return pattern.sub(self._resolve_callback, raw_context)
