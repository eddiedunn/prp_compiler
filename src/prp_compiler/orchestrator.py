import importlib
import subprocess
from pathlib import Path
from typing import Tuple

import typer

from .agents.planner import Action, PlannerAgent
from .knowledge import VectorStore
from .cache import ResultCache
from .primitives import PrimitiveLoader
from .context import ContextManager


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
        self,
        primitive_loader: PrimitiveLoader,
        knowledge_store: VectorStore,
        result_cache: "ResultCache | None" = None,
    ):
        self.primitive_loader = primitive_loader
        self.knowledge_store = knowledge_store
        self.result_cache = result_cache
        self.planner = PlannerAgent(self.primitive_loader)

    def execute_action(self, action: Action) -> str:
        """Dynamically loads and executes an action primitive from its file path.

        Results are cached based on the tool name and arguments to avoid
        repeating expensive operations across runs.
        """
        cache_key = self._compute_action_cache_key(action)
        if self.result_cache:
            cached = self.result_cache.get(cache_key)
            if isinstance(cached, dict) and "result" in cached:
                return cached["result"]
        try:
            # Built-in retrieval bypasses the primitive loader and directly
            # queries the KnowledgeStore.
            if action.tool_name == "retrieve_knowledge":
                query = action.arguments.get("query", "")
                chunks = self.knowledge_store.retrieve(query)
                result = "\n".join(chunks)
                if self.result_cache:
                    self.result_cache.set(cache_key, {"result": result})
                return result

            actions = self.primitive_loader.primitives.get("actions", {})
            action_manifest = actions.get(action.tool_name)
            if not action_manifest:
                raise ValueError(f"Action '{action.tool_name}' not found in manifest.")

            allowed_cmds = action_manifest.get("allowed_shell_commands")
            if allowed_cmds is not None:
                cmd = action.arguments.get("command")
                if cmd and cmd.split()[0] not in allowed_cmds:
                    raise PermissionError(
                        f"Command '{cmd}' not allowed for action '{action.tool_name}'"
                    )

            # Install action-specific dependencies if specified
            req_path = Path(action_manifest["base_path"]) / "requirements.txt"
            if req_path.is_file():
                subprocess.run([
                    "uv",
                    "pip",
                    "install",
                    "-r",
                    str(req_path),
                ], check=False)

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

            result_str = str(result)
            if self.result_cache:
                self.result_cache.set(cache_key, {"result": result_str})

            return result_str
        except Exception as e:
            return f"[ERROR] Failed to execute action '{action.tool_name}': {e}"

    def run(
        self,
        user_goal: str,
        constitution: str,
        max_steps: int = 10,
        strategy_name: str | None = None,
    ) -> Tuple[str, str]:
        """Drives the main ReAct loop and assembles the final context."""
        cache_key = self._compute_cache_key(user_goal)
        if self.result_cache:
            cached = self.result_cache.get(cache_key)
            if (
                isinstance(cached, dict)
                and "schema_choice" in cached
                and "final_context" in cached
            ):
                return cached["schema_choice"], cached["final_context"]

        # STEP 1: Select Strategy
        if strategy_name:
            chosen_strategy_name = strategy_name
        else:
            chosen_strategy_name = self.planner.select_strategy(user_goal, constitution)

        typer.secho(f"Selected strategy: {chosen_strategy_name}", fg=typer.colors.BLUE)

        strategy_content = self.primitive_loader.get_primitive_content(
            "strategies", chosen_strategy_name
        )

        context = ContextManager(model=None)  # Pass None to disable summarization in tests
        context.add_entry("Observation", "Planner initialized.")
        final_plan_args = None

        for i in range(max_steps):
            try:
                step = self.planner.plan_step(
                    user_goal,
                    constitution,
                    strategy_content,
                    context.get_history_str().split("\n") if context.history else [],
                )

                thought_text = (
                    f"Thought: {step.thought.reasoning}\n"
                    f"Critique: {step.thought.criticism}"
                )
                context.add_entry("Thought", thought_text)
                typer.secho(f"\U0001F914 {thought_text}", fg=typer.colors.CYAN)

                action = step.thought.next_action
                action_text = f"Action: {action.tool_name}({action.arguments})"
                context.add_entry("Action", action_text)
                typer.secho(f"\u25B6\uFE0F {action_text}", fg=typer.colors.MAGENTA)

                if action.tool_name == "finish":
                    final_plan_args = action.arguments
                    break

                observation = self.execute_action(action)
                observation_text = f"Observation: {observation}"
                context.add_entry("Observation", observation_text)
                typer.secho(f"\U0001F440 {observation_text}", fg=typer.colors.GREEN)

                # History is managed by the ContextManager

            except Exception as e:
                return (
                    "",
                    f"[ERROR] Exception in Orchestrator.run: {e}\n\n"
                    + context.get_history_str(),
                )
        else:  # This 'else' belongs to the 'for' loop
            return (
                "",
                "[ERROR] Planner did not finish within max_steps.\n\n"
                + context.get_history_str(),
            )

        # After the loop, assemble the final context
        if not final_plan_args:
            return (
                "",
                "[ERROR] Planner did not finish with a final plan.\n\n"
                + context.get_history_str(),
            )

        schema_choice = final_plan_args.get("schema_choice", "")
        schema_content = self.primitive_loader.get_primitive_content(
            "schemas", schema_choice
        )
        context.add_entry("Schema", f"{schema_choice}\n{schema_content}")

        for pattern_ref in final_plan_args.get("pattern_references", []):
            pattern_content = self.primitive_loader.get_primitive_content(
                "patterns", pattern_ref
            )
            context.add_entry("Pattern", f"{pattern_ref}\n{pattern_content}")
        final_context = context.get_history_str()
        if self.result_cache:
            self.result_cache.set(
                cache_key,
                {"schema_choice": schema_choice, "final_context": final_context},
            )
        return (schema_choice, final_context)

    def _compute_cache_key(self, user_goal: str) -> str:
        """Generate a cache key from the goal and loaded primitives."""
        import hashlib

        parts = [user_goal]
        for p_type, prims in self.primitive_loader.primitives.items():
            for name, manifest in prims.items():
                version = manifest.get("version", "")
                parts.append(f"{p_type}:{name}:{version}")
        joined = "|".join(sorted(parts))
        return hashlib.sha256(joined.encode()).hexdigest()

    def _compute_action_cache_key(self, action: Action) -> str:
        """Generate a cache key for an individual action call."""
        import hashlib
        import json

        data = {
            "tool": action.tool_name,
            "args": action.arguments,
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
