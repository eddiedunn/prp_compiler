import tiktoken

def count_tokens(text: str, model: str = "gpt-4") -> int:
    """Counts tokens locally using tiktoken for a given model."""
    try:
        # cl100k_base is the encoding used by GPT-4 and Gemini models
        encoding = tiktoken.get_encoding("cl100k_base")
    except Exception:
        encoding = tiktoken.encoding_for_model(model)
    return len(encoding.encode(text))
