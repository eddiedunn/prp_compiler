from unittest.mock import MagicMock, patch

import pytest

from src.prp_compiler.agents.planner import PlannerAgent
from src.prp_compiler.models import ReActStep


@pytest.fixture
def mock_primitive_loader():
    loader = MagicMock()
    # No actions returned; retrieve_knowledge is built-in to the planner.
    loader.get_all.return_value = []
    return loader

def make_mock_gemini_response(tool_name, args):
    """Helper to create a mock Gemini response object."""
    fc = MagicMock()
    fc.name = tool_name
    fc.args = args
    part = MagicMock(function_call=fc)
    candidate = MagicMock(content=MagicMock(parts=[part]))
    return MagicMock(candidates=[candidate])

@patch("src.prp_compiler.agents.base_agent.genai.GenerativeModel")
def test_plan_step_returns_react_step(
    mock_generative_model, mock_primitive_loader
):
    """Tests that a single call to plan_step returns a correctly formed ReActStep."""
    # Arrange
    mock_model_instance = mock_generative_model.return_value
    planner = PlannerAgent(mock_primitive_loader)

    # Mock a single response from the Gemini model, including reasoning and criticism
    mock_response_args = {
        "reasoning": "I need to find information.",
        "criticism": "This might be too broad.",
        "query": "test query",
    }
    mock_response = make_mock_gemini_response("retrieve_knowledge", mock_response_args)
    mock_model_instance.generate_content.return_value = mock_response

    # Act
    history = ["Observation: It all starts here."]
    step = planner.plan_step("test goal", constitution="", history=history)

    # Assert
    assert isinstance(step, ReActStep)

    # Check thought
    assert step.thought.reasoning == "I need to find information."
    assert step.thought.criticism == "This might be too broad."

    # Check action
    assert step.thought.next_action.tool_name == "retrieve_knowledge"
    assert step.thought.next_action.arguments == {"query": "test query"}

    # Check that generate_content was called correctly
    mock_model_instance.generate_content.assert_called_once()
    call_args, call_kwargs = mock_model_instance.generate_content.call_args
    prompt = call_args[0]
    assert "test goal" in prompt
    assert "Observation: It all starts here." in prompt


@patch("src.prp_compiler.agents.base_agent.genai.GenerativeModel")
def test_tools_schema_includes_retrieve_knowledge(mock_generative_model, mock_primitive_loader):
    """Planner should always include the retrieve_knowledge tool."""
    planner = PlannerAgent(mock_primitive_loader)

    tool_names = [tool["name"] for tool in planner.tools_schema]
    assert "retrieve_knowledge" in tool_names

    # Ensure the query parameter is present
    tool = next(t for t in planner.tools_schema if t["name"] == "retrieve_knowledge")
    assert "query" in tool["parameters"]["properties"]

