import pytest
from pydantic import ValidationError
from src.prp_compiler.models import ExecutionPlan, ToolPlanItem


def test_execution_plan_validation():
    """Tests that the ExecutionPlan model correctly validates data."""
    # Test valid data
    valid_data = {
        "tool_plan": [{"command_name": "test_command", "arguments": "--arg1 val1"}],
        "knowledge_plan": ["knowledge_doc_1"],
        "schema_choice": "some_schema",
    }
    plan = ExecutionPlan.model_validate(valid_data)
    assert len(plan.tool_plan) == 1
    assert isinstance(plan.tool_plan[0], ToolPlanItem)
    assert plan.knowledge_plan == ["knowledge_doc_1"]
    assert plan.schema_choice == "some_schema"

    # Test invalid data (e.g., missing required field)
    invalid_data = {
        "tool_plan": [],
        "knowledge_plan": [],
        # Missing 'schema_choice'
    }
    with pytest.raises(ValidationError):
        ExecutionPlan.model_validate(invalid_data)

    # Test invalid tool_plan item
    invalid_tool_plan = {
        "tool_plan": [{"wrong_field": "value"}],  # Missing command_name
        "knowledge_plan": [],
        "schema_choice": "some_schema",
    }
    with pytest.raises(ValidationError):
        ExecutionPlan.model_validate(invalid_tool_plan)
