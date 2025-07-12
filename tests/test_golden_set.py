import json
import os
import subprocess
import sys
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
    goal_text = goal_md_path.read_text().strip().replace("\n", " ")
    # Run the CLI, capturing output to a temp file
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as tmp:
        output_path_str = tmp.name

    cmd = [
        sys.executable,
        "-m",
        "prp_compiler.main",
        "compile",
        goal_text,
        "--out",
        output_path_str,
    ]

    try:
        # Using check=False to capture output even on failure
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)

        if result.returncode == 0:
            with open(output_path_str, "r") as f:
                generated = json.load(f)
            os.remove(output_path_str)
            return generated
        else:
            last_error = f"Command: {' '.join(cmd)}\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
    finally:
        if os.path.exists(output_path_str):
            os.remove(output_path_str)

    raise RuntimeError(f"All CLI invocations failed. Last error:\n{last_error}")


def compare_prp_json(generated, expected):
    # Compare structure, allow some flexibility in text fields
    import difflib

    assert isinstance(generated, dict) and isinstance(expected, dict), (
        f"Generated and expected must be dicts. Got: {type(generated)} and {type(expected)}"
    )
    for key in expected:
        assert key in generated, (
            f"Missing key: {key}\nExpected keys: {list(expected.keys())}\nGenerated keys: {list(generated.keys())}"
        )
        if isinstance(expected[key], str):
            exp, gen = expected[key].strip(), generated[key].strip()
            if exp != gen:
                diff = "\n".join(
                    difflib.unified_diff(
                        exp.splitlines(),
                        gen.splitlines(),
                        fromfile="expected",
                        tofile="generated",
                        lineterm="",
                    )
                )
                raise AssertionError(
                    f"Mismatch in '{key}':\nDiff:\n{diff}\nExpected:\n{exp}\nGenerated:\n{gen}"
                )
        else:
            if expected[key] != generated[key]:
                raise AssertionError(
                    f"Mismatch in '{key}':\nExpected: {expected[key]}\nGenerated: {generated[key]}"
                )


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
