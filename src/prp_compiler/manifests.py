import json
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .models import ManifestItem

# Regex to find YAML frontmatter at the start of a file
FRONTMATTER_RE = re.compile(r"^---\s*$(.*?)^---\s*$", re.S | re.M)


def _parse_frontmatter(file_path: Path) -> Dict[str, Any]:
    """Parses the YAML frontmatter from a file using a robust regex."""
    try:
        text = file_path.read_text()
        match = FRONTMATTER_RE.match(text)
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


def save_manifest(
    tools: List[ManifestItem],
    knowledge: List[ManifestItem],
    schemas: List[ManifestItem],
    output_path: Path,
):
    """Saves all manifests to a single structured JSON file."""
    manifest_data = {
        "tools": [item.model_dump() for item in tools],
        "knowledge": [item.model_dump() for item in knowledge],
        "schemas": [item.model_dump() for item in schemas],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(manifest_data, f, indent=2)


def generate_and_save_all_manifests(
    tools_path: Path, knowledge_path: Path, schemas_path: Path, output_path: Path
) -> Tuple[List[ManifestItem], List[ManifestItem], List[ManifestItem]]:
    """Generates and saves all manifests, returning the generated lists."""
    print(f"Generating manifests from: {tools_path}, {knowledge_path}, {schemas_path}")
    tools_manifest = generate_manifest(tools_path)
    knowledge_manifest = generate_manifest(knowledge_path)
    schemas_manifest = generate_manifest(schemas_path)
    save_manifest(tools_manifest, knowledge_manifest, schemas_manifest, output_path)
    print(f"Manifests successfully generated and saved to {output_path}")
    return tools_manifest, knowledge_manifest, schemas_manifest
