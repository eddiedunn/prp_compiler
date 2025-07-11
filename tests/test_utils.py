from src.prp_compiler.utils import get_tokenizer, count_tokens

def test_get_tokenizer():
    """Test that a valid tokenizer is returned."""
    tokenizer = get_tokenizer()
    assert tokenizer is not None
    # Test with a specific model if needed
    tokenizer_gpt2 = get_tokenizer("gpt2")
    assert tokenizer_gpt2 is not None

def test_count_tokens():
    """Test that the token count is accurate."""
    text = "hello world"
    # Using cl100k_base, "hello world" is 2 tokens
    assert count_tokens(text) == 2

    text_long = "tiktoken is a fast BPE tokenizer from OpenAI."
    # This should be 10 tokens
    assert count_tokens(text_long) == 13

    # Test with a different model's tokenizer
    text_gpt2 = "hello world"
    assert count_tokens(text_gpt2, model_name="gpt2") == 2
