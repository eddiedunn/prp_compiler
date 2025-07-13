from __future__ import annotations

from typing import Any, Dict, List

from .models import Action, ReActStep, Thought

import tiktoken


class ContextManager:
    """Manages ReAct history with automatic summarization to avoid token overflow."""

    def __init__(self, model: Any, token_limit: int = 80000) -> None:
        self.model = model
        self.token_limit = token_limit
        self.history: List[ReActStep] = []
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def add_step(self, step: ReActStep) -> None:
        """Adds a complete thought-action-observation step to the history."""
        self.history.append(step)
        self._summarize_if_needed()

    def get_history_str(self, subset: List[ReActStep] | None = None) -> str:
        """Returns a string representation of the history for prompting."""
        entries = subset if subset is not None else self.history
        lines = []
        for step in entries:
            lines.append(f"Thought: {step.thought.reasoning}")
            lines.append(
                f"Action: {step.thought.next_action.tool_name}({step.thought.next_action.arguments})"
            )
            if step.observation is not None:
                lines.append(f"Observation: {step.observation}")
        return "\n".join(lines)

    def get_structured_history(self) -> List[Dict[str, Any]]:
        """Returns the history as serializable dictionaries."""
        return [step.model_dump() for step in self.history]

    def _current_token_count(self) -> int:
        return len(self._tokenizer.encode(self.get_history_str()))

    def _summarize_if_needed(self) -> None:
        if self.model and self._current_token_count() > self.token_limit:
            print("[INFO] Context limit reached, summarizing history...")
            keep_last_n = 5
            to_summarize = self.history[:-keep_last_n]
            keep_these = self.history[-keep_last_n:]
            summary_prompt = (
                "Summarize the following conversation history into a concise paragraph:\n\n"
                + self.get_history_str(to_summarize)
            )
            response = self.model.generate_content(summary_prompt)
            summary = response.text
            summary_step = ReActStep(
                thought=Thought(
                    reasoning="summary",
                    criticism="",
                    next_action=Action(tool_name="summary", arguments={}),
                ),
                observation=f"Summary of previous steps: {summary}",
            )
            self.history = [summary_step] + keep_these
            print(
                f"[INFO] History summarized. New token count: {self._current_token_count()}"
            )
