from unittest.mock import MagicMock, patch, mock_open

import pytest

from src.prp_compiler.models import Action, ReActStep, Thought
from src.prp_compiler.orchestrator import Orchestrator





@pytest.fixture
def mock_knowledge_store():
    """A pytest fixture to create a mocked KnowledgeStore.""" 
    return MagicMock()


@patch("importlib.import_module")
def test_execute_action_dynamically_imports_and_runs_function(mock_import_module, mock_knowledge_store):
    """ 
    Tests that execute_action correctly imports and runs an action's Python function.
    """
    # Arrange
    mock_loader = MagicMock()
    mock_action_module = MagicMock()
    mock_action_function = MagicMock(return_value={"status": "success", "files": ["a.txt"]})
    mock_action_module.run = mock_action_function
    mock_import_module.return_value = mock_action_module

    # Configure the loader to return the entrypoint and the manifest
    action_name = "test_action"
    mock_loader.get_action_entrypoint.return_value = ("test_action.py", "run")
    mock_loader.primitives = {
        "actions": {
            action_name: {
                "version": "1.0.0",
                "entrypoint": "test_action.py:run"
            }
        }
    }

    orchestrator = Orchestrator(mock_loader, mock_knowledge_store)
    action = Action(tool_name=action_name, arguments={"path": "/tmp"})

    # Act
    result = orchestrator.execute_action(action)

    # Assert
    # 1. Verify the loader was called to get the entrypoint
    mock_loader.get_action_entrypoint.assert_called_once_with(action_name)

    # 2. Verify that the correct module was dynamically imported
    expected_import_path = "prp_compiler.primitives.actions.test_action.v1_0_0.test_action"
    mock_import_module.assert_called_once_with(expected_import_path)

    # 3. Verify the action function was called with the correct arguments
    mock_action_function.assert_called_once_with(path="/tmp")

    # 4. Verify the result is the string representation of the function's return value
    assert result == str({"status": "success", "files": ["a.txt"]})



@patch("src.prp_compiler.orchestrator.PlannerAgent")
def test_run_captures_finish_args_and_assembles_context(
    MockPlannerAgent, mock_knowledge_store
):
    """
    Tests that the main run loop correctly captures the 'finish' action's arguments
    and uses them to assemble and return the final context and schema choice.
    """
    # Arrange
    mock_planner_instance = MockPlannerAgent.return_value

    # This generator yields one action step, then the final 'finish' step
    def mock_planning_loop(*args, **kwargs):
        # First step: a simple action
        yield ReActStep(
            thought=Thought(
                reasoning="I need to see what files are in the directory.",
                criticism="This is a good first step.",
                next_action=Action(tool_name="list_directory", arguments={"directory_path": "."})
            )
        )
        # Final step: the finish action with the plan details
        yield ReActStep(
            thought=Thought(
                reasoning="I have enough information to finish.",
                criticism="The plan is complete.",
                next_action=Action(
                    tool_name="finish",
                    arguments={
                        "schema_choice": "test_schema",
                        "pattern_references": ["test_pattern"]
                    }
                )
            )
        )

    mock_planner_instance.run_planning_loop.side_effect = mock_planning_loop

    # The loader is still needed for schemas and patterns
    mock_loader = MagicMock()
    mock_loader.get_primitive_content.side_effect = [
        '{"title": "Test Schema"}',  # First call for the schema
        'This is a test pattern.'   # Second call for the pattern
    ]

    orchestrator = Orchestrator(mock_loader, mock_knowledge_store)
    orchestrator.execute_action = MagicMock(return_value="Observation: file1.txt")

    # Act
    schema_choice, final_context = orchestrator.run("test goal", "test constitution")

    # Assert
    # 1. Check that the correct schema choice is returned
    assert schema_choice == "test_schema"

    # 2. Check that the final context contains all the parts of the loop
    assert "Thought: I need to see what files are in the directory." in final_context
    assert "Action: list_directory({'directory_path': '.'})" in final_context
    assert "Observation: file1.txt" in final_context
    assert "Action: finish({" in final_context # Check that finish was called

    # 3. Check that the schema and pattern content were appended correctly
    assert "Schema: test_schema\n{\"title\": \"Test Schema\"}" in final_context
    assert "Pattern: test_pattern\nThis is a test pattern." in final_context
