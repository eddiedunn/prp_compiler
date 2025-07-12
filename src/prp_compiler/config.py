import os
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

# Define the project root as the grandparent of this file's directory.
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Define default paths relative to the project root.
DEFAULT_TOOLS_PATH = PROJECT_ROOT / "agent_capabilities/tools"
DEFAULT_KNOWLEDGE_PATH = PROJECT_ROOT / "agent_capabilities/knowledge"
DEFAULT_SCHEMAS_PATH = PROJECT_ROOT / "agent_capabilities/schemas"
DEFAULT_MANIFEST_PATH = PROJECT_ROOT / "manifests/"

# Allowlist for shell commands to prevent arbitrary code execution.
ALLOWED_SHELL_COMMANDS = ["git", "ls", "cat", "tree", "echo"]


def configure_gemini():
    """Loads the Gemini API key and configures the genai library."""
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
