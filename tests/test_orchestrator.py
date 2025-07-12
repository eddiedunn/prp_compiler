from unittest.mock import MagicMock
import pytest
from src.prp_compiler.orchestrator import Orchestrator

class DummyPrimitiveLoader:
    def get_all_names(self, kind):
        return ["retrieve_knowledge"]
    def get_primitive(self, kind, name):
        if kind == "schemas" and name == "my_schema":
            return {"base_path": "/tmp", "entrypoint": "schema.json"}
        return None

class DummyKnowledgeStore:
    def __init__(self):
        self.retrieve = MagicMock(return_value=["doc1", "doc2"])

class DummyPlanner:
    def __init__(self, steps):
        self.steps = steps
        self.idx = 0
    def run_planning_step(self, user_goal, history):
        step = self.steps[self.idx]
        self.idx += 1
        return step

class DummyAction:
    def __init__(self, tool_name, arguments):
        self.tool_name = tool_name
        self.arguments = arguments

class DummyThought:
    def __init__(self, tool_name, arguments):
        self.reasoning = ""
        self.criticism = ""
        self.next_action = DummyAction(tool_name, arguments)

class DummyReActStep:
    def __init__(self, tool_name, arguments):
        self.thought = DummyThought(tool_name, arguments)
        self.observation = None

def test_run_orchestrates_loop(monkeypatch):
    loader = DummyPrimitiveLoader()
    knowledge_store = DummyKnowledgeStore()
    # Sequence: retrieve_knowledge, then finish
    steps = [
        DummyReActStep("retrieve_knowledge", {"query": "foo"}),
        DummyReActStep("finish", {"schema_choice": "my_schema", "pattern_references": ["pat1"], "final_plan": "done"}),
    ]
    orchestrator = Orchestrator(loader, knowledge_store)
    orchestrator.planner = DummyPlanner(steps)
    schema, context = orchestrator.run("my user goal")
    # Check that retrieve was called
    knowledge_store.retrieve.assert_called_with("foo")
    assert schema["entrypoint"] == "schema.json"
    assert context == "done"


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


def test_orchestrator_run_integration(monkeypatch):
    """
    Integration test for Orchestrator.run with mocked PlannerAgent and KnowledgeStore.
    """
    from src.prp_compiler.orchestrator import Orchestrator
    from src.prp_compiler.models import ReActStep, Thought, Action

    # Dummy primitive loader with minimal structure
    class DummyPrimitiveLoader:
        primitives = {
            'schemas': {
                'standard_prp': {'content': 'SCHEMA_CONTENT'}
            },
            'patterns': {
                'pattern1': {'content': 'PATTERN_CONTENT'}
            }
        }

    # Mock PlannerAgent to return two steps: retrieve_knowledge then finish
    class DummyPlanner:
        def run_planning_loop(self, user_goal, max_steps=10):
            retrieve_action = Action(tool_name="retrieve_knowledge", arguments={"query": "test query"})
            finish_action = Action(tool_name="finish", arguments={"schema_choice": "standard_prp", "pattern_references": ["pattern1"]})
            step1 = ReActStep(thought=Thought(reasoning="r1", criticism="c1", next_action=retrieve_action))
            step2 = ReActStep(thought=Thought(reasoning="r2", criticism="c2", next_action=finish_action))
            return [step1, step2]

    # Mock KnowledgeStore
    class DummyKnowledgeStore:
        def __init__(self):
            self.last_query = None
        def retrieve(self, query):
            self.last_query = query
            return ["MOCK_KNOWLEDGE"]

    dummy_loader = DummyPrimitiveLoader()
    dummy_knowledge = DummyKnowledgeStore()
    orchestrator = Orchestrator(dummy_loader, dummy_knowledge)
    orchestrator.planner = DummyPlanner()  # Inject mock planner

    user_goal = "Write a PRP for X"
    schema, context = orchestrator.run(user_goal)
    assert schema == 'SCHEMA_CONTENT'
    assert 'MOCK_KNOWLEDGE' in context
    assert 'PATTERN_CONTENT' in context
    assert dummy_knowledge.last_query == "test query"


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
    # Use an allowed command that will fail.
    command = "ls /this/path/should/not/exist"
    raw_context = f"!{command}"
    result = orchestrator._resolve_dynamic_content(raw_context)
    assert f"[ERROR: Command '{command}' failed:" in result


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


def test_resolve_dynamic_content_with_quoted_arguments(orchestrator):
    """Test that shell commands with spaces and quotes are handled correctly."""
    raw_context = '!git commit -m "feat: a test message"'
    expected_command = ["git", "commit", "-m", "feat: a test message"]

    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.return_value.stdout = "Success"
        orchestrator._resolve_dynamic_content(raw_context)
        # Assert that subprocess.run was called with the correctly parsed list
        mock_subprocess_run.assert_called_with(
            expected_command,
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )


def test_resolve_dynamic_content_disallowed_command(orchestrator):
    """Test that a disallowed shell command is blocked."""
    raw_context = "!rm -rf /"
    result = orchestrator._resolve_dynamic_content(raw_context)
    assert "[ERROR: Command 'rm' is not in the allowlist.]" in result


def test_resolve_dynamic_content_allowed_command(orchestrator):
    """Test that an allowed shell command is executed."""
    raw_context = "!echo 'hello'"
    with patch("subprocess.run") as mock_subprocess_run:
        mock_subprocess_run.return_value.stdout = "hello"
        result = orchestrator._resolve_dynamic_content(raw_context)
        assert result == "hello"
        mock_subprocess_run.assert_called_once()


def test_resolve_dynamic_content_empty_command(orchestrator):
    """Test that an empty command string is handled."""
    raw_context = "! "
    result = orchestrator._resolve_dynamic_content(raw_context)
    assert "[ERROR: Command '' is not in the allowlist.]" in result
