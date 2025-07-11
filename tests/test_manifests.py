import pytest
from pathlib import Path
import tempfile
import shutil
from src.prp_compiler.manifests import generate_manifest, save_manifest
from src.prp_compiler.models import ManifestItem

@pytest.fixture
def temp_capability_dir():
    """Create a temporary directory with dummy capability files for testing."""
    temp_dir = Path(tempfile.mkdtemp())

    # Valid capability file
    (temp_dir / "tool1.md").write_text(
        """---
name: example-tool
description: This is a test tool.
arguments: The file to process.
keywords: ["test", "example"]
---

# Example Tool
This is the body of the tool file.
        """
    )

    # Another valid capability file
    (temp_dir / "tool2.txt").write_text(
        """---
name: another-tool
description: Another test tool.
---

Body of another tool.
        """
    )

    # File with invalid frontmatter (bad YAML)
    (temp_dir / "bad_tool.md").write_text(
        """---
name: bad-tool
description: this is not valid yaml:
---

This file will be ignored.
        """
    )

    # File without frontmatter
    (temp_dir / "no_frontmatter.txt").write_text("Just a regular file.")

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)

def test_generate_manifest(temp_capability_dir):
    """Test that the manifest is generated correctly."""
    # The function now expects to be called on a specific subdirectory, not the root.
    manifest = generate_manifest(temp_capability_dir)

    assert len(manifest) == 2, "Should find 2 valid manifest items"

    # Create a dictionary for easy lookup
    manifest_map = {item.name: item for item in manifest}

    # Assertions for 'example-tool'
    assert 'example-tool' in manifest_map
    example_tool = manifest_map['example-tool']
    assert example_tool.description == "This is a test tool."
    assert example_tool.arguments == "The file to process."
    assert example_tool.keywords == ["test", "example"]
    assert example_tool.file_path == str((temp_capability_dir / "tool1.md").resolve())

    # Assertions for 'another-tool'
    assert 'another-tool' in manifest_map
    another_tool = manifest_map['another-tool']
    assert another_tool.description == "Another test tool."
    assert another_tool.arguments is None
    assert another_tool.keywords == []
    assert another_tool.file_path == str((temp_capability_dir / "tool2.txt").resolve())

def test_save_manifest(temp_capability_dir):
    """Test saving the manifest to a file."""
    # Create dummy manifests for testing
    tools_manifest = [ManifestItem(name='tool1', description='desc1', file_path='path1')]
    knowledge_manifest = [ManifestItem(name='knowledge1', description='desc2', file_path='path2')]
    schemas_manifest = [ManifestItem(name='schema1', description='desc3', file_path='path3')]

    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".json") as tmp_file:
        output_path = Path(tmp_file.name)

    save_manifest(tools_manifest, knowledge_manifest, schemas_manifest, output_path)

    assert output_path.exists()
    
    import json
    with open(output_path, 'r') as f:
        loaded_data = json.load(f)
    
    assert len(loaded_data) == 3
    assert 'tools' in loaded_data
    assert 'knowledge' in loaded_data
    assert 'schemas' in loaded_data
    # Clean up the created file
    output_path.unlink()
