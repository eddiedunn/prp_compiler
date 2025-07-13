import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.prp_compiler.main import compile

GOLDEN_DIR = Path(__file__).parent / "golden"


def find_golden_cases() -> list[tuple[str, Path, Path]]:
    """Return a list of (name, goal_path, expected_path) tuples for testing."""
    cases: list[tuple[str, Path, Path]] = []
    if not GOLDEN_DIR.is_dir():
        return cases

    for subdir in sorted(GOLDEN_DIR.iterdir()):
        if subdir.is_dir():
            goal_md = subdir / "goal.md"
            expected_json = subdir / "expected_prp.json"
            if goal_md.exists() and expected_json.exists():
                cases.append((subdir.name, goal_md, expected_json))
    return cases


# Helper to create a valid mock for the PlannerAgent.
# The original version was subtly flawed in its mock construction, leading
# to Pydantic validation errors where a MagicMock was passed instead of a string.
def make_mock_planner_response(tool_name: str, args: dict) -> MagicMock:
    """Return a mock Gemini response with a function call."""
    response = MagicMock()

    # Configure the nested attributes directly so attribute access on the
    # response object returns real values instead of new MagicMocks.  When the
    # code accesses `response.candidates[0].content.parts[0].function_call.name`
    # it will get the provided string rather than another mock object.
    response.candidates[0].content.parts[0].function_call.name = tool_name
    response.candidates[0].content.parts[0].function_call.args = args

    # Some parts of the code expect a ``text`` attribute on the response.
    response.text = ""
    return response


@pytest.fixture
def mock_primitive_loader():
    """Fixture to mock PrimitiveLoader to provide a required schema."""
    loader = MagicMock()
    # This is the schema content the test needs.
    schema_content = json.dumps({"name": "base_feature_prp", "description": "..."})
    loader.get_primitive_content.return_value = schema_content
    return loader


CASES = find_golden_cases()


@pytest.mark.slow
@pytest.mark.parametrize(
    "name, goal_md, expected_json_path",
    CASES,
    ids=[case[0] for case in CASES],
)
@patch("src.prp_compiler.main.configure_gemini")
@patch("src.prp_compiler.main.ChromaKnowledgeStore")
@patch("src.prp_compiler.main.PrimitiveLoader")
@patch("src.prp_compiler.agents.base_agent.genai.GenerativeModel")
def test_golden_prp(
    mock_generative_model,
    mock_loader_class,
    mock_knowledge_store_class,
    mock_configure_gemini,
    name,
    goal_md,
    expected_json_path,
    tmp_path,
    temp_agent_dir,
):
    """
    Tests the full PRP compilation process by directly calling the 'compile' function.

    This avoids issues with CliRunner and ensures mocks are applied correctly.
    """
    # Arrange
    # 1. Mock loaders and configurations
    mock_loader_instance = mock_loader_class.return_value

    # The old mock returned a JSON string for all calls to get_primitive_content,
    # which caused a KeyError when the orchestrator tried to format the "strategy" content.
    # This new mock correctly returns a strategy template or a schema based on the type.
    def get_content_side_effect(primitive_type, name):
        if primitive_type == "strategies":
            # A minimal strategy template that uses the expected variables.
            return "Goal: {user_goal}\nHistory: {history}\nTools: {tools_json_schema}"
        elif primitive_type == "schemas":
            return json.dumps({"type": "object"})
        return ""  # Default for other types like patterns

    mock_loader_instance.get_primitive_content.side_effect = get_content_side_effect
    mock_loader_instance.get_all.return_value = []
    mock_knowledge_store_instance = mock_knowledge_store_class.return_value
    mock_knowledge_store_instance.retrieve.return_value = ["mock knowledge"]

    # 2. Set up paths and read test case data
    output_file = tmp_path / "output.json"
    goal = goal_md.read_text()
    with open(expected_json_path, "r") as f:
        expected_output = json.load(f)

    # 3. Mock the sequence of LLM calls for the ReAct loop
    mock_planner_step1 = make_mock_planner_response(
        "retrieve_knowledge", {"query": "how to copy a file"}
    )
    mock_planner_step2 = make_mock_planner_response(
        "finish", {"schema_choice": "prp_base_schema", "pattern_references": []}
    )
    mock_synthesizer_response = MagicMock()
    mock_synthesizer_response.text = json.dumps(expected_output)

    # 4. Create a router for mock LLM calls to make the test more robust.
    # This avoids rigid side_effect lists that break if the call order changes.
    call_count = {"planner": 0}

    def mock_llm_router(prompt, tools=None):
        """Route LLM calls based on the tools provided and call order."""
        # Planner's first call is to select a strategy.
        if "select_strategy" in str(tools):
            return make_mock_planner_response(
                "select_strategy", {"strategy_name": "simple_feature_strategy"}
            )

        call_count["planner"] += 1

        # The first planner step retrieves knowledge.
        if call_count["planner"] == 1:
            return mock_planner_step1

        # The second planner step finishes.
        if call_count["planner"] == 2:
            return mock_planner_step2

        # The synthesizer's call contains the final context to generate the PRP.
        if "Product Requirement Prompt (PRP)" in prompt:
            return mock_synthesizer_response

        return MagicMock(text="Unexpected call")

    mock_llm_instance = mock_generative_model.return_value
    mock_llm_instance.generate_content.side_effect = mock_llm_router

    # Act
    # Directly call the compile function instead of using CliRunner
    exit_code = 0
    try:
        compile(
            goal=goal,
            output_file=output_file,
            primitives_path=temp_agent_dir["base"],
            vector_db_path=Path(tmp_path / "chroma_db"),
            constitution_path=Path("non_existent_file.md"),
            cache_db_path=Path(tmp_path / "cache.sqlite"),
            strategy=None,
            plan_file=None,
        )
    except SystemExit as e:
        # Capture the exit code if Typer raises it
        exit_code = e.code
    except Exception as e:  # pragma: no cover - unexpected errors cause failure
        pytest.fail(f"Test failed with an unexpected exception: {e}")

    # Assert
    assert exit_code == 0, (
        f"CLI function failed for case '{name}' with exit code {exit_code}"
    )
    assert output_file.exists()

    with open(output_file, "r") as f:
        generated_output = json.load(f)

    assert generated_output == expected_output, f"Output mismatch for case '{name}'"
