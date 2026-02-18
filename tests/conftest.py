"""Shared pytest fixtures for cscd tests."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def sample_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace for CLI and config tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace
