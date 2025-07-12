import pytest
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_gemini_model():
    """Globally mocks the Gemini model to prevent actual API calls during tests."""
    # Patching where the model is used in the agents
    with patch(
        "src.prp_compiler.agents.base_agent.genai.GenerativeModel"
    ) as mock_agent_model:
        # You can configure the mock's behavior here if needed for all tests
        # For example, setting a default return value for a method.
        yield mock_agent_model

@pytest.fixture
def mock_configure_gemini(monkeypatch):
    """Fixture to mock configure_gemini to prevent real API calls in CLI tests."""
    from unittest.mock import MagicMock
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
