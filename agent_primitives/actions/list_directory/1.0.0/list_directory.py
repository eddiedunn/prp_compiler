import os


def run(directory_path: str = '.') -> str:
    """Lists the contents of a directory and returns it as a string."""
    try:
        entries = os.listdir(directory_path)
        return "\n".join(entries)
    except Exception as e:
        return f"[ERROR] Failed to list directory {directory_path}: {e}"
