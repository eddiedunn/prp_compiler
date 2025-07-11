from src.prp_compiler.manifests import generate_manifest, save_manifests, load_manifests
from src.prp_compiler.models import ManifestItem


def test_generate_manifest(temp_agent_dir):
    """Test that the manifest is generated correctly using the shared fixture."""
    # Generate manifest for the 'tools' subdirectory created by the fixture
    manifest = generate_manifest(temp_agent_dir["tools"])

    # The fixture creates one valid tool file
    assert len(manifest) == 1, "Should find 1 valid manifest item in the tools directory"

    item = manifest[0]
    assert item.name == "test_tool"
    assert item.description == "A test tool."
    assert item.file_path == str((temp_agent_dir["tools"] / "test_tool.md").resolve())


def test_save_and_load_manifests(tmp_path):
    """Test saving and then loading the manifests from a directory."""
    # 1. Create dummy manifest data
    tools_manifest = [ManifestItem(name="tool1", description="desc1", file_path="path1")]
    knowledge_manifest = [ManifestItem(name="knowledge1", description="desc2", file_path="path2")]
    schemas_manifest = [ManifestItem(name="schema1", description="desc3", file_path="path3")]

    manifest_dir = tmp_path / "manifests"

    # 2. Save the manifests
    save_manifests(tools_manifest, knowledge_manifest, schemas_manifest, manifest_dir)

    # 3. Assert that the files were created
    assert (manifest_dir / "tools_manifest.json").exists()
    assert (manifest_dir / "knowledge_manifest.json").exists()
    assert (manifest_dir / "schemas_manifest.json").exists()

    # 4. Load the manifests back
    loaded_tools, loaded_knowledge, loaded_schemas = load_manifests(manifest_dir)

    # 5. Assert that the loaded data matches the original data
    assert loaded_tools == tools_manifest
    assert loaded_knowledge == knowledge_manifest
    assert loaded_schemas == schemas_manifest
