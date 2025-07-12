import pytest
from unittest.mock import MagicMock, patch
from src.prp_compiler.agents.planner import PlannerAgent
from src.prp_compiler.models import Action

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

def test_run_planning_loop(mock_primitive_loader):
    # Arrange
    planner = PlannerAgent(mock_primitive_loader)
    
    # Mock a sequence of two responses from the Gemini model
    retrieve_response = make_mock_gemini_response('retrieve_knowledge', {"query": "test"})
    finish_response = make_mock_gemini_response('finish', {"schema_choice": "final_schema", "pattern_references": ["p1"]})
    planner.model.generate_content.side_effect = [retrieve_response, finish_response]
    
    # Act
    planner_gen = planner.run_planning_loop("test goal", constitution="")
    
    # Step 1: Yield first action
    first_action = next(planner_gen)
    assert isinstance(first_action, Action)
    assert first_action.tool_name == "retrieve_knowledge"
    
    # Step 2: Send observation and yield second action
    try:
        final_args = planner_gen.send("Observation from retrieve")
        # This should not be reached, the generator should raise StopIteration with a return value
        pytest.fail("Generator should have stopped.")
    except StopIteration as e:
        final_args = e.value # The return value of a generator is in StopIteration exception

    # Assert
    assert final_args == {"schema_choice": "final_schema", "pattern_references": ["p1"]}
    assert planner.model.generate_content.call_count == 2
    # Check that the history was passed to the second call
    second_call_prompt = planner.model.generate_content.call_args_list[1][0][0]
    assert "Observation from retrieve" in second_call_prompt
