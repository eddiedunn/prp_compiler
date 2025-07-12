import os
import json
import subprocess
from pathlib import Path

import pytest

def find_golden_cases(golden_dir):
    cases = []
    for subdir in Path(golden_dir).iterdir():
        if subdir.is_dir():
            goal_md = subdir / "goal.md"
            expected_json = subdir / "expected_prp.json"
            if goal_md.exists() and expected_json.exists():
                cases.append((goal_md, expected_json))
    return cases

def run_prp_compiler(goal_md_path):
    # Run the CLI, capturing output to a temp file
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        output_path = tmp.name
    # Assume CLI: prp_compiler <goal_md> --output <output_path>
    result = subprocess.run([
        "prp_compiler", str(goal_md_path), "--output", output_path
    ], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"prp_compiler failed: {result.stderr}")
    with open(output_path, "r") as f:
        generated = json.load(f)
    os.remove(output_path)
    return generated

def compare_prp_json(generated, expected):
    # Compare structure, allow some flexibility in text fields
    assert isinstance(generated, dict) and isinstance(expected, dict)
    for key in expected:
        assert key in generated, f"Missing key: {key}"
        if isinstance(expected[key], str):
            # Allow some flexibility for text fields (e.g. ignore whitespace)
            assert expected[key].strip() == generated[key].strip(), f"Mismatch in '{key}': expected '{expected[key]}', got '{generated[key]}'"
        else:
            assert expected[key] == generated[key], f"Mismatch in '{key}': expected {expected[key]}, got {generated[key]}"
    # Optionally, ensure no unexpected extra keys
    # assert set(generated.keys()) == set(expected.keys())

GOLDEN_DIR = Path(__file__).parent / "golden"

golden_cases = find_golden_cases(GOLDEN_DIR)

@pytest.mark.parametrize("goal_md,expected_json", golden_cases)
def test_golden_prp(goal_md, expected_json):
    with open(expected_json, "r") as f:
        expected = json.load(f)
    generated = run_prp_compiler(goal_md)
    compare_prp_json(generated, expected)
