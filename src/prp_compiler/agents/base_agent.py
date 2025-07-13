import re

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - allow tests without package
    class DummyModel:
        def generate_content(self, *args, **kwargs):
            class Res:
                text = "{}"
                candidates = [type("C", (), {"content": type("P", (), {"parts": [type('FC', (), {"function_call": None})()]})()})]

            return Res()

    genai = type("genai", (), {"GenerativeModel": lambda *a, **kw: DummyModel()})


class BaseAgent:
    """Base class for all agents, handling API configuration and common utilities."""

    def __init__(self, model_name: str = "gemini-1.5-flash"):
        # Configuration is now handled in main.py
        self.model = genai.GenerativeModel(model_name)

    def _clean_json_response(self, text: str) -> str:
        """
        Cleans the raw text response from the LLM to extract a valid JSON object.
        It handles markdown fences, optional 'json' specifiers, and surrounding text.
        """
        # Match ```json, ```, or just the JSON object itself
        match = re.search(
            r"```(?:json)?\s*(\{[\s\S]*?\})\s*```|(\{[\s\S]*\})", text, re.DOTALL
        )
        if match:
            # Prioritize the content within fences if both groups are found
            return match.group(1) or match.group(2)

        # As a fallback, try to find the first and last curly braces
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return text[start:end]
        except ValueError:
            return text  # Return original text if no JSON object is found
