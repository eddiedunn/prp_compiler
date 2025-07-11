import pytest
from unittest.mock import patch
import sys

from src.prp_compiler.main import run
from src.prp_compiler.models import ExecutionPlan, ToolPlanItem


@pytest.fixture
def temp_agent_dir(tmp_path):
    """Creates a temporary agent_capabilities directory with dummy files."""
    base_path = tmp_path / "agent_capabilities"
    tools_path = base_path / "tools"
    knowledge_path = base_path / "knowledge"
    schemas_path = base_path / "schemas"

    tools_path.mkdir(parents=True)
    knowledge_path.mkdir(parents=True)
    schemas_path.mkdir(parents=True)

    (tools_path / "sample_tool.md").write_text(
        "---\nname: sample_tool\ndescription: A test tool.\n---\nA tool."
    )
    (knowledge_path / "sample_knowledge.md").write_text(
        "---\nname: sample_knowledge\ndescription: Some knowledge.\n---\nSome knowledge."
    )
    (schemas_path / "sample_schema.md").write_text(
        "---\nname: sample_schema\ndescription: A schema template.\n---\nA schema template."
    )

    return base_path


@patch("src.prp_compiler.main.PlannerAgent")
@patch("src.prp_compiler.main.SynthesizerAgent")
def test_end_to_end_integration(
    MockSynthesizerAgent, MockPlannerAgent, temp_agent_dir, tmp_path
):
    """
    Tests the full application flow from CLI command to file output,
    with planner and synthesizer mocked.
    """
    # 1. Configure Mocks
    mock_planner_instance = MockPlannerAgent.return_value
    mock_synthesizer_instance = MockSynthesizerAgent.return_value

    # Mock Planner to return a fixed plan
    fixed_plan = ExecutionPlan(
        tool_plan=[ToolPlanItem(command_name="sample_tool", arguments="")],
        knowledge_plan=["sample_knowledge"],
        schema_choice="sample_schema",
    )
    mock_planner_instance.plan.return_value = fixed_plan

    # Mock Synthesizer to return a fixed final PRP
    expected_output_content = "This is the final generated PRP."
    mock_synthesizer_instance.synthesize.return_value = expected_output_content

    # 2. Set up sys.argv to simulate command-line execution
    output_prp_path = tmp_path / "output.prp"
    manifest_path = tmp_path / "manifest.json"

    # Correctly point to the subdirectories for each capability type
    tools_dir = temp_agent_dir / "tools"
    knowledge_dir = temp_agent_dir / "knowledge"
    schemas_dir = temp_agent_dir / "schemas"

    sys.argv = [
        "prp_compiler",
        "--goal",
        "Test goal",
        "--output",
        str(output_prp_path),
        "--tools-path",
        str(tools_dir),
        "--knowledge-path",
        str(knowledge_dir),
        "--schemas-path",
        str(schemas_dir),
        "--manifest-path",
        str(manifest_path),
    ]

    # 3. Run the main application logic
    run()

    # 4. Assertions
    # Check that the planner was called correctly
    mock_planner_instance.plan.assert_called_once()

    # Check that the synthesizer was called correctly
    mock_synthesizer_instance.synthesize.assert_called_once()

    # Check that the final output file was created and has the correct content
    assert output_prp_path.exists()
    assert output_prp_path.read_text() == expected_output_content

    # Check that the manifest file was created
    assert manifest_path.exists()
