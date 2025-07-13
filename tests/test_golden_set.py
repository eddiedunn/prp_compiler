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
# This version ensures `fc.args` is a dict, as the planner expects.
def make_mock_planner_response(tool_name, args):
    fc = MagicMock()
    fc.name = tool_name
    fc.args = args  # The planner agent's `dict(fc.args)` works on a real dict.
    part = MagicMock(function_call=fc)
    candidate = MagicMock(content=MagicMock(parts=[part]))
    return MagicMock(candidates=[candidate])


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
@patch("src.prp_compiler.main.KnowledgeStore")
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
    # Mock the loader to return a valid schema when get_primitive_content is called.
    # This is what the compile() function actually calls.
    mock_loader_instance.get_primitive_content.return_value = json.dumps(
        {"type": "object"}
    )
    mock_knowledge_store_class.return_value

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
    mock_synthesizer_response = MagicMock(text=json.dumps(expected_output))

    mock_llm_instance = mock_generative_model.return_value
    mock_llm_instance.generate_content.side_effect = [
        mock_planner_step1,
        mock_planner_step2,
        mock_synthesizer_response,
    ]

    # Act
    # Directly call the compile function instead of using CliRunner
    try:
        compile(
            goal=goal,
            output_file=output_file,
            primitives_path=temp_agent_dir["base"],
            vector_db_path=Path(tmp_path / "chroma_db"),
            constitution_path=Path("non_existent_file.md"),
        )
        # We expect this to succeed
        exit_code = 0
    except SystemExit as e:
        # Capture the exit code if Typer raises it
        exit_code = e.code

    # Assert
    assert exit_code == 0, (
        f"CLI function failed for case '{name}' with exit code {exit_code}"
    )
    assert output_file.exists()

    with open(output_file, "r") as f:
        generated_output = json.load(f)

    assert generated_output == expected_output, f"Output mismatch for case '{name}'"
