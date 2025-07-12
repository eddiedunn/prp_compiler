import pytest
from unittest.mock import patch, MagicMock
from src.prp_compiler.agents.planner import PlannerAgent
from src.prp_compiler.models import ManifestItem

class DummyPrimitiveLoader:
    def get_all(self, kind):
        if kind == 'actions':
            return [
                {
                    "name": "retrieve_knowledge",
                    "description": "Retrieve knowledge",
                    "arguments": "A query string"
                }
            ]
        return []

@pytest.fixture
def planner_agent():
    """Provides a PlannerAgent instance for testing."""
    with patch("google.generativeai.GenerativeModel") as mock_model_constructor:
        # Mock the model instance returned by the constructor
        mock_model_instance = MagicMock()
        mock_model_constructor.return_value = mock_model_instance
        agent = PlannerAgent()
        # Attach the mock to the agent instance for easy access in tests
        agent.mock_model = mock_model_instance
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


@patch("src.prp_compiler.agents.planner.BaseAgent")
def test_run_planning_loop(mock_base_agent):
    # Setup
    primitive_loader = DummyPrimitiveLoader()
    planner = PlannerAgent(primitive_loader)

    # Mock the Gemini model's generate_content to return two sequential responses
    mock_model = MagicMock()
    planner.model = mock_model

    # Mock function_call objects for two steps
    retrieve_fc = MagicMock()
    retrieve_fc.name = "retrieve_knowledge"
    retrieve_fc.args = {"query": "test query"}
    finish_fc = MagicMock()
    finish_fc.name = "finish"
    finish_fc.args = {"schema_choice": "standard_prp", "pattern_references": ["pattern1"]}

    # Mock response objects
    retrieve_response = MagicMock()
    retrieve_response.candidates = [MagicMock(content=MagicMock(parts=[MagicMock(function_call=retrieve_fc)]))]
    finish_response = MagicMock()
    finish_response.candidates = [MagicMock(content=MagicMock(parts=[MagicMock(function_call=finish_fc)]))]

    # Side effect for generate_content: first call returns retrieve, second returns finish
    mock_model.generate_content.side_effect = [retrieve_response, finish_response]

    # Run
    user_goal = "Write a PRP for X"
    steps = planner.run_planning_loop(user_goal, max_steps=2)

    # Assert
    assert len(steps) == 2
    assert steps[0].thought.next_action.tool_name == "retrieve_knowledge"
    assert steps[1].thought.next_action.tool_name == "finish"
