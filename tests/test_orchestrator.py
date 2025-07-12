from unittest.mock import MagicMock, patch, mock_open

import pytest

from src.prp_compiler.models import Action, ReActStep, Thought
from src.prp_compiler.orchestrator import Orchestrator


@pytest.fixture
def mock_loader():
    """A pytest fixture to create a mocked PrimitiveLoader."""
    loader = MagicMock()

    def get_content_side_effect(primitive_type, name):
        if primitive_type == "actions" and name == "list_directory":
            return "!ls -l $ARGUMENTS(directory_path)"
        if primitive_type == "schemas" and name == "test_schema":
            return '{"title": "Test Schema"}'
        if primitive_type == "patterns" and name == "test_pattern":
            return "This is a test pattern."
        return f"content for {primitive_type}/{name}"

    loader.get_primitive_content.side_effect = get_content_side_effect
    return loader


@pytest.fixture
def mock_knowledge_store():
    """A pytest fixture to create a mocked KnowledgeStore."""
    ks = MagicMock()
    ks.retrieve.return_value = ["Retrieved knowledge chunk."]
    return ks


def test_execute_action_substitutes_arguments(mock_loader, mock_knowledge_store):
    """
    Tests that execute_action correctly substitutes arguments using regex.
    """
    orchestrator = Orchestrator(mock_loader, mock_knowledge_store)
    action = Action(tool_name="list_directory", arguments={"directory_path": "/tmp"})

    # Mock the dynamic content resolution to isolate the argument substitution
    orchestrator._resolve_dynamic_content = MagicMock(side_effect=lambda x: x)

    result = orchestrator.execute_action(action)

    mock_loader.get_primitive_content.assert_called_once_with("actions", "list_directory")
    # Assert that the arguments were substituted correctly before dynamic resolution
    orchestrator._resolve_dynamic_content.assert_called_once_with("!ls -l /tmp")
    assert result == "!ls -l /tmp"


@patch("subprocess.run")
def test_execute_action_with_dynamic_content(
    mock_subprocess_run, mock_loader, mock_knowledge_store
):
    """
    Tests that execute_action correctly substitutes arguments AND resolves dynamic content.
    """
    # Arrange
    mock_subprocess_run.return_value.stdout = "file1.txt\nfile2.txt"
    mock_subprocess_run.return_value.check.return_value = None # No exception

    orchestrator = Orchestrator(mock_loader, mock_knowledge_store)
    action = Action(tool_name="list_directory", arguments={"directory_path": "/app"})

    # Act
    result = orchestrator.execute_action(action)

    # Assert
    mock_loader.get_primitive_content.assert_called_once_with("actions", "list_directory")
    mock_subprocess_run.assert_called_once_with(
        ["ls", "-l", "/app"], capture_output=True, text=True, check=True, timeout=30
    )
    assert result == "file1.txt\nfile2.txt"



@patch("src.prp_compiler.orchestrator.PlannerAgent")
def test_run_captures_finish_args_and_assembles_context(
    MockPlannerAgent, mock_loader, mock_knowledge_store
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

    orchestrator = Orchestrator(mock_loader, mock_knowledge_store)

    # Mock execute_action to return a simple observation
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
