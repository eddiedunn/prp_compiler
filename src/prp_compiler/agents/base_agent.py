import google.generativeai as genai
import re
from ..config import get_api_key

class BaseAgent:
    """Base class for all agents, handling API configuration and common utilities."""

    def __init__(self, model_name: str = "gemini-1.5-flash"):
        api_key = get_api_key()
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in .env file or environment variables.")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def _clean_json_response(self, text: str) -> str:
        """
        Cleans the raw text response from the LLM to extract a valid JSON object.
        It removes markdown code fences (```json ... ```) and leading/trailing whitespace.
        """
        # Find the start and end of the JSON block
        match = re.search(r'```(json)?(.*)```', text, re.DOTALL)
        if match:
            # Extract the content within the fences
            json_str = match.group(2).strip()
        else:
            # If no fences, assume the whole string is the JSON content
            json_str = text.strip()
        
        return json_str
