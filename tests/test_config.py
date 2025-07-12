from unittest.mock import patch

import pytest

from src.prp_compiler.config import configure_gemini


@patch("src.prp_compiler.config.os.getenv")
@patch("src.prp_compiler.config.genai.configure")
@patch("src.prp_compiler.config.load_dotenv")
def test_configure_gemini_success(mock_load_dotenv, mock_genai_configure, mock_getenv):
    """Tests that configure_gemini successfully configures the API key when it exists."""
    # Arrange: Mock the environment variable to return a fake API key
    mock_getenv.return_value = "fake_api_key"

    # Act
    configure_gemini()

    # Assert
    mock_load_dotenv.assert_called_once()
    mock_getenv.assert_called_once_with("GEMINI_API_KEY")
    mock_genai_configure.assert_called_once_with(api_key="fake_api_key")


@patch("src.prp_compiler.config.os.getenv")
@patch("src.prp_compiler.config.load_dotenv")
def test_configure_gemini_failure_key_not_found(mock_load_dotenv, mock_getenv):
    """Tests that configure_gemini raises a ValueError if the API key is not found."""
    # Arrange: Mock the environment variable to return None
    mock_getenv.return_value = None

    # Act & Assert
    with pytest.raises(ValueError, match="GEMINI_API_KEY not found"):
        configure_gemini()
    mock_load_dotenv.assert_called_once()
    mock_getenv.assert_called_once_with("GEMINI_API_KEY")
