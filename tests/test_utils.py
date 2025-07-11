from unittest.mock import patch, MagicMock
from src.prp_compiler.utils import count_tokens


@patch("src.prp_compiler.utils.genai.GenerativeModel")
def test_count_tokens(mock_generative_model):
    """Test that the token count is accurate using a mocked Gemini model."""
    # Arrange
    # Create a mock for the model instance and its methods
    mock_model_instance = MagicMock()
    mock_generative_model.return_value = mock_model_instance

    # Configure the mock to return a specific token count
    text = "hello world"
    expected_tokens = 2
    mock_model_instance.count_tokens.return_value = MagicMock(
        total_tokens=expected_tokens
    )

    # Act
    actual_tokens = count_tokens(text)

    # Assert
    assert actual_tokens == expected_tokens
    mock_generative_model.assert_called_once_with("gemini-1.5-flash")
    mock_model_instance.count_tokens.assert_called_once_with(text)

    # Test with a different text
    mock_generative_model.reset_mock()
    mock_model_instance.reset_mock()

    text_long = "This is a longer sentence for token counting."
    expected_tokens_long = 9
    mock_model_instance.count_tokens.return_value = MagicMock(
        total_tokens=expected_tokens_long
    )

    actual_tokens_long = count_tokens(text_long)

    assert actual_tokens_long == expected_tokens_long
    mock_model_instance.count_tokens.assert_called_once_with(text_long)
