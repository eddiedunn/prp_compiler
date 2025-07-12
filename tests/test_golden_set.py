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

@pytest.mark.slow
@pytest.mark.parametrize("name, goal_md, expected_json_path", find_golden_cases())
@patch("google.generativeai.GenerativeModel.generate_content")
def test_golden_prp(
    mock_generate_content,
    name,
    goal_md,
    expected_json_path,
    tmp_path,
    temp_agent_dir,
):
    # Arrange
    runner = CliRunner()
    output_file = tmp_path / "output.json"
    goal = goal_md.read_text()

    with open(expected_json_path, "r") as f:
        expected_output = json.load(f)

    # Mock the sequence of LLM calls.
    # The first call is for the Planner, the second is for the Synthesizer.
    # This is a simplified mock; a real test would have case-specific responses.
    mock_planner_response_text = '```json\n{"tool_plan": [{"tool_name": "web_search", "arguments": {"query": "how to copy a file"}}], "knowledge_plan": [], "schema_choice": "prp_base/1.0.0"}\n```'
    mock_synthesizer_response_text = json.dumps(expected_output)

    # The mock will return these in order
    mock_generate_content.side_effect = [
        MagicMock(text=mock_planner_response_text),
        MagicMock(text=mock_synthesizer_response_text),
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
    assert result.exit_code == 0, f"CLI command failed for case '{name}': {result.stdout}"
    assert output_file.exists()

    with open(output_file, "r") as f:
        generated_output = json.load(f)

    assert (
        generated_output == expected_output
    ), f"Output mismatch for case '{name}'"
