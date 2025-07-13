try:
    import tiktoken
except Exception:  # pragma: no cover - allow running without tiktoken
    tiktoken = None


def count_tokens(text: str) -> int:
    """Counts tokens using the cl100k_base encoding used by modern models."""
    if not tiktoken:
        count = 0
        for word in text.split():
            count += 1
            if word and word[-1] in {".", ",", "!", "?", ";", ":"} and len(word) > 1:
                count += 1
        return count
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
    except KeyError:
        encoding = tiktoken.encoding_for_model("gpt-4")
    return len(encoding.encode(text))
