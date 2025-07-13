from unittest.mock import MagicMock

from src.prp_compiler.context import ContextManager


def test_context_manager_summarizes_when_limit_reached():
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = "summary"

    cm = ContextManager(model=mock_model, token_limit=20)
    # Add entries until limit exceeded
    for i in range(10):
        cm.add_entry("Observation", "hello world")

    # Should summarize and keep recent entries
    assert any("Summary of previous steps" in e["content"] for e in cm.history)
    mock_model.generate_content.assert_called()
