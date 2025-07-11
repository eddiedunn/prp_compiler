import os
from dotenv import load_dotenv
import google.generativeai as genai

def configure_gemini():
    """Loads API key from .env and configures the Gemini client."""
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file or environment variables.")
    genai.configure(api_key=api_key)
    print("Gemini API configured successfully.")
