import json
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture(autouse=True)
def mock_google_embeddings(monkeypatch):
    """Globally mocks GoogleGenerativeAIEmbeddings to prevent auth errors."""
    mock_embeddings_class = MagicMock()
    mock_instance = mock_embeddings_class.return_value
    # The mock needs to return a list of lists for the embeddings
    mock_instance.embed_documents.return_value = [[1.0, 2.0, 3.0]]
    monkeypatch.setattr(
        "src.prp_compiler.knowledge.GoogleGenerativeAIEmbeddings",
        mock_embeddings_class
    )

@pytest.fixture
def mock_configure_gemini(monkeypatch):
    """Fixture to mock configure_gemini to prevent real API calls in CLI tests."""
    mock = MagicMock()
    monkeypatch.setattr("src.prp_compiler.config.configure_gemini", mock)
    yield mock


@pytest.fixture(scope="session")
def temp_agent_dir(tmp_path_factory):
    """Creates a temporary agent_capabilities directory with dummy files for session-wide use."""
    base_path = tmp_path_factory.mktemp("agent_capabilities_session")

    # Define paths
    schemas_path = base_path / "schemas"
    knowledge_path = base_path / "knowledge"
    tools_path = base_path / "tools"

    # Create directories
    schemas_path.mkdir()
    knowledge_path.mkdir()
    tools_path.mkdir()

    # Create dummy schema file
    (schemas_path / "test_schema.md").write_text("""---
name: test_schema
description: A test schema.
---
Schema content here.""")

    # Create dummy knowledge file
    (knowledge_path / "test_knowledge.md").write_text("""---
name: test_knowledge
description: A knowledge document.
---
Knowledge content here.""")

    # Create dummy tool file
    (tools_path / "test_tool.md").write_text("""---
name: test_tool
description: A test tool.
---
Tool content with !echo 'dynamic'.""")

    return {
        "base": base_path,
        "schemas": schemas_path,
        "knowledge": knowledge_path,
        "tools": tools_path,
    }
