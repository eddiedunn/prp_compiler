import json
import tempfile
from pathlib import Path

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
    class DummyOrchestrator:
        def __init__(self, loader, knowledge_store, result_cache):
            pass

        def run(self, goal, constitution, max_steps=10, strategy_name=None):
            return (
                "test_schema",
                "dummy context",
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
        result = runner.invoke(
            app,
            [
                "compile",
                "test-goal",
                "--out",
                str(output_file),
                "--primitives-path",
                str(primitives_dir),
            ],
        )

        assert result.exit_code == 0, (
            f"CLI command failed.\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert data["goal"] == "Test goal"
        assert data["why"] == "Test why"
