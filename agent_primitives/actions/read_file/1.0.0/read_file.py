from pathlib import Path

def run(file_path: str) -> str:
    """Reads and returns the content of a file."""
    try:
        return Path(file_path).read_text()
    except FileNotFoundError:
        return f"[ERROR] File not found at '{file_path}'"
    except Exception as e:
        return f"[ERROR] Could not read file at '{file_path}': {e}"
