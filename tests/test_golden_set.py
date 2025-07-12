import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.prp_compiler.main import app
from typer.testing import CliRunner

GOLDEN_DIR = Path(__file__).parent / "golden"

def find_golden_cases():
    cases = []
    if not GOLDEN_DIR.is_dir():
        return cases
    for subdir in GOLDEN_DIR.iterdir():
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


@pytest.mark.slow
@pytest.mark.parametrize("name, goal_md, expected_json_path", find_golden_cases())
@patch("src.prp_compiler.main.PrimitiveLoader") # Patch where it's instantiated
@patch("src.prp_compiler.agents.base_agent.genai.GenerativeModel") # Patch where it's used
def test_golden_prp(
    mock_generative_model,
    mock_loader_class,
    name,
    goal_md,
    expected_json_path,
    tmp_path,
    temp_agent_dir,
    mock_primitive_loader, # Use the fixture
):
    # Arrange
    mock_loader_class.return_value = mock_primitive_loader
    runner = CliRunner()
    output_file = tmp_path / "output.json"
    goal = goal_md.read_text()

    with open(expected_json_path, "r") as f:
        expected_output = json.load(f)

    # Mock the sequence of LLM calls.
    mock_planner_response = make_mock_planner_response(
        "finish",
        {"schema_choice": "base_feature_prp", "pattern_references": []},
    )
    mock_synthesizer_response = MagicMock(text=json.dumps(expected_output))

    # Configure the mock instance that will be created in the agent's __init__
    mock_instance = mock_generative_model.return_value
    mock_instance.generate_content.side_effect = [
        mock_planner_response,
        mock_synthesizer_response,
    ]

    # Act
    result = runner.invoke(
        app,
        [
            "compile",
            goal,
            "--out",
            str(output_file),
            "--primitives-path",
            str(temp_agent_dir["base"]),
        ],
    )

    # Assert
    assert result.exit_code == 0, f"CLI command failed for case '{name}': {result.stdout}\n{result.stderr}"
    assert output_file.exists()

    with open(output_file, "r") as f:
        generated_output = json.load(f)

    assert generated_output == expected_output, f"Output mismatch for case '{name}'"
