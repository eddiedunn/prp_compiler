import pytest
from unittest.mock import patch

@pytest.fixture(autouse=True)
def mock_gemini_config():
    """Globally mocks the Gemini API configuration for all tests."""
    with patch('src.prp_compiler.agents.base_agent.get_api_key', return_value='test_key'), \
         patch('src.prp_compiler.agents.base_agent.genai.configure'):
        yield
