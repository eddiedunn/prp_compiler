from unittest.mock import patch, MagicMock
import pytest
from src.prp_compiler.agents.planner import PlannerAgent
from src.prp_compiler.models import ReActStep, Thought, Action

class DummyPrimitiveLoader:
    def get_all(self, kind):
        if kind == 'actions':
            return [
                {"name": "retrieve_knowledge", "description": "Retrieve knowledge", "inputs_schema": {"type": "object", "properties": {"query": {"type": "string"}}}},
            ]
        return []

    def get_all_names(self, kind):
        return [a['name'] for a in self.get_all(kind)]

def make_mock_gemini_response(tool_name, args):
    class FunctionCall:
        def __init__(self, name, args):
            self.name = name
            self.args = args
    class Part:
        def __init__(self, fc):
            self.function_call = fc
    class Candidate:
        def __init__(self, parts):
            self.content = MagicMock(parts=parts)
    fc = FunctionCall(tool_name, args)
    return MagicMock(candidates=[Candidate([Part(fc)])])

def test_run_planning_loop_calls_finish(monkeypatch):
    loader = DummyPrimitiveLoader()
    planner = PlannerAgent(loader)
    calls = []
    def fake_generate_content(prompt):
        calls.append(prompt)
        return make_mock_gemini_response('retrieve_knowledge', {"query": "What is the meaning of life?"})
    with patch.object(planner.model, 'generate_content', fake_generate_content):
        planner_gen = planner.run_planning_loop("test goal", max_steps=2)
        steps = list(planner_gen)
        assert len(steps) == 2
        assert steps[0].thought.next_action.tool_name == "retrieve_knowledge"
        assert steps[1].thought.next_action.tool_name == "finish"
        # Check that history was passed to the second call
        assert any("Observation: got some data" in call for call in calls)
        # The generator should stop after the 'finish' action
        with pytest.raises(StopIteration):
            next(planner_gen)
        assert any("Observation:" in call for call in calls)
