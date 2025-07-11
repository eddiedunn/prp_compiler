import os
from dotenv import load_dotenv
import google.generativeai as genai
from pathlib import Path

# Define default paths. These assume a 'agent_capabilities' directory
# in the current working directory where the command is run.
DEFAULT_TOOLS_PATH = Path("./agent_capabilities/tools")
DEFAULT_KNOWLEDGE_PATH = Path("./agent_capabilities/knowledge")
DEFAULT_SCHEMAS_PATH = Path("./agent_capabilities/schemas")
DEFAULT_MANIFEST_PATH = Path("./component_manifest.json")


def configure_gemini():
    """Loads the Gemini API key and configures the genai library."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Please set it in your .env file or environment variables."
        )
    genai.configure(api_key=api_key)
