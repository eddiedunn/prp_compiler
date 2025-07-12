import pytest
from unittest.mock import MagicMock, patch
from src.prp_compiler.orchestrator import Orchestrator
from src.prp_compiler.models import ReActStep, Thought, Action

# --- Fixtures ---

@pytest.fixture
def mock_primitive_loader():
    """
    A pytest fixture to create a comprehensively mocked PrimitiveLoader.
    This simulates the loader's behavior for different primitive types.
    """
    loader = MagicMock()

    # Define a side effect function for get_primitive to return different manifests
    def get_primitive_side_effect(primitive_type, name):
        if primitive_type == "actions" and name == "retrieve_knowledge":
            return {
                "name": "retrieve_knowledge",
                "entrypoint": "src.prp_compiler.knowledge:KnowledgeStore.retrieve",
                "description": "Retrieves knowledge chunks."
            }
        # Add other actions here if needed for future tests
        return None

    # Define a side effect function for get_primitive_content
    def get_content_side_effect(primitive_type, name):
        if primitive_type == "schemas" and name == "final_schema":
            return '{"title": "Final PRP Schema", "type": "object"}'
        if primitive_type == "patterns" and name == "api_contract_pattern":
            return "# API Contract Pattern\nThis is a pattern for defining API contracts."
        return ""

    loader.get_primitive.side_effect = get_primitive_side_effect
    loader.get_primitive_content.side_effect = get_content_side_effect
    return loader


@pytest.fixture
def mock_knowledge_store():
    """A pytest fixture to create a mocked KnowledgeStore."""
    ks = MagicMock()
    ks.retrieve.return_value = ["This is a retrieved knowledge chunk."]
    return ks


@pytest.fixture
def mock_planner_agent(monkeypatch):
    """Mocks the PlannerAgent to yield a predictable sequence of ReAct steps."""
    
    # The generator function that will replace the real planning loop
    def mock_planning_loop(*args, **kwargs):
        # Step 1: Planner decides to retrieve knowledge
        action1 = Action(tool_name="retrieve_knowledge", arguments={"query": "test query"})
        yield ReActStep(thought=Thought(reasoning="I need to know things to start.", criticism="This query might be too broad.", next_action=action1))
        
        # Step 2: Planner decides it has enough info and finishes
        action2 = Action(
            tool_name="finish", 
            arguments={
                "schema_choice": "final_schema", 
                "pattern_references": ["api_contract_pattern"]
            }
        )
        yield ReActStep(thought=Thought(reasoning="The retrieved knowledge is sufficient. I will now assemble the final PRP.", criticism="None.", next_action=action2))

    # We use monkeypatch to replace the real class instance with our mock generator
    # This is a bit tricky because the Planner is instantiated inside the Orchestrator
    # So we patch the class itself before the Orchestrator is created.
    mock_planner_class = MagicMock()
    mock_planner_class.return_value.run_planning_loop = mock_planning_loop
    monkeypatch.setattr("src.prp_compiler.orchestrator.PlannerAgent", mock_planner_class)
    return mock_planner_class


# --- Test Case ---

def test_orchestrator_run_loop_and_dynamic_dispatch(mock_primitive_loader, mock_knowledge_store, mock_planner_agent):
    """
    Tests that the Orchestrator:
    1. Correctly drives the ReAct loop provided by the mock planner.
    2. Dynamically executes the 'retrieve_knowledge' action.
    3. Assembles the final context from thoughts, observations, and patterns.
    4. Returns the correct final schema and context.
    """
    # Arrange
    # The 'importlib' patch ensures we don't try to actually import modules for actions.
    # Instead, we check that the correct underlying function (from our mock knowledge store) is called.
    orchestrator = Orchestrator(mock_primitive_loader, mock_knowledge_store)

    # Act
    # Run the orchestrator. The mock_planner_agent fixture ensures it uses our controlled loop.
    final_schema, final_context = orchestrator.run("A test goal")

    # Assert
    # 1. Assert Schema Correctness
    assert final_schema == '{"title": "Final PRP Schema", "type": "object"}'

    # 2. Assert Context Assembly and Content
    # Check that the thought process from the ReAct loop is recorded
    assert "Thought: I need to know things to start." in final_context
    assert "Action: retrieve_knowledge({'query': 'test query'})" in final_context
    
    # Check that the observation from the executed action is recorded
    assert "Observation: Retrieved 1 chunks for query: 'test query'" in final_context
    assert "Content:\nThis is a retrieved knowledge chunk." in final_context
    
    # Check that the final thought before finishing is recorded
    assert "Thought: The retrieved knowledge is sufficient. I will now assemble the final PRP." in final_context

    # Check that the content from the referenced pattern is correctly included
    assert "--- Relevant Pattern: api_contract_pattern ---" in final_context
    assert "This is a pattern for defining API contracts." in final_context

    # 3. Assert Mock Calls
    # Verify that the knowledge store's retrieve method was called exactly once with the correct query.
    # This proves the dynamic dispatch correctly routed the 'retrieve_knowledge' action to the right place.
    mock_knowledge_store.retrieve.assert_called_once_with("test query")