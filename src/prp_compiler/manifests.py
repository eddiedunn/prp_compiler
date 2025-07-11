import json
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .models import ManifestItem

# This regex is more robust as it doesn't anchor to the absolute start of the string.
FRONTMATTER_RE = re.compile(r"---\s*\n(.*?)\n---\s*\n", re.S)


def _parse_frontmatter(file_path: Path) -> Dict[str, Any]:
    """Parses the YAML frontmatter from a file using a robust regex."""
    try:
        text = file_path.read_text()
        # Use re.search instead of re.match
        match = FRONTMATTER_RE.search(text)
        if not match:
            return {}
        frontmatter_str = match.group(1)
        frontmatter = yaml.safe_load(frontmatter_str)
        return frontmatter if isinstance(frontmatter, dict) else {}
    except (IOError, yaml.YAMLError):
        return {}


def generate_manifest(capability_path: Path) -> List[ManifestItem]:
    """Generates a manifest by scanning all files in a directory."""
    manifest = []
    for file_path in capability_path.rglob("*.*"):
        if file_path.is_file():
            frontmatter = _parse_frontmatter(file_path)
            if "name" in frontmatter and "description" in frontmatter:
                item = ManifestItem(
                    name=frontmatter["name"],
                    description=frontmatter["description"],
                    arguments=frontmatter.get("arguments"),
                    keywords=frontmatter.get("keywords", []),
                    file_path=str(file_path.resolve()),
                )
                manifest.append(item)
    return manifest


def save_manifests(
    tools: List[ManifestItem],
    knowledge: List[ManifestItem],
    schemas: List[ManifestItem],
    output_dir: Path,
):
    """Saves each manifest to a separate JSON file in the specified directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_files = {
        "tools_manifest.json": [item.model_dump() for item in tools],
        "knowledge_manifest.json": [item.model_dump() for item in knowledge],
        "schemas_manifest.json": [item.model_dump() for item in schemas],
    }

    for filename, data in manifest_files.items():
        with open(output_dir / filename, "w") as f:
            json.dump(data, f, indent=2)

def load_manifests(
    manifest_dir: Path,
) -> Tuple[List[ManifestItem], List[ManifestItem], List[ManifestItem]]:
    """Loads all manifests from their separate JSON files."""
    try:
        with open(manifest_dir / "tools_manifest.json", "r") as f:
            tools_data = json.load(f)
            tools = [ManifestItem(**item) for item in tools_data]

        with open(manifest_dir / "knowledge_manifest.json", "r") as f:
            knowledge_data = json.load(f)
            knowledge = [ManifestItem(**item) for item in knowledge_data]

        with open(manifest_dir / "schemas_manifest.json", "r") as f:
            schemas_data = json.load(f)
            schemas = [ManifestItem(**item) for item in schemas_data]

        return tools, knowledge, schemas
    except (FileNotFoundError, json.JSONDecodeError) as e:
        # If any file is missing or corrupt, we'll need to regenerate.
        raise IOError(f"Could not load manifests from {manifest_dir}: {e}")



