import json
from unittest.mock import MagicMock

import pytest

from src.prp_compiler.agents.synthesizer import SynthesizerAgent


@pytest.fixture
def synthesizer_agent():
    agent = SynthesizerAgent()
    agent.model = MagicMock() # Mock the model at instance level
    return agent

@pytest.fixture
def sample_schema():
    return {
        "type": "object",
        "properties": {"goal": {"type": "string"}},
        "required": ["goal"]
    }

def test_synthesizer_valid_json_first_try(synthesizer_agent, sample_schema):
    # Arrange
    valid_json = {"goal": "Test goal"}
    mock_response = MagicMock(text=json.dumps(valid_json))
    synthesizer_agent.model.generate_content.return_value = mock_response

    # Act
    result = synthesizer_agent.synthesize(sample_schema, "context", "constitution")

    # Assert
    assert result == valid_json
    synthesizer_agent.model.generate_content.assert_called_once()

def test_synthesizer_invalid_then_valid_json(synthesizer_agent, sample_schema):
    # Arrange
    invalid_json_str = '{"wrong_key": "Test goal"}' # Fails schema validation
    valid_json = {"goal": "Test goal"}

    mock_response1 = MagicMock(text=invalid_json_str)
    mock_response2 = MagicMock(text=json.dumps(valid_json))
    synthesizer_agent.model.generate_content.side_effect = [
        mock_response1, mock_response2
    ]

    # Act
    result = synthesizer_agent.synthesize(
        sample_schema, "context", "constitution", max_retries=2
    )

    # Assert
    assert result == valid_json
    assert synthesizer_agent.model.generate_content.call_count == 2
    # Check that the second prompt contained the error message
    second_call_prompt = (
        synthesizer_agent.model.generate_content.call_args_list[1][0][0]
    )
    assert "PREVIOUS ATTEMPT FAILED" in second_call_prompt
    assert "'goal' is a required property" in second_call_prompt

def test_synthesizer_fails_after_max_retries(synthesizer_agent, sample_schema):
    # Arrange
    invalid_response = MagicMock(text='{"wrong_key": "bad"}')
    synthesizer_agent.model.generate_content.return_value = invalid_response

    # Act & Assert
    with pytest.raises(
        RuntimeError, match="failed to produce a valid PRP JSON after 2 attempts"
    ):
        synthesizer_agent.synthesize(
            sample_schema, "context", "constitution", max_retries=2
        )
    assert synthesizer_agent.model.generate_content.call_count == 2
