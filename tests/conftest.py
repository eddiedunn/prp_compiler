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
