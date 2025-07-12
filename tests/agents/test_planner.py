import pytest
from unittest.mock import MagicMock, patch
from src.prp_compiler.agents.planner import PlannerAgent
from src.prp_compiler.models import ReActStep

@pytest.fixture
def mock_primitive_loader():
    loader = MagicMock()
    loader.get_all.return_value = [{
        "name": "retrieve_knowledge", "description": "desc", "inputs_schema": {"type": "object", "properties": {"query": {"type": "string"}}}
    }]
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
def test_run_planning_loop(mock_generative_model, mock_primitive_loader):
    # Arrange
    mock_instance = mock_generative_model.return_value
    planner = PlannerAgent(mock_primitive_loader)

    # Mock a sequence of two responses from the Gemini model
    retrieve_response = make_mock_gemini_response('retrieve_knowledge', {"query": "test"})
    finish_response = make_mock_gemini_response('finish', {"schema_choice": "final_schema", "pattern_references": ["p1"]})
    mock_instance.generate_content.side_effect = [retrieve_response, finish_response]

    # Act
    planner_gen = planner.run_planning_loop("test goal", constitution="")

    # Step 1: Prime the generator and send the first observation to get the first action
    next(planner_gen)  # Prime the generator
    first_step = planner_gen.send("No observation yet. Start by thinking about the user's goal.")
    assert isinstance(first_step, ReActStep)
    assert first_step.thought.next_action.tool_name == "retrieve_knowledge"

    # Step 2: Send observation and catch the end of the loop
    # This should yield the finish step
    try:
        finish_step = planner_gen.send("Observation from retrieve")
        assert finish_step.thought.next_action.tool_name == "finish"
    except StopIteration:
        pytest.fail("Generator stopped prematurely. It should yield the 'finish' step.")

    # Step 3: Sending again should raise StopIteration with the final arguments
    try:
        planner_gen.send("Another observation.")
        pytest.fail("Generator did not stop after yielding finish action")
    except StopIteration as e:
        final_args = e.value

    # Assert
    assert final_args == {"schema_choice": "final_schema", "pattern_references": ["p1"]}
    assert mock_instance.generate_content.call_count == 2
    # Check that the history was passed to the second call
    second_call_prompt = mock_instance.generate_content.call_args_list[1][0][0]
    assert "Observation from retrieve" in second_call_prompt
