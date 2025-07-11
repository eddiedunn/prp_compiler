import pytest
from unittest.mock import patch
import os
import stat
import tempfile

from src.prp_compiler.orchestrator import Orchestrator
from src.prp_compiler.models import ManifestItem, ExecutionPlan, ToolPlanItem


@pytest.fixture
def temp_capabilities(tmp_path):
    """Creates a temporary agent_capabilities directory with dummy files."""
    base_path = tmp_path / "agent_capabilities"

    schemas_path = base_path / "schemas"
    knowledge_path = base_path / "knowledge"
    tools_path = base_path / "tools"
    schemas_path.mkdir(parents=True)
    knowledge_path.mkdir(parents=True)
    tools_path.mkdir(parents=True)

    schema_file = schemas_path / "test_schema.md"
    schema_file.write_text("This is the schema template.")

    knowledge_file = knowledge_path / "test_knowledge.md"
    knowledge_file.write_text("This is the knowledge content.")

    tool_file = tools_path / "test_tool.md"
    tool_file.write_text("This is the tool content.\n!echo 'dynamic part'")

    return {"schema": schema_file, "knowledge": knowledge_file, "tool": tool_file}


@pytest.fixture
def sample_manifests(temp_capabilities):
    """Provides sample manifest data pointing to temporary files."""
    tools = [
        ManifestItem(
            name="test_tool",
            description="A test tool",
            file_path=str(temp_capabilities["tool"]),
        )
    ]
    knowledge = [
        ManifestItem(
            name="test_knowledge",
            description="A knowledge doc",
            file_path=str(temp_capabilities["knowledge"]),
        )
    ]
    schemas = [
        ManifestItem(
            name="test_schema",
            description="A schema",
            file_path=str(temp_capabilities["schema"]),
        )
    ]
    return tools, knowledge, schemas


@pytest.fixture
def orchestrator(sample_manifests):
    """Provides an Orchestrator instance initialized with sample manifests."""
    tools, knowledge, schemas = sample_manifests
    return Orchestrator(tools, knowledge, schemas)


def test_assemble_context_concatenates_content(orchestrator, temp_capabilities):
    """Tests that assemble_context reads and concatenates the full file contents."""
    plan = ExecutionPlan(
        tool_plan=[ToolPlanItem(command_name="test_tool", arguments="")],
        knowledge_plan=["test_knowledge"],
        schema_choice="test_schema",
    )

    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.return_value.stdout = "dynamic part"

        schema_template, resolved_context = orchestrator.assemble_context(plan)

        # 1. Check if schema is read correctly
        assert schema_template == temp_capabilities["schema"].read_text()

        # 2. Check if knowledge content is in the context
        assert temp_capabilities["knowledge"].read_text() in resolved_context

        # 3. Check if tool content is in the context (before dynamic resolution)
        assert "This is the tool content." in resolved_context

        # 4. Check that the dynamic part was resolved and included
        assert "dynamic part" in resolved_context

        # 5. Check concatenation separator
        assert "\n\n---\n\n" in resolved_context


def test_assemble_context_handles_missing_items(orchestrator, capsys):
    """Tests that warnings are printed for items not found in manifests."""
    plan = ExecutionPlan(
        tool_plan=[ToolPlanItem(command_name="fake_tool", arguments="")],
        knowledge_plan=["fake_knowledge"],
        schema_choice="test_schema",
    )

    _, _ = orchestrator.assemble_context(plan)

    captured = capsys.readouterr()
    assert "[WARNING] Knowledge 'fake_knowledge' not found in manifest." in captured.out
    assert "[WARNING] Tool 'fake_tool' not found in manifest." in captured.out


def test_assemble_context_schema_not_found(orchestrator):
    """Tests that a ValueError is raised if the schema is not found."""
    plan = ExecutionPlan(
        tool_plan=[], knowledge_plan=[], schema_choice="non_existent_schema"
    )
    with pytest.raises(
        ValueError, match="Schema 'non_existent_schema' not found in manifest."
    ):
        orchestrator.assemble_context(plan)


def test_resolve_dynamic_content_command_failure(orchestrator):
    """Test that a failed shell command returns an error message."""
    raw_context = "! non_existent_command_12345"
    result = orchestrator._resolve_dynamic_content(raw_context)
    assert "[ERROR: Command 'non_existent_command_12345' failed:" in result


def test_resolve_dynamic_content_file_not_found(orchestrator):
    """Test that a missing file reference returns an error message."""
    raw_context = "@ /tmp/this_file_should_not_exist_12345.txt"
    result = orchestrator._resolve_dynamic_content(raw_context)
    assert (
        result
        == "[ERROR: File not found at '/tmp/this_file_should_not_exist_12345.txt']"
    )


def test_resolve_dynamic_content_file_read_error(orchestrator):
    """Test that an unreadable file returns an error message."""
    # Create a temporary file
    fd, file_path = tempfile.mkstemp()
    os.close(fd)

    # Remove read permissions
    os.chmod(file_path, stat.S_IWUSR)
    try:
        raw_context = f"@ {file_path}"
        result = orchestrator._resolve_dynamic_content(raw_context)
        assert f"[ERROR: Could not read file at '{file_path}':" in result
    finally:
        # Restore permissions to allow deletion
        os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR)
        os.unlink(file_path)
