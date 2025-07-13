import json
import tempfile
from pathlib import Path
from typing import List

import pytest
from typer.testing import CliRunner

from src.prp_compiler.main import app


@pytest.fixture
def mock_result_cache(monkeypatch):
    class DummyResultCache:
        def __init__(self, db_path):
            pass

        def get(self, key):
            return None

        def set(self, key, value):
            pass

    monkeypatch.setattr("src.prp_compiler.main.ResultCache", DummyResultCache)


@pytest.fixture
def mock_orchestrator(monkeypatch):
    class DummyContext:
        def get_structured_history(self):
            return [{"thought": {"reasoning": "r", "criticism": "", "next_action": {"tool_name": "finish", "arguments": {}}}, "observation": "o"}]

    class DummyOrchestrator:
        def __init__(self, loader, knowledge_store, result_cache, debug=False):
            self.debug = debug

        def run(self, goal, constitution, max_steps=10, strategy_name=None):
            if self.debug:
                typer.echo("Thought: r")
                typer.echo("Action: finish({})")
                typer.echo("Observation: o")
            return (
                "test_schema",
                "dummy context",
                DummyContext(),
            )

    monkeypatch.setattr("src.prp_compiler.main.Orchestrator", DummyOrchestrator)


@pytest.fixture
def mock_primitive_loader(monkeypatch):
    class DummyLoader:
        def __init__(self, base_path):
            pass

        def get_primitive_content(self, p_type, name):
            if p_type == "schemas" and name == "test_schema":
                schema_dict = {
                    "type": "object",
                    "properties": {"goal": {"type": "string"}},
                }
                return json.dumps(schema_dict)
            return ""

        def get_all(self, p_type):
            return []

    monkeypatch.setattr("src.prp_compiler.main.PrimitiveLoader", DummyLoader)


@pytest.fixture
def mock_synthesizer(monkeypatch):
    class DummySynthesizer:
        def __init__(self):
            pass

        def synthesize(self, schema, context, constitution, max_retries=2):
            return {
                "goal": "Test goal",
                "why": "Test why",
                "what": {},
                "context": {},
                "implementation_blueprint": {},
                "validation_loop": {},
            }

    monkeypatch.setattr("src.prp_compiler.main.SynthesizerAgent", DummySynthesizer)


@pytest.fixture
def mock_knowledge_store(monkeypatch):
    class DummyKnowledgeStore:
        def __init__(self, persist_directory):
            pass

        def build(self, knowledge_primitives):
            pass

        def load(self):
            pass

        def retrieve(self, query: str, k: int = 5) -> List[str]:
            return [f"Mocked knowledge for '{query}'"]

    monkeypatch.setattr(
        "src.prp_compiler.main.ChromaKnowledgeStore", DummyKnowledgeStore
    )


def test_cli_compile_command(
    mock_orchestrator,
    mock_synthesizer,
    mock_configure_gemini,
    mock_knowledge_store,
    mock_primitive_loader,
    mock_result_cache,
):
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test.json"
        # Create a dummy primitives directory so the loader doesn't fail
        primitives_dir = Path(tmpdir) / "agent_primitives"
        primitives_dir.mkdir()
        plan_file = Path(tmpdir) / "plan.txt"
        result = runner.invoke(
            app,
            [
                "compile",
                "test-goal",
                "--out",
                str(output_file),
                "--plan-out",
                str(plan_file),
                "--primitives-path",
                str(primitives_dir),
            ],
        )

        assert result.exit_code == 0, (
            f"CLI command failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        assert output_file.exists()
        assert plan_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert data["goal"] == "Test goal"
        assert data["why"] == "Test why"
        plan_json = json.loads(plan_file.read_text())
        assert isinstance(plan_json, list)


def test_cli_debug_flag_outputs_steps(
    mock_orchestrator,
    mock_synthesizer,
    mock_configure_gemini,
    mock_knowledge_store,
    mock_primitive_loader,
    mock_result_cache,
):
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test.json"
        primitives_dir = Path(tmpdir) / "agent_primitives"
        primitives_dir.mkdir()
        plan_file = Path(tmpdir) / "plan.json"
        result = runner.invoke(
            app,
            [
                "compile",
                "test-goal",
                "--out",
                str(output_file),
                "--plan-out",
                str(plan_file),
                "--primitives-path",
                str(primitives_dir),
                "--debug",
            ],
        )

        assert result.exit_code == 0
        assert "Thought:" in result.stdout
        assert "Action:" in result.stdout
        assert "Observation:" in result.stdout
