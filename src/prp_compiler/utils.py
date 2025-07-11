import tiktoken

def get_tokenizer(model_name: str = "cl100k_base"):
    """Returns a tiktoken tokenizer."""
    return tiktoken.get_encoding(model_name)

def count_tokens(text: str, model_name: str = "cl100k_base") -> int:
    """Counts the number of tokens in a string."""
    encoding = get_tokenizer(model_name)
    return len(encoding.encode(text))
