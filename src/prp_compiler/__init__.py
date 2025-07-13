"""Core package for the PRP Compiler."""

from importlib import metadata


def _get_version() -> str:
    """Return the installed package version or a fallback."""
    try:
        return metadata.version("prp-compiler")
    except metadata.PackageNotFoundError:
        # Package is not installed; use the version from pyproject for sources
        return "0.1.0"


__version__ = _get_version()

__all__ = ["__version__"]

