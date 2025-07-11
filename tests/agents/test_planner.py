import pytest
from unittest.mock import patch, MagicMock
from src.prp_compiler.agents.planner import PlannerAgent
from src.prp_compiler.models import ManifestItem, ExecutionPlan, ToolPlanItem


@pytest.fixture
def planner_agent():
    """Provides a PlannerAgent instance for testing."""
    with patch('google.generativeai.GenerativeModel') as mock_model_constructor:
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
    tools = [ManifestItem(name='tool1', description='A test tool', file_path='/path/tool1')]
    knowledge = [ManifestItem(name='doc1', description='A knowledge doc', file_path='/path/doc1')]
    schemas = [ManifestItem(name='schema1', description='A schema', file_path='/path/schema1')]
    return tools, knowledge, schemas

def test_planner_prompt_format(planner_agent, sample_manifests):
    """Test 1: Assert that the plan() method calls the mock API with a correctly formatted prompt."""
    user_goal = "Test goal"
    tools, knowledge, schemas = sample_manifests

    # Set up a dummy response to allow the method to complete
    mock_response = MagicMock()
    mock_response.text = '{"tool_plan": [], "knowledge_plan": [], "schema_choice": ""}'
    planner_agent.mock_model.generate_content.return_value = mock_response

    planner_agent.plan(user_goal, tools, knowledge, schemas)

    # Check that generate_content was called once
    planner_agent.mock_model.generate_content.assert_called_once()
    
    # Extract the prompt passed to the mock
    prompt = planner_agent.mock_model.generate_content.call_args[0][0]

    # Assert that the prompt contains all the necessary components
    assert f'**User\'s Goal:**\n"{user_goal}"' in prompt
    assert '"name": "tool1"' in prompt
    assert '"name": "doc1"' in prompt
    assert '"name": "schema1"' in prompt

def test_planner_parses_response(planner_agent, sample_manifests):
    """Test 2: Assert that plan() correctly cleans, parses, and returns a valid ExecutionPlan."""
    user_goal = "Test goal"
    tools, knowledge, schemas = sample_manifests

    # Mocked API response with markdown fences and extra whitespace
    mocked_json_str = '''
    ```json
    {
        "tool_plan": [
            {"command_name": "tool1", "arguments": "some_args"}
        ],
        "knowledge_plan": ["doc1"],
        "schema_choice": "schema1"
    }
    ```
    '''
    mock_response = MagicMock()
    mock_response.text = mocked_json_str
    planner_agent.mock_model.generate_content.return_value = mock_response

    result = planner_agent.plan(user_goal, tools, knowledge, schemas)

    assert isinstance(result, ExecutionPlan)
    assert result.schema_choice == "schema1"
    assert result.knowledge_plan == ["doc1"]
    assert len(result.tool_plan) == 1
    assert isinstance(result.tool_plan[0], ToolPlanItem)
    assert result.tool_plan[0].command_name == "tool1"
    assert result.tool_plan[0].arguments == "some_args"
