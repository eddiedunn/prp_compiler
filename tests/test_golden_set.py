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
@patch('src.prp_compiler.main.Orchestrator')
@patch('src.prp_compiler.main.SynthesizerAgent')
@patch('src.prp_compiler.main.configure_gemini')
@patch('src.prp_compiler.main.KnowledgeStore')
def test_golden_prp(mock_ks, mock_config, mock_synth, mock_orch, name, goal_md, expected_json_path, tmp_path):
    # Arrange
    runner = CliRunner()
    output_file = tmp_path / "output.json"
    goal = goal_md.read_text()
    
    with open(expected_json_path, "r") as f:
        expected_output = json.load(f)

    # Mock the agents to return predictable output
    mock_orchestrator_instance = mock_orch.return_value
    mock_orchestrator_instance.run.return_value = ('{}', 'Final context')

    mock_synthesizer_instance = mock_synth.return_value
    mock_synthesizer_instance.synthesize.return_value = expected_output

    # Act
    result = runner.invoke(app, ["compile", goal, "--out", str(output_file)])

    # Assert
    assert result.exit_code == 0, f"CLI command failed for case '{name}': {result.stdout}"
    assert output_file.exists()
    
    with open(output_file, 'r') as f:
        generated_output = json.load(f)

    assert generated_output == expected_output, f"Output mismatch for case '{name}'"
