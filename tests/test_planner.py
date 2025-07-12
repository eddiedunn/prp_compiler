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

def test_run_planning_step_calls_finish(monkeypatch):
    loader = DummyPrimitiveLoader()
    planner = PlannerAgent(loader)
    # Patch planner.model.generate_content to simulate Gemini
    calls = []
    def fake_generate_content(prompt):
        calls.append(prompt)
        if len(calls) == 1:
            return make_mock_gemini_response("retrieve_knowledge", {"query": "foo"})
        else:
            return make_mock_gemini_response("finish", {"schema_choice": "final_schema", "pattern_references": ["pat1"], "final_plan": "done"})
    monkeypatch.setattr(planner.model, "generate_content", fake_generate_content)
    history = []
    # Step 1: retrieve_knowledge
    step1 = planner.run_planning_step("my goal", history)
    assert step1.thought.next_action.tool_name == "retrieve_knowledge"
    history.append(step1)
    # Step 2: finish
    step2 = planner.run_planning_step("my goal", history)
    assert step2.thought.next_action.tool_name == "finish"
    # Check that observation from step1 is present in prompt for step2
    assert "Observation:" in calls[1]
