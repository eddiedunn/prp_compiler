import os
from dotenv import load_dotenv
from typing import Optional

def get_api_key() -> Optional[str]:
    """Loads the Gemini API key from a .env file or the environment.

    Returns:
        The API key as a string, or None if not found.
    """
    load_dotenv()
    return os.getenv("GEMINI_API_KEY")

