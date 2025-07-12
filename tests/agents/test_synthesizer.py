import json
from unittest.mock import MagicMock, patch

import pytest

from src.prp_compiler.agents.synthesizer import SynthesizerAgent


@pytest.fixture
def synthesizer_agent():
    with patch("google.generativeai.GenerativeModel") as mock_model_constructor:
        mock_model_instance = MagicMock()
        mock_model_constructor.return_value = mock_model_instance
        agent = SynthesizerAgent()
        agent.model = mock_model_instance
        return agent


def test_synthesizer_valid_json_first_try(synthesizer_agent):
    schema = {
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "why": {"type": "string"},
            "what": {"type": "object"},
            "context": {"type": "object"},
            "implementation_blueprint": {"type": "object"},
            "validation_loop": {"type": "object"},
        },
        "required": [
            "goal",
            "why",
            "what",
            "context",
            "implementation_blueprint",
            "validation_loop",
        ],
    }
    context = "irrelevant for test"
    valid_json = {
        "goal": "Test goal",
        "why": "Test why",
        "what": {},
        "context": {},
        "implementation_blueprint": {},
        "validation_loop": {},
    }
    mock_response = MagicMock()
    mock_response.text = json.dumps(valid_json)
    synthesizer_agent.model.generate_content.return_value = mock_response
    constitution = "CONSTITUTION"
    result = synthesizer_agent.synthesize(schema, context, constitution)
    assert result == valid_json
    synthesizer_agent.model.generate_content.assert_called_once()


def test_synthesizer_invalid_then_valid_json(synthesizer_agent):
    schema = {
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "why": {"type": "string"},
            "what": {"type": "object"},
            "context": {"type": "object"},
            "implementation_blueprint": {"type": "object"},
            "validation_loop": {"type": "object"},
        },
        "required": [
            "goal",
            "why",
            "what",
            "context",
            "implementation_blueprint",
            "validation_loop",
        ],
    }
    context = "irrelevant for test"
    invalid_json_str = "not a json"
    valid_json = {
        "goal": "Test goal",
        "why": "Test why",
        "what": {},
        "context": {},
        "implementation_blueprint": {},
        "validation_loop": {},
    }
    valid_json_str = json.dumps(valid_json)
    mock_response1 = MagicMock()
    mock_response1.text = invalid_json_str
    mock_response2 = MagicMock()
    mock_response2.text = valid_json_str
    synthesizer_agent.model.generate_content.side_effect = [
        mock_response1,
        mock_response2,
    ]
    constitution = "CONSTITUTION"
    result = synthesizer_agent.synthesize(schema, context, constitution)
    assert result == valid_json
    assert synthesizer_agent.model.generate_content.call_count == 2


def test_synthesizer_schema_validation_failure(synthesizer_agent):
    schema = {
        "type": "object",
        "properties": {
            "goal": {"type": "string"},
            "why": {"type": "string"},
            "what": {"type": "object"},
            "context": {"type": "object"},
            "implementation_blueprint": {"type": "object"},
            "validation_loop": {"type": "object"},
        },
        "required": [
            "goal",
            "why",
            "what",
            "context",
            "implementation_blueprint",
            "validation_loop",
        ],
    }
    context = "irrelevant for test"
    invalid_json_str = "not a json"
    valid_json = {
        "goal": "Test goal",
        "why": "Test why",
        "what": {},
        "context": {},
        "implementation_blueprint": {},
        "validation_loop": {},
    }
    valid_json_str = json.dumps(valid_json)
    mock_response1 = MagicMock()
    mock_response1.text = invalid_json_str
    mock_response2 = MagicMock()
    mock_response2.text = valid_json_str
    synthesizer_agent.model.generate_content.side_effect = [
        mock_response1,
        mock_response2,
    ]
    constitution = "CONSTITUTION"
    result = synthesizer_agent.synthesize(schema, context, constitution, max_retries=2)
    assert result == valid_json
    assert synthesizer_agent.model.generate_content.call_count == 2
