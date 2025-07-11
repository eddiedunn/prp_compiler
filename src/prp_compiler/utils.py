import tiktoken

def count_tokens(text: str) -> int:
    """Counts tokens using the cl100k_base encoding used by modern models."""
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except KeyError:
        # Fallback for minimal installations, though cl100k_base should be standard.
        encoding = tiktoken.encoding_for_model("gpt-4")
    return len(encoding.encode(text))
