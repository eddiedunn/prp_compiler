from unittest.mock import MagicMock, patch

import pytest

from src.prp_compiler.models import Action, ReActStep, Thought
from src.prp_compiler.orchestrator import Orchestrator


@pytest.fixture
def mock_loader():
    """A pytest fixture to create a mocked PrimitiveLoader."""
    loader = MagicMock()

    def get_primitive_side_effect(primitive_type, name):
        if primitive_type == "actions" and name == "retrieve_knowledge":
            return {
                "name": "retrieve_knowledge",
                "entrypoint": "src.prp_compiler.knowledge:KnowledgeStore:retrieve",
                "description": "Retrieves knowledge chunks.",
            }
        return None

    def get_content_side_effect(primitive_type, name):
        if primitive_type == "schemas" and name == "my_schema":
            return '{"description": "A test schema"}'
        if primitive_type == "patterns" and name == "my_pattern":
            return "This is the pattern content."
        return ""

    loader.get_primitive.side_effect = get_primitive_side_effect
    loader.get_primitive_content.side_effect = get_content_side_effect
    return loader


@pytest.fixture
def mock_knowledge_store():
    """A pytest fixture to create a mocked KnowledgeStore."""
    ks = MagicMock()
    ks.retrieve.return_value = ["Retrieved knowledge chunk."]
    return ks


@patch("importlib.import_module")
def test_orchestrator_dynamic_action(
    mock_import_module, mock_loader, mock_knowledge_store
):
    """Tests that the orchestrator dynamically imports and calls the action."""
    # Arrange
    mock_run_func = MagicMock(return_value="Action successful!")
    mock_module = MagicMock()
    mock_module.run = mock_run_func
    mock_import_module.return_value = mock_module

    orchestrator = Orchestrator(mock_loader, mock_knowledge_store)

    # Redefine the mock planner to return a simpler action
    def mock_planning_loop(*args, **kwargs):
        action = Action(
            tool_name="retrieve_knowledge", arguments={"query": "test query"}
        )
        yield ReActStep(
            thought=Thought(reasoning="test", criticism="test", next_action=action)
        )
        # Immediately finish
        finish_action = Action(
            tool_name="finish",
            arguments={"schema_choice": "my_schema", "pattern_references": []},
        )
        yield ReActStep(
            thought=Thought(
                reasoning="done", criticism="none", next_action=finish_action
            )
        )

    orchestrator.planner.run_planning_loop = mock_planning_loop

    # Act
    schema, context = orchestrator.run("test goal")

    # Assert
    # Check that the mock function was called
    mock_knowledge_store.retrieve.assert_called_once_with(query="test query")
    # Check that the observation from the mock call is in the context
    assert "Observation: ['Retrieved knowledge chunk.']" in context
