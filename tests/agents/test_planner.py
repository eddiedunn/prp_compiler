from unittest.mock import MagicMock, patch

import pytest

from src.prp_compiler.agents.planner import PlannerAgent
from src.prp_compiler.models import ReActStep


def make_mock_gemini_response(tool_name, args):
    fc = MagicMock()
    fc.name = tool_name
    fc.args = args
    part = MagicMock(function_call=fc)
    candidate = MagicMock(content=MagicMock(parts=[part]))
    return MagicMock(candidates=[candidate])


@pytest.fixture
def mock_primitive_loader():
    loader = MagicMock()
    loader.get_all.side_effect = [
        [],  # strategies for selection
        [],  # actions for plan_step
    ]
    return loader


@patch("src.prp_compiler.agents.base_agent.genai.GenerativeModel")
def test_select_strategy(mock_generative_model, mock_primitive_loader):
    mock_model = mock_generative_model.return_value
    mock_response = make_mock_gemini_response("select_strategy", {"strategy_name": "simple"})
    mock_model.generate_content.return_value = mock_response

    planner = PlannerAgent(mock_primitive_loader)
    chosen = planner.select_strategy("add feature", "")

    assert chosen == "simple"
    mock_model.generate_content.assert_called_once()


@patch("src.prp_compiler.agents.base_agent.genai.GenerativeModel")
def test_plan_step_uses_strategy(mock_generative_model, mock_primitive_loader):
    mock_model = mock_generative_model.return_value
    mock_response = make_mock_gemini_response(
        "retrieve_knowledge",
        {"reasoning": "why", "criticism": "crit", "query": "foo"},
    )
    mock_model.generate_content.return_value = mock_response

    planner = PlannerAgent(mock_primitive_loader)
    step = planner.plan_step(
        user_goal="goal",
        constitution="",
        strategy={"template": "My Strategy"},
        history=["Observation: start"],
    )

    assert isinstance(step, ReActStep)
    called_prompt = mock_model.generate_content.call_args[0][0]
    assert "My Strategy" in called_prompt
