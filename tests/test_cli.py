import json
import tempfile
from pathlib import Path
from typer.testing import CliRunner
import pytest
from src.prp_compiler.main import app

@pytest.fixture
def mock_orchestrator(monkeypatch):
    class DummyOrchestrator:
        def __init__(self, loader, knowledge_store):
            pass
        def run(self, goal):
            return ({
                "type": "object",
                "properties": {
                    "goal": {"type": "string"},
                    "why": {"type": "string"},
                    "what": {"type": "object"},
                    "context": {"type": "object"},
                    "implementation_blueprint": {"type": "object"},
                    "validation_loop": {"type": "object"}
                },
                "required": ["goal", "why", "what", "context", "implementation_blueprint", "validation_loop"]
            }, "dummy context")
    monkeypatch.setattr("src.prp_compiler.main.Orchestrator", DummyOrchestrator)

@pytest.fixture
def mock_synthesizer(monkeypatch):
    class DummySynthesizer:
        def __init__(self):
            pass
        def synthesize(self, schema, context, max_retries=2):
            return {
                "goal": "Test goal",
                "why": "Test why",
                "what": {},
                "context": {},
                "implementation_blueprint": {},
                "validation_loop": {}
            }
    monkeypatch.setattr("src.prp_compiler.main.SynthesizerAgent", DummySynthesizer)

def test_cli_compile_command(mock_orchestrator, mock_synthesizer):
    runner = CliRunner()
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = Path(tmpdir) / "test.json"
        result = runner.invoke(app, ["compile", "test-goal", "--out", str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()
        with open(output_file) as f:
            data = json.load(f)
        assert data["goal"] == "Test goal"
        assert data["why"] == "Test why"
