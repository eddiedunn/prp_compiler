import google.generativeai as genai
from prp_compiler.config import configure_gemini


def run(text: str, model_name: str = "gemini-pro") -> str:
    """Summarize the given text using Gemini."""
    try:
        configure_gemini()
    except Exception as e:
        return f"[ERROR] Failed to configure Gemini: {e}"

    model = genai.GenerativeModel(model_name)
    prompt = f"Summarize the following text in a concise paragraph:\n\n{text}"
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[ERROR] Gemini summarization failed: {e}"
