import json
import tempfile
from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.prp_compiler.main import app


@pytest.fixture
def mock_orchestrator(monkeypatch):
    class DummyOrchestrator:
        def __init__(self, loader, knowledge_store):
            pass

        def run(self, goal, constitution):
            schema_dict = {
                "type": "object",
                "properties": {
                    "goal": {"type": "string"},
                    "why": {"type": "string"},
                    "what": {"type": "object"},
                    "context": {"type": "object"},
                    "implementation_blueprint": {"type": "object"},
                    "validation_loop": {"type": "object"},
                },
                "required": [
                    "goal",
                    "why",
                    "what",
                    "context",
                    "implementation_blueprint",
                    "validation_loop",
                ],
            }
            return (
                json.dumps(schema_dict),
                "dummy context",
            )

    monkeypatch.setattr("src.prp_compiler.main.Orchestrator", DummyOrchestrator)


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

    monkeypatch.setattr("src.prp_compiler.main.KnowledgeStore", DummyKnowledgeStore)


def test_cli_compile_command(
    mock_orchestrator, mock_synthesizer, mock_configure_gemini, mock_knowledge_store
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
