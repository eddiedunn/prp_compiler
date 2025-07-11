from prp_compiler.models import ExecutionPlan
from prp_compiler.config import configure_gemini

def test_models():
    # This will fail if the model is invalid
    ExecutionPlan.parse_obj({
        "tool_plan": [{"command_name": "test", "arguments": "args"}],
        "knowledge_plan": ["doc1"],
        "schema_choice": "schema1"
    })
    print("Pydantic models are valid.")

def test_config():
    try:
        configure_gemini()
    except ValueError as e:
        # This is expected if the key isn't set yet
        print(f"Config function works as expected: {e}")

test_models()
test_config()
