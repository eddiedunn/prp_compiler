import json
from jsonschema import validate, ValidationError
from .base_agent import BaseAgent

SYNTHESIZER_PROMPT_TEMPLATE = """
You are an expert prompt engineer. Your task is to generate a complete and detailed Product Requirement Prompt (PRP) as a single, valid JSON object that strictly conforms to the provided JSON schema. Do not output any text or explanation outside of the JSON object itself.

**JSON Schema to follow:**
{json_schema}

**Assembled Context:**
{context}

Now, generate the JSON object for the PRP.
"""

class SynthesizerAgent(BaseAgent):
    def synthesize(self, schema: dict, context: str, constitution: str, max_retries: int = 2) -> dict:
        """Generates the final PRP JSON, validating it against the schema and retrying if necessary."""
        prompt = constitution + "\n\n" + SYNTHESIZER_PROMPT_TEMPLATE.format(json_schema=json.dumps(schema, indent=2), context=context)
        for attempt in range(max_retries):
            response = self.model.generate_content(prompt)
            cleaned_response_text = self._clean_json_response(response.text)
            try:
                generated_json = json.loads(cleaned_response_text)
                validate(instance=generated_json, schema=schema)
                print(f"Synthesizer output validated successfully on attempt {attempt + 1}.")
                return generated_json
            except (json.JSONDecodeError, ValidationError) as e:
                print(f"[Warning] Synthesizer output validation failed on attempt {attempt + 1}: {e}")
                prompt += f"\n\nPREVIOUS ATTEMPT FAILED. DO NOT REPEAT THE MISTAKE. Error: {e}. Raw Response: {cleaned_response_text}. Please correct the JSON output to strictly conform to the schema."
        raise RuntimeError("Synthesizer failed to produce a valid PRP JSON after multiple attempts.")

    def _clean_json_response(self, text: str) -> str:
        """Attempts to extract a JSON object from the model's response text."""
        # Remove leading/trailing whitespace and markdown fencing if present
        text = text.strip()
        if text.startswith('```json'):
            text = text[len('```json'):]
        if text.startswith('```'):
            text = text[len('```'):]
        if text.endswith('```'):
            text = text[:-3]
        # Try to find the first and last curly braces
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return text[start:end+1]
        return text
