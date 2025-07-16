import json

from jsonschema import ValidationError, validate

from .base_agent import BaseAgent

SYNTHESIZER_PROMPT_TEMPLATE = """
You are an expert prompt engineer. Your task is to generate a complete and detailed
Product Requirement Prompt (PRP). Your output **MUST** be a single, valid JSON
object that strictly conforms to the provided JSON schema. Do not output any text,
explanation, or markdown formatting outside of the JSON object itself.

**JSON Schema to follow:**
{json_schema}

**Assembled Context:**
{context}

Now, generate the JSON object for the PRP based on the context and schema.
"""

class SynthesizerAgent(BaseAgent):
    def __init__(self, model_name: str | None = None):
        if model_name is None:
            from ..config import get_model_name
            model_name = get_model_name("synthesizer")
        super().__init__(model_name=model_name)

    def synthesize(
        self, schema: dict, context: str, constitution: str, max_retries: int = 2
    ) -> dict:
        """Generates the final PRP JSON, validating it against the schema and retrying."""
        prompt = (
            constitution
            + "\n\n"
            + SYNTHESIZER_PROMPT_TEMPLATE.format(
                json_schema=json.dumps(schema, indent=2).replace("{", "{{").replace("}", "}}"),
                context=context,
            )
        )

        for attempt in range(max_retries):
            response = self.model.generate_content(prompt)
            cleaned_response_text = self._clean_json_response(response.text)

            try:
                generated_json = json.loads(cleaned_response_text)
                validate(instance=generated_json, schema=schema)
                print(
                    f"Synthesizer output validated successfully on attempt {attempt + 1}."
                )
                return generated_json
            except (json.JSONDecodeError, ValidationError) as e:
                print(
                    f"[WARNING] Synthesizer output validation failed on attempt "
                    f"{attempt + 1}: {e}"
                )
                # Append error to prompt for self-correction
                prompt += (
                    f"\n\nPREVIOUS ATTEMPT FAILED. DO NOT REPEAT THE MISTAKE. "
                    f"Error: {e}. Raw Response: {cleaned_response_text}. "
                    f"Please correct the JSON output to strictly conform to the schema."
                )

        raise RuntimeError(
            f"Synthesizer failed to produce a valid PRP JSON after {max_retries} attempts."
        )
