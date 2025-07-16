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
# Allowed shell commands for dynamic content resolution.
ALLOWED_SHELL_COMMANDS = ["echo", "ls"]


def get_model_name(role: str) -> str:
    """
    Returns the Gemini model name for a specific role.
    Loads from environment variables or .env file, with sensible defaults.
    
    Args:
        role: The role of the model (e.g., "planner", "synthesizer", "embedding").
    """
    # Map roles to environment variables and default models
    model_map = {
        "planner": ("PLANNER_MODEL", "models/gemini-1.5-pro-latest"),
        "synthesizer": ("SYNTHESIZER_MODEL", "models/gemini-1.5-flash-latest"),
        "summarizer": ("SUMMARIZER_MODEL", "models/gemini-1.5-flash-latest"),
        "embedding": ("EMBEDDING_MODEL", "models/embedding-001"),
    }
    
    env_var_name, default_model = model_map.get(role, (None, None))
    
    if not env_var_name:
        raise ValueError(f"Unknown model role: {role}")

    # Try getting from os.environ first
    model_name = os.environ.get(env_var_name)
    
    # If not found, try loading from .env
    model_name = os.environ.get("PRP_MODEL_NAME")
    if not model_name:
        try:
            load_dotenv(PROJECT_ROOT / ".env")
            model_name = os.environ.get("PRP_MODEL_NAME")
        except ImportError:
            pass
    return model_name or "models/gemini-1.5-pro-latest"


def configure_gemini():
    """Loads the Gemini API key and configures the genai library."""
    if not genai:
        return
    
    # First try to get API key from environment variable
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # If not found, try loading from .env file
    if not api_key:
        try:
            from dotenv import load_dotenv
            load_dotenv(PROJECT_ROOT / ".env")
            api_key = os.environ.get("GEMINI_API_KEY")
        except ImportError:
            pass
    
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY not found. Please set it in your environment variables or .env file.\n"
            "Example: export GEMINI_API_KEY='your-api-key-here'"
        )
    
    # Configure the genai library with just the API key
    genai.configure(api_key=api_key)
