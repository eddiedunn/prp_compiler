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
    cli_commands = [
        ["prp-compiler", str(goal_md_path), "--output"],
        ["prp_compiler", str(goal_md_path), "--output"]
    ]
    last_error = None
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        output_path = tmp.name
    for cmd_base in cli_commands:
        cmd = cmd_base + [output_path]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                with open(output_path, "r") as f:
                    generated = json.load(f)
                os.remove(output_path)
                return generated
            else:
                last_error = f"Command: {' '.join(cmd)}\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
        except FileNotFoundError as e:
            last_error = f"Command not found: {' '.join(cmd)}\nError: {e}"
            continue
    os.remove(output_path)
    raise RuntimeError(f"All CLI invocations failed. Last error:\n{last_error}")

def compare_prp_json(generated, expected):
    # Compare structure, allow some flexibility in text fields
    import difflib
    assert isinstance(generated, dict) and isinstance(expected, dict), f"Generated and expected must be dicts. Got: {type(generated)} and {type(expected)}"
    for key in expected:
        assert key in generated, f"Missing key: {key}\nExpected keys: {list(expected.keys())}\nGenerated keys: {list(generated.keys())}"
        if isinstance(expected[key], str):
            exp, gen = expected[key].strip(), generated[key].strip()
            if exp != gen:
                diff = '\n'.join(difflib.unified_diff(exp.splitlines(), gen.splitlines(), fromfile='expected', tofile='generated', lineterm=''))
                raise AssertionError(f"Mismatch in '{key}':\nDiff:\n{diff}\nExpected:\n{exp}\nGenerated:\n{gen}")
        else:
            if expected[key] != generated[key]:
                raise AssertionError(f"Mismatch in '{key}':\nExpected: {expected[key]}\nGenerated: {generated[key]}")

GOLDEN_DIR = Path(__file__).parent / "golden"
golden_cases = find_golden_cases(GOLDEN_DIR)

@pytest.mark.slow  # Mark golden tests as slow
@pytest.mark.skipif(not golden_cases, reason="No golden cases found")
@pytest.mark.parametrize("goal_md,expected_json", golden_cases)
def test_golden_prp(goal_md, expected_json):
    with open(expected_json, "r") as f:
        expected = json.load(f)
    generated = run_prp_compiler(goal_md)
    compare_prp_json(generated, expected)
