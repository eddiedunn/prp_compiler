from __future__ import annotations

from typing import List

from .utils import count_tokens


class ContextManager:
    """Manages the ReAct history with automatic summarization."""

    def __init__(self, model, token_limit: int = 8000) -> None:
        self.model = model
        self.token_limit = token_limit
        self.history: List[str] = []

    def add(self, entry: str) -> None:
        """Add a new history entry and summarize if needed."""
        self.history.append(entry)
        self._maybe_summarize()

    def _maybe_summarize(self) -> None:
        current_tokens = count_tokens("\n".join(self.history))
        if current_tokens <= int(self.token_limit * 0.8):
            return
        if len(self.history) <= 3:
            return
        old_entries = self.history[:-3]
        recent_entries = self.history[-3:]
        prompt = (
            "Summarize these previous steps so the context fits in fewer tokens:\n"
            + "\n".join(old_entries)
        )
        try:
            response = self.model.generate_content(prompt)
            summary = response.text.strip()
        except Exception:
            summary = "(failed to summarize history)"
        self.history = [f"Summary: {summary}"] + recent_entries

    def as_list(self) -> List[str]:
        return list(self.history)
