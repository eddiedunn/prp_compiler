import json
import re
import yaml
from pathlib import Path
from typing import List, Dict, Any
from .models import ManifestItem

# Regex to find YAML frontmatter at the start of a file
FRONTMATTER_RE = re.compile(r'^---\s*$(.*?)^---\s*$', re.S | re.M)

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
    for file_path in capability_path.rglob('*.*'):
        if file_path.is_file():
            frontmatter = _parse_frontmatter(file_path)
            if 'name' in frontmatter and 'description' in frontmatter:
                item = ManifestItem(
                    name=frontmatter['name'],
                    description=frontmatter['description'],
                    arguments=frontmatter.get('arguments'),
                    keywords=frontmatter.get('keywords', []),
                    file_path=str(file_path.resolve()),
                )
                manifest.append(item)
    return manifest

def save_manifest(tools_manifest: List[ManifestItem], knowledge_manifest: List[ManifestItem], schemas_manifest: List[ManifestItem], output_path: Path):
    """Saves all manifests to a single structured JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest_data = {
        "tools": [item.model_dump() for item in tools_manifest],
        "knowledge": [item.model_dump() for item in knowledge_manifest],
        "schemas": [item.model_dump() for item in schemas_manifest],
    }

    with open(output_path, 'w') as f:
        json.dump(manifest_data, f, indent=2)
