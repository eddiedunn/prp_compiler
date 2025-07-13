from unittest.mock import MagicMock

from src.prp_compiler.context import ContextManager
from src.prp_compiler.models import Action, ReActStep, Thought


def test_context_manager_summarizes_when_limit_reached():
    mock_model = MagicMock()
    mock_model.generate_content.return_value.text = "summary"

    cm = ContextManager(model=mock_model, token_limit=20)
    step = ReActStep(
        thought=Thought(
            reasoning="r",
            criticism="",
            next_action=Action(tool_name="a", arguments={}),
        ),
        observation="hello world",
    )
    for _ in range(10):
        cm.add_step(step)

    assert any("Summary of previous steps" in s.observation for s in cm.history)
    mock_model.generate_content.assert_called()
