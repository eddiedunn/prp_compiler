try:
    import tiktoken
except Exception:  # pragma: no cover - allow running without tiktoken
    tiktoken = None


def count_tokens(text: str) -> int:
    """Counts tokens using the cl100k_base encoding used by modern models."""
    if not tiktoken:
        return len(text.split())
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except KeyError:
        encoding = tiktoken.encoding_for_model("gpt-4")
    return len(encoding.encode(text))
