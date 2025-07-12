from unittest.mock import MagicMock

import pytest

from src.prp_compiler.agents.planner import PlannerAgent


class DummyPrimitiveLoader:
    def get_all(self, kind):
        if kind == "actions":
            return [
                {
                    "name": "retrieve_knowledge",
                    "description": "Retrieve knowledge",
                    "inputs_schema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                    },
                },
            ]
        return []

    def get_all_names(self, kind):
        return [a["name"] for a in self.get_all(kind)]


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

    # Mock responses
    retrieve_response = make_mock_gemini_response(
        "retrieve_knowledge",
        {"query": "test query", "reasoning": "r1", "criticism": "c1"},
    )
    finish_response = make_mock_gemini_response(
        "finish",
        {
            "schema_choice": "standard_prp",
            "pattern_references": ["pattern1"],
            "reasoning": "r2",
            "criticism": "c2",
        },
    )

    mock_generate_content = MagicMock(side_effect=[retrieve_response, finish_response])
    monkeypatch.setattr(planner.model, "generate_content", mock_generate_content)

    # Run and interact with the generator
    user_goal = "Write a PRP for X"
    planner_gen = planner.run_planning_loop(user_goal, "", max_steps=2)

    # Assert Step 1
    next(planner_gen)  # Prime the generator
    step1 = planner_gen.send("Initial observation")
    assert step1.thought.next_action.tool_name == "retrieve_knowledge"

    # Assert Step 2 (after sending an observation)
    try:
        step2 = planner_gen.send("Mock observation for retrieve.")
        assert step2.thought.next_action.tool_name == "finish"
    except StopIteration:
        pytest.fail("Generator stopped prematurely. It should yield the 'finish' step.")

    # Assert generator is exhausted after 'finish'
    with pytest.raises(StopIteration):
        planner_gen.send("Another observation.")

    assert mock_generate_content.call_count == 2
    # Check that history was passed to the second call
    # The first argument of the first call is the prompt.
    second_call_prompt = mock_generate_content.call_args_list[1][0][0]
    assert "Observation: Mock observation for retrieve." in second_call_prompt
