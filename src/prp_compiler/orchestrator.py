import re
import shlex
import subprocess
from pathlib import Path
from typing import Tuple
from .config import ALLOWED_SHELL_COMMANDS

from .agents.planner import PlannerAgent, Action
from .primitives import PrimitiveLoader
from .knowledge import KnowledgeStore

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
    def __init__(self, primitive_loader: PrimitiveLoader, knowledge_store: KnowledgeStore):
        self.primitive_loader = primitive_loader
        self.knowledge_store = knowledge_store
        self.planner = PlannerAgent(self.primitive_loader)

        # The new dynamic dispatch map for actions.
        self.action_handlers: Dict[str, Callable[..., str]] = {
            "retrieve_knowledge": self.knowledge_store.retrieve,
            # In the future, other actions like 'web_search' would be registered here.
        }

    def execute_action(self, action: Action) -> str:
        """Executes a single action using the handler map."""
        handler = self.action_handlers.get(action.tool_name)
        if not handler:
            return f"[ERROR] Action '{action.tool_name}' not found in handler map."
        
        # The 'query' key is a simplification for now. A more robust solution
        # would inspect the handler's signature, but this is sufficient.
        query = action.arguments.get("query", "")
        if not query:
             return f"[ERROR] Missing 'query' argument for action '{action.tool_name}'."
        
        # Assuming all current handlers take a single 'query' argument.
        results = handler(query)
        return f"Retrieved {len(results)} chunks for query: '{query}'\nContent:\n" + "\n".join(results)

    def run(self, user_goal: str, max_steps: int = 10) -> Tuple[str, str]:
        """Drives the main ReAct loop and assembles the final context."""
        planner_gen = self.planner.run_planning_loop(user_goal, max_steps=max_steps)
        final_context_parts = []
        final_plan_args = None
        
        observation = "No observation yet. Start by thinking about the user's goal."
        
        for _ in range(max_steps):
            try:
                step = planner_gen.send(observation)
                action = step.thought.next_action
                
                final_context_parts.append(f"Thought: {step.thought.reasoning}\nAction: {action.tool_name}({action.arguments})")

                if action.tool_name == "finish":
                    final_plan_args = action.arguments
                    break

                observation = self.execute_action(action)
                final_context_parts.append(f"Observation: {observation}")

            except StopIteration:
                break
        
        if not final_plan_args:
            raise RuntimeError("Planner failed to call 'finish' within max steps.")

        # Assemble final context from patterns and the loop history
        schema_content = self.primitive_loader.get_primitive_content('schemas', final_plan_args['schema_choice'])
        
        for pattern_name in final_plan_args.get('pattern_references', []):
            pattern_content = self.primitive_loader.get_primitive_content('patterns', pattern_name)
            final_context_parts.append(f"\n--- Relevant Pattern: {pattern_name} ---\n{pattern_content}")

        return schema_content, "\n\n".join(final_context_parts)



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
