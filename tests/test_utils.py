from src.prp_compiler.utils import count_tokens

def test_count_tokens_local():
    """Test that the local token count is accurate using tiktoken."""
    # Arrange
    text = "hello world"
    # Using cl100k_base encoding, "hello" is 1 token and " world" is 1 token.
    expected_tokens = 2

    # Act
    actual_tokens = count_tokens(text)

    # Assert
    assert actual_tokens == expected_tokens

    # Test with a different text
    text_long = "This is a longer sentence for token counting."
    # Based on the cl100k_base tokenizer used by GPT-4 and Gemini.
    expected_tokens_long = 9

    actual_tokens_long = count_tokens(text_long)

    assert actual_tokens_long == expected_tokens_long

    # Test with an empty string
    assert count_tokens("") == 0
