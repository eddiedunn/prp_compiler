from pathlib import Path


def run(file_path: str) -> str:
    """Reads the content of a file and returns it as a string."""
    try:
        return Path(file_path).read_text()
    except Exception as e:
        return f"[ERROR] Failed to read file {file_path}: {e}"
