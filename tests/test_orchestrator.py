from unittest.mock import MagicMock, patch

import pytest

from src.prp_compiler.models import Action, ReActStep, Thought
from src.prp_compiler.orchestrator import Orchestrator


@pytest.fixture
def mock_loader():
    """A pytest fixture to create a mocked PrimitiveLoader."""
    loader = MagicMock()
    loader.primitives = {
        "actions": {
            "retrieve_knowledge": {
                "name": "retrieve_knowledge",
                "entrypoint": "src.prp_compiler.knowledge:KnowledgeStore:retrieve",
                "description": "Retrieves knowledge chunks.",
            }
        }
    }

    def get_content_side_effect(primitive_type, name):
        if primitive_type == "schemas" and name == "my_schema":
            return '{"description": "A test schema"}'
        return ""

    loader.get_primitive_content.side_effect = get_content_side_effect
    return loader


@pytest.fixture
def mock_knowledge_store():
    """A pytest fixture to create a mocked KnowledgeStore."""
    ks = MagicMock()
    ks.retrieve.return_value = ["Retrieved knowledge chunk."]
    return ks


def test_execute_action_resolves_template(mock_loader, mock_knowledge_store):
    """
    Tests that execute_action correctly loads a template, substitutes arguments,
    and returns the resolved content.
    """
    # Arrange
    action_name = "web_search"
    # FIX 2: Use the new argument syntax from orchestrator.py
    template = 'Perform a web search for: "$ARGUMENTS(query)"'

    # FIX 1: Unset the fixture's side_effect so return_value can be used.
    mock_loader.get_primitive_content.side_effect = None
    mock_loader.get_primitive_content.return_value = template

    orchestrator = Orchestrator(mock_loader, mock_knowledge_store)

    # Mock the internal dynamic content resolution to isolate the test
    orchestrator._resolve_dynamic_content = MagicMock(side_effect=lambda x: x)

    action = Action(tool_name=action_name, arguments={"query": "agentic systems"})

    # Act
    result = orchestrator.execute_action(action)

    # Assert
    mock_loader.get_primitive_content.assert_called_once_with("actions", action_name)
    orchestrator._resolve_dynamic_content.assert_called_once_with(
        'Perform a web search for: "agentic systems"'
    )
    assert result == 'Perform a web search for: "agentic systems"'
