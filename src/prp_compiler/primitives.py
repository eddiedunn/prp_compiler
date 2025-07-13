from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import yaml
except Exception:  # pragma: no cover - allow running without PyYAML
    yaml = None

def _simple_yaml_load(text: str) -> Dict[str, Any]:
    """Very small YAML loader for our manifest format."""
    data: Dict[str, Any] = {}
    current_stack: list[tuple[int, Any]] = [(0, data)]

    def convert(value: str) -> Any:
        if value.startswith("[") and value.endswith("]"):
            return [v.strip().strip('"') for v in value[1:-1].split("") if v.strip()]
        if value.isdigit():
            return int(value)
        return value.strip('"')

    for line in text.splitlines():
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if stripped.startswith("- "):
            key, container = current_stack[-1]
            if not isinstance(container, list):
                container_list = []
                current_stack[-1] = (key, container_list)
                if isinstance(current_stack[-2][1], dict):
                    current_stack[-2][1][key] = container_list
            else:
                container_list = container
            container_list.append(convert(stripped[2:]))
            continue
        if ":" in stripped:
            k, v = stripped.split(":", 1)
            k = k.strip()
            v = v.strip()
            while current_stack and indent <= current_stack[-1][0]:
                current_stack.pop()
            if not current_stack:
                current_stack.append((0, data))
            parent = current_stack[-1][1]
            if v == "":
                new_obj: Dict[str, Any] | list[Any] = {}
                parent[k] = new_obj
                current_stack.append((indent, k))
                current_stack.append((indent + 2, new_obj))
            else:
                parent[k] = convert(v)
    return data
from semantic_version import Version  # type: ignore


class PrimitiveLoader:
    def __init__(self, base_path: Path):
        if not base_path.is_dir():
            raise FileNotFoundError(
                f"Primitives base path does not exist: {base_path}"
            )
        self.base_path = base_path
        self.primitives = self._load_all()

    def _load_all(self) -> Dict[str, Any]:
        """
        Walks the base path and loads the latest compatible version of each primitive.
        """
        loaded: dict[str, Any] = {}
        for primitive_type_path in self.base_path.iterdir():
            if not primitive_type_path.is_dir():
                continue
            type_name = primitive_type_path.name
            loaded[type_name] = {}
            for primitive_name_path in primitive_type_path.iterdir():
                if not primitive_name_path.is_dir():
                    continue
                name = primitive_name_path.name
                latest_version, manifest = self._find_latest_version(
                    primitive_name_path
                )
                if latest_version and manifest:
                    loaded[type_name][name] = manifest
        return loaded

    def _find_latest_version(self, path: Path) -> Tuple[Version, Dict[str, Any]]:
        """Finds the latest semantic version in a directory and returns its manifest."""
        latest_version = None
        latest_manifest = None
        for version_path in path.iterdir():
            if not version_path.is_dir():
                continue
            try:
                current_version = Version(version_path.name)
                if latest_version is None or current_version > latest_version:
                    manifest_path = version_path / "manifest.yml"
                    if manifest_path.is_file():
                        with open(manifest_path, "r") as f:
                            text = f.read()
                            if yaml:
                                manifest = yaml.safe_load(text)
                            else:
                                manifest = _simple_yaml_load(text)
                            manifest["version"] = str(current_version)
                            manifest["base_path"] = str(version_path.resolve())
                            latest_version = current_version
                            latest_manifest = manifest
            except ValueError:
                continue
        if latest_version is not None and latest_manifest is not None:
            return latest_version, latest_manifest
        return Version("0.0.0"), {}

    def get_all(self, primitive_type: str) -> List[Dict[str, Any]]:
        """Returns a list of all primitives of a given type."""
        return list(self.primitives.get(primitive_type, {}).values())

    def get_primitive_content(self, primitive_type: str, name: str) -> str:
        """Gets the content of a primitive's entrypoint file."""
        primitive = self.primitives.get(primitive_type, {}).get(name)
        if not primitive:
            raise ValueError(
                f"Primitive '{name}' of type '{primitive_type}' not found."
            )
        entrypoint_path = Path(primitive["base_path"]) / primitive["entrypoint"]
        if not entrypoint_path.is_file():
            raise FileNotFoundError(
                f"Entrypoint file not found for primitive '{name}': {entrypoint_path}"
            )
        return entrypoint_path.read_text()

    def get_action_entrypoint(self, name: str) -> Tuple[str, str]:
        action_manifest = self.primitives.get("actions", {}).get(name)
        if not action_manifest or "entrypoint" not in action_manifest:
            raise ValueError(f"Action '{name}' or its entrypoint not found.")
        module_str, function_str = action_manifest["entrypoint"].split(":")
        return module_str, function_str
