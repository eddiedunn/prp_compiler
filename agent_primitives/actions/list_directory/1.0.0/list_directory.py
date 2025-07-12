import os
from pathlib import Path

def run(directory_path: str, recursive: bool = False) -> str:
    """Lists the contents of a directory."""
    path = Path(directory_path)
    if not path.is_dir():
        return f"[ERROR] Directory not found at '{directory_path}'"
    
    output = []
    if recursive:
        for root, dirs, files in os.walk(directory_path):
            level = root.replace(directory_path, '').count(os.sep)
            indent = ' ' * 4 * level
            output.append(f"{indent}{os.path.basename(root)}/")
            sub_indent = ' ' * 4 * (level + 1)
            for f in files:
                output.append(f"{sub_indent}{f}")
    else:
        for item in path.iterdir():
            output.append(f"{'d' if item.is_dir() else '-'} {item.name}")
    
    return "\n".join(output)
