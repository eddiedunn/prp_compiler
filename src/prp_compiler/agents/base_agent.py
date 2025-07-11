import google.generativeai as genai
import re


class BaseAgent:
    """Base class for all agents, handling API configuration and common utilities."""

    def __init__(self, model_name: str = "gemini-1.5-flash"):
        # Configuration is now handled in main.py
        self.model = genai.GenerativeModel(model_name)

    def _clean_json_response(self, text: str) -> str:
        """
        Cleans the raw text response from the LLM to extract a valid JSON object.
        It removes markdown code fences (```json ... ```) and leading/trailing whitespace.
        """
        # Find the start and end of the JSON block
        match = re.search(r"```(json)?(.*)```", text, re.DOTALL)
        if match:
            # Extract the content within the fences
            json_str = match.group(2).strip()
        else:
            # If no fences, assume the whole string is the JSON content
            json_str = text.strip()

        return json_str
