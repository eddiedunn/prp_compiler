import os
from pathlib import Path

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None
from dotenv import load_dotenv

# Define the project root as the grandparent of this file's directory.
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Define default paths relative to the project root.
DEFAULT_TOOLS_PATH = PROJECT_ROOT / "agent_primitives/actions"
DEFAULT_KNOWLEDGE_PATH = PROJECT_ROOT / "agent_primitives/knowledge"
DEFAULT_SCHEMAS_PATH = PROJECT_ROOT / "agent_primitives/schemas"
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "manifests/"



def configure_gemini():
    """Loads the Gemini API key and configures the genai library."""
    if not genai:
        return
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            (
                "GEMINI_API_KEY not found. Please set it in your .env file or "
                "environment variables."
            )
        )
    genai.configure(api_key=api_key)
