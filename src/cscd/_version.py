"""Version information for cscd.

This file uses importlib.metadata to get the version dynamically:
- When installed: Uses version from package metadata (set by hatch-vcs)
- When running from source: Falls back to development version
"""

from __future__ import annotations

__all__ = ["__version__"]


def _get_version() -> str:
    """Get version from package metadata or fallback."""
    try:
        from importlib.metadata import version

        return version("cscd")
    except Exception:
        # Fallback for development (not installed)
        return "0.0.0.dev0"


__version__ = _get_version()
