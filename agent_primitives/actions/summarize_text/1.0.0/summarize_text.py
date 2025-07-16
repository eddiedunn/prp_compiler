import google.generativeai as genai
from prp_compiler.config import configure_gemini, get_model_name

def run(text: str) -> str:
    """Summarize the given text using the configured summarizer Gemini model."""
    try:
        configure_gemini()
    except Exception as e:
        return f"[ERROR] Failed to configure Gemini: {e}"

    model_name = get_model_name("summarizer")
    try:
        model = genai.GenerativeModel(model_name)
        prompt = f"Summarize the following text in a concise paragraph:\n\n{text}"
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"[ERROR] Gemini summarization failed for model {model_name}: {e}"
