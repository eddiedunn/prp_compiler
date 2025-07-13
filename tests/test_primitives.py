import pytest

from src.prp_compiler.primitives import PrimitiveLoader


@pytest.fixture
def temp_primitives_dir(tmp_path):
    # Create the directory structure
    base = tmp_path / "temp_primitives"
    actions = base / "actions" / "web_search"
    v1_0_0 = actions / "1.0.0"
    v1_1_0 = actions / "1.1.0"
    v1_0_0.mkdir(parents=True)
    v1_1_0.mkdir(parents=True)
    # Write manifest.yml files
    (v1_0_0 / "manifest.yml").write_text("""
name: web_search
description: Search the web for a query.
""")
    (v1_1_0 / "manifest.yml").write_text("""
name: web_search
description: Search the web for a query (improved).
""")
    # Write dummy prompt.md
    (v1_0_0 / "prompt.md").write_text("Prompt v1.0.0")
    (v1_1_0 / "prompt.md").write_text("Prompt v1.1.0")
    return base


@pytest.fixture
def temp_primitives_dir_invalid(tmp_path):
    base = tmp_path / "temp_primitives_invalid"
    invalid = base / "actions" / "bad_action"
    version_dir = invalid / "1.0.0"
    version_dir.mkdir(parents=True)
    # add a directory that isn't a semantic version
    (invalid / "not_a_version").mkdir()
    return base


def test_primitive_loader_latest_version(temp_primitives_dir):
    loader = PrimitiveLoader(temp_primitives_dir)
    actions = loader.get_all("actions")
    assert len(actions) == 1
    action = actions[0]
    assert action["version"] == "1.1.0"
    assert action["name"] == "web_search"


def test_primitive_loader_ignores_invalid(temp_primitives_dir_invalid):
    loader = PrimitiveLoader(temp_primitives_dir_invalid)
    actions = loader.get_all("actions")
    assert actions == []
