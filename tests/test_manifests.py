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
    manifest = generate_manifest(temp_capability_dir)

    assert len(manifest) == 2
    assert isinstance(manifest[0], ManifestItem)
    assert isinstance(manifest[1], ManifestItem)

    # Sort by name to ensure consistent order for assertions
    manifest.sort(key=lambda x: x.name)

    assert manifest[0].name == "another-tool"
    assert manifest[0].description == "Another test tool."
    assert manifest[0].arguments is None
    assert manifest[0].keywords == []
    assert manifest[0].file_path == str((temp_capability_dir / "tool2.txt").resolve())

    assert manifest[1].name == "example-tool"
    assert manifest[1].description == "This is a test tool."
    assert manifest[1].arguments == "The file to process."
    assert manifest[1].keywords == ["test", "example"]
    assert manifest[1].file_path == str((temp_capability_dir / "tool1.md").resolve())

def test_save_manifest(temp_capability_dir):
    """Test saving the manifest to a file."""
    manifest_data = generate_manifest(temp_capability_dir)
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix=".json") as tmp_file:
        output_path = Path(tmp_file.name)

    save_manifest(manifest_data, output_path)

    assert output_path.exists()
    
    import json
    with open(output_path, 'r') as f:
        loaded_data = json.load(f)
    
    assert len(loaded_data) == 2
    # Clean up the created file
    output_path.unlink()
