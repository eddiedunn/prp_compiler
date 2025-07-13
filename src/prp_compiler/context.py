from __future__ import annotations

from typing import Any, Dict, List

import tiktoken


class ContextManager:
    """Manages ReAct history with automatic summarization to avoid token overflow."""

    def __init__(self, model: Any, token_limit: int = 80000) -> None:
        self.model = model
        self.token_limit = token_limit
        self.history: List[Dict[str, str]] = []
        self._tokenizer = tiktoken.get_encoding("cl100k_base")

    def add_entry(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        self._summarize_if_needed()

    def get_history_str(self, subset: List[Dict[str, str]] | None = None) -> str:
        entries = subset if subset is not None else self.history
        return "\n".join([f"{e['role']}: {e['content']}" for e in entries])

    def _current_token_count(self) -> int:
        return len(self._tokenizer.encode(self.get_history_str()))

    def _summarize_if_needed(self) -> None:
        if self._current_token_count() > self.token_limit:
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
            self.history = [
                {"role": "Observation", "content": f"Summary of previous steps: {summary}"}
            ] + keep_these
            print(f"[INFO] History summarized. New token count: {self._current_token_count()}")
