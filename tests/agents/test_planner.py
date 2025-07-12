from unittest.mock import MagicMock

import pytest

from src.prp_compiler.agents.planner import PlannerAgent
from src.prp_compiler.models import ManifestItem


class DummyPrimitiveLoader:
    def get_all(self, kind):
        if kind == "actions":
            return [
                {
                    "name": "retrieve_knowledge",
                    "description": "Retrieve knowledge",
                    "arguments": "A query string",
                }
            ]
        return []


@pytest.fixture
def planner_agent(monkeypatch):
    """Provides a PlannerAgent instance for testing."""
    mock_model_instance = MagicMock()
    monkeypatch.setattr(
        "google.generativeai.GenerativeModel",
        MagicMock(return_value=mock_model_instance),
    )

    loader = DummyPrimitiveLoader()
    agent = PlannerAgent(loader)
    agent.model = mock_model_instance
    return agent


@pytest.fixture
def sample_manifests():
    """Provides sample manifest data for testing."""
    tools = [
        ManifestItem(name="tool1", description="A test tool", file_path="/path/tool1")
    ]
    knowledge = [
        ManifestItem(name="doc1", description="A knowledge doc", file_path="/path/doc1")
    ]
    schemas = [
        ManifestItem(name="schema1", description="A schema", file_path="/path/schema1")
    ]
    return tools, knowledge, schemas


def test_run_planning_loop(planner_agent):
    # Setup
    mock_model = planner_agent.model

    # Mock function_call objects for two steps
    retrieve_fc = MagicMock()
    retrieve_fc.name = "retrieve_knowledge"
    retrieve_fc.args = {"query": "test query", "reasoning": "r1", "criticism": "c1"}

    finish_fc = MagicMock()
    finish_fc.name = "finish"
    finish_fc.args = {
        "schema_choice": "standard_prp",
        "pattern_references": ["pattern1"],
        "reasoning": "r2",
        "criticism": "c2",
    }

    # Mock response objects
    retrieve_response = MagicMock()
    retrieve_response.candidates = [
        MagicMock(content=MagicMock(parts=[MagicMock(function_call=retrieve_fc)]))
    ]
    finish_response = MagicMock()
    finish_response.candidates = [
        MagicMock(content=MagicMock(parts=[MagicMock(function_call=finish_fc)]))
    ]

    # Side effect for generate_content: first call returns retrieve, second returns finish
    mock_model.generate_content.side_effect = [retrieve_response, finish_response]

    # Run and interact with the generator
    user_goal = "Write a PRP for X"
    planner_gen = planner_agent.run_planning_loop(user_goal, max_steps=2)

    # Assert Step 1
    step1 = next(planner_gen)
    assert step1.thought.next_action.tool_name == "retrieve_knowledge"

    # Assert Step 2 (after sending an observation)
    try:
        step2 = planner_gen.send("Mock observation for retrieve.")
        assert step2.thought.next_action.tool_name == "finish"
    except StopIteration:
        pytest.fail("Generator stopped prematurely. It should yield the 'finish' step.")

    # Assert generator is exhausted after 'finish'
    with pytest.raises(StopIteration):
        planner_gen.send("Another observation.")
