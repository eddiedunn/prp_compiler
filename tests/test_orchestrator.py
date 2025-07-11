import pytest
from unittest.mock import patch, MagicMock
import subprocess
from src.prp_compiler.orchestrator import Orchestrator

@pytest.fixture
def orchestrator():
    """Provides an instance of the Orchestrator for testing."""
    return Orchestrator()

@patch('subprocess.run')
@patch('pathlib.Path.read_text')
def test_resolve_dynamic_content_success(mock_read_text, mock_subprocess_run, orchestrator):
    """Test successful resolution of both command and file content."""
    # Mock the subprocess call
    mock_subprocess_run.return_value = MagicMock(
        stdout='hello from command',
        stderr='',
        returncode=0
    )
    
    # Mock the file read
    mock_read_text.return_value = 'hello from file'

    raw_context = (
        'This is a test.\n'
        '!echo "hello from command"\n'
        'And this is a file.\n'
        '@some/file.txt'
    )

    resolved_context = orchestrator._resolve_dynamic_content(raw_context)

    # The regex processes line by line, so we check the replacements
    assert 'hello from command' in resolved_context
    assert 'hello from file' in resolved_context
    assert 'This is a test.' in resolved_context # Ensures other lines are preserved

    # Verify that the mocks were called correctly
    mock_subprocess_run.assert_called_once_with(
        'echo "hello from command"',
        shell=True,
        capture_output=True,
        text=True,
        check=True
    )
    mock_read_text.assert_called_once()

@patch('subprocess.run')
def test_resolve_dynamic_content_command_error(mock_subprocess_run, orchestrator):
    """Test handling of a failed subprocess command."""
    # Configure the mock to raise an error
    mock_subprocess_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd='bad-command', stderr='Error'
    )

    raw_context = '!bad-command'
    resolved_context = orchestrator._resolve_dynamic_content(raw_context)

    assert "[ERROR: Command 'bad-command' failed" in resolved_context

@patch('pathlib.Path.read_text')
def test_resolve_dynamic_content_file_not_found(mock_read_text, orchestrator):
    """Test handling of a non-existent file."""
    # Configure the mock to raise an error
    mock_read_text.side_effect = FileNotFoundError

    raw_context = '@/non/existent/file.txt'
    resolved_context = orchestrator._resolve_dynamic_content(raw_context)

    assert "[ERROR: File not found at '/non/existent/file.txt']" in resolved_context
