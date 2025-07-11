import google.generativeai as genai


def count_tokens(text: str, model_name: str = "gemini-1.5-flash") -> int:
    """Counts tokens using the Google Gemini tokenizer."""
    # Assumes genai is configured. You might need to pass the model object.
    model = genai.GenerativeModel(model_name)
    return model.count_tokens(text).total_tokens
