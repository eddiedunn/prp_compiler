import pytest
from unittest.mock import patch, MagicMock
from src.prp_compiler.agents.synthesizer import SynthesizerAgent


@pytest.fixture
def synthesizer_agent():
    """Provides a SynthesizerAgent instance for testing."""
    with patch("google.generativeai.GenerativeModel") as mock_model_constructor:
        mock_model_instance = MagicMock()
        mock_model_constructor.return_value = mock_model_instance
        agent = SynthesizerAgent()
        agent.mock_model = mock_model_instance
        return agent


def test_synthesizer_prompt_format(synthesizer_agent):
    """Test that the synthesize() method constructs the correct prompt."""
    schema_template = "# My Schema\n## Section 1"
    context = "This is the assembled context from various sources."
    expected_prp = "This is the final generated PRP."

    # Set up the mock response
    mock_response = MagicMock()
    mock_response.text = expected_prp
    synthesizer_agent.mock_model.generate_content.return_value = mock_response

    # Call the method
    result = synthesizer_agent.synthesize(schema_template, context)

    # Check that the result is what the mock returned
    assert result == expected_prp

    # Check that generate_content was called once
    synthesizer_agent.mock_model.generate_content.assert_called_once()

    # Extract the prompt passed to the mock
    prompt = synthesizer_agent.mock_model.generate_content.call_args[0][0]

    # Assert that the prompt contains the schema and context
    assert f"**Schema Template:**\n---\n{schema_template}\n---" in prompt
    assert f"**Assembled Context:**\n---\n{context}\n---" in prompt
    assert "Now, generate the final PRP as a complete Markdown document." in prompt
