from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import subprocess
import pytest

from src.prp_compiler.models import Action, ReActStep, Thought
from src.prp_compiler.orchestrator import Orchestrator


@pytest.fixture
def mock_knowledge_store():
    """A pytest fixture to create a mocked KnowledgeStore."""
    return MagicMock()


@patch("src.prp_compiler.orchestrator.PlannerAgent")
def test_execute_action_retrieve_knowledge(MockPlannerAgent, mock_knowledge_store):
    """execute_action should return joined chunks from the knowledge store."""
    orchestrator = Orchestrator(MagicMock(primitives={}), mock_knowledge_store)
    mock_knowledge_store.retrieve.return_value = ["ChunkA", "ChunkB"]

    action = Action(tool_name="retrieve_knowledge", arguments={"query": "foo"})
    result = orchestrator.execute_action(action)

    mock_knowledge_store.retrieve.assert_called_once_with("foo")
    assert result == "ChunkA\nChunkB"


@patch("subprocess.run")
@patch("importlib.util.module_from_spec")
@patch("importlib.util.spec_from_file_location")
def test_execute_action_dynamically_imports_and_runs_function(
    mock_spec_from_file_location,
    mock_module_from_spec,
    mock_subprocess_run,
    mock_knowledge_store,
):
    """
    Tests that execute_action correctly loads and runs an action's Python
    function from a file path.
    """
    # Arrange
    mock_loader = MagicMock()
    action_name = "test_action"

    # Mock the action's Python module and function
    mock_action_function = MagicMock(return_value={"status": "success"})
    mock_action_module = MagicMock()
    mock_action_module.run = mock_action_function

    # Mock the importlib.util machinery
    mock_spec = MagicMock()
    # This is needed because the real spec.loader is not None
    mock_spec.loader.exec_module = MagicMock()
    mock_spec_from_file_location.return_value = mock_spec
    mock_module_from_spec.return_value = mock_action_module

    # Configure the loader to return the manifest, including the base path
    mock_loader.primitives = {
        "actions": {
            action_name: {
                "version": "1.0.0",
                "entrypoint": "test_action.py:run",
                "base_path": "/fake/primitives/actions/test_action/1.0.0"
            }
        }
    }

    orchestrator = Orchestrator(mock_loader, mock_knowledge_store)
    action = Action(tool_name=action_name, arguments={"path": "/tmp"})

    # Act
    result = orchestrator.execute_action(action)

    # Assert
    # 1. Verify that the spec was created from the correct file path
    expected_path = (
        Path("/fake/primitives/actions/test_action/1.0.0") / "test_action.py"
    )
    mock_spec_from_file_location.assert_called_once_with(action_name, expected_path)

    # 2. Verify the action function was called with the correct arguments
    mock_action_function.assert_called_once_with(path="/tmp")

    # 3. Verify the result is the string representation of the function's return value
    assert result == str({"status": "success"})
    # Under this test's setup, no requirements.txt exists at the fake path,
    # so subprocess.run should not be called.
    mock_subprocess_run.assert_not_called()


@patch("src.prp_compiler.orchestrator.PlannerAgent")
def test_run_captures_finish_args_and_assembles_context(
    MockPlannerAgent, mock_knowledge_store
):
    """
    Tests that the main run loop correctly captures the 'finish' action's
    arguments and uses them to assemble and return the final context and schema
    choice.
    """
    # Arrange
    mock_planner_instance = MockPlannerAgent.return_value
    mock_planner_instance.select_strategy.return_value = "simple"

    steps = [
        ReActStep(
            thought=Thought(
                reasoning="look", criticism="none",
                next_action=Action(tool_name="list_directory", arguments={"directory_path": "."})
            )
        ),
        ReActStep(
            thought=Thought(
                reasoning="done", criticism="none",
                next_action=Action(tool_name="finish", arguments={"schema_choice": "test_schema", "pattern_references": ["test_pattern"]})
            )
        )
    ]
    mock_planner_instance.plan_step.side_effect = steps

    # The loader is still needed for schemas and patterns
    mock_loader = MagicMock()
    strategy_content = "This is a simple strategy."
    mock_loader.get_primitive_content.side_effect = [
        strategy_content,             # First call for the strategy
        '{"title": "Test Schema"}',  # Second call for the schema
        'This is a test pattern.'     # Third call for the pattern

    ]
    strategy_manifest = {
        "name": "simple",
        "entrypoint": "template.md",
        "base_path": "/tmp",
    }
    mock_loader.primitives = {"strategies": {"simple": strategy_manifest}}

    orchestrator = Orchestrator(mock_loader, mock_knowledge_store, MagicMock())
    orchestrator.execute_action = MagicMock(return_value="file1.txt")

    # Act
    schema_choice, final_context = orchestrator.run(
        "test goal", "test constitution"
    )

    mock_planner_instance.select_strategy.assert_called_once_with(
        "test goal", "test constitution"
    )
    mock_planner_instance.plan_step.assert_any_call(
        "test goal",
        "test constitution",
        strategy_content,
        ANY,
    )

    # Assert
    # 1. Check that the correct schema choice is returned
    assert schema_choice == "test_schema"

    # 2. Check that the final context contains all the parts of the loop
    assert "Thought: look" in final_context
    assert "Action: list_directory({'directory_path': '.'})" in final_context
    assert "Observation: file1.txt" in final_context
    assert "Action: finish({" in final_context  # Check that finish was called

    # 3. Check that the schema and pattern content were appended correctly
    assert "Schema: test_schema\n{\"title\": \"Test Schema\"}" in final_context
    assert "Pattern: test_pattern\nThis is a test pattern." in final_context

@patch("subprocess.run")
def test_resolve_dynamic_content_allowed_command(mock_run, mock_knowledge_store):
    orchestrator = Orchestrator(MagicMock(primitives={}), mock_knowledge_store)
    mock_run.return_value = subprocess.CompletedProcess(args=["echo"], returncode=0, stdout="hello\n")
    result = orchestrator._resolve_dynamic_content("Value: !(echo hello)")
    assert result == "Value: hello"

@patch("subprocess.run")
def test_resolve_dynamic_content_command_failure(mock_run, mock_knowledge_store):
    orchestrator = Orchestrator(MagicMock(primitives={}), mock_knowledge_store)
    mock_run.side_effect = subprocess.CalledProcessError(1, ["ls"], "error")
    result = orchestrator._resolve_dynamic_content("Files: !(ls missing)")
    assert "[ERROR]" in result


def test_resolve_dynamic_content_disallowed_command(mock_knowledge_store):
    orchestrator = Orchestrator(MagicMock(primitives={}), mock_knowledge_store)
    result = orchestrator._resolve_dynamic_content("Bad: !(rm -rf /)")
    assert "[DISALLOWED]" in result


def test_resolve_dynamic_content_file_not_found(mock_knowledge_store):
    orchestrator = Orchestrator(MagicMock(primitives={}), mock_knowledge_store)
    result = orchestrator._resolve_dynamic_content("Include: @(/nope.txt)")
    assert "[ERROR]" in result
