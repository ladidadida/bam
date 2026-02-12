"""Component/integration tests for cascade CLI."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.component
def test_cli_entrypoint() -> None:
    """Test CLI entry point via console script."""
    result = subprocess.run(
        ["cascade", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "**Cascade** is a content-addressed workflow orchestration tool that brings the power of content-addressable storage (CAS) to everyday development workflows" in result.stdout or "usage:" in result.stdout


@pytest.mark.component
def test_cli_module_invocation() -> None:
    """Test CLI via python -m invocation."""
    result = subprocess.run(
        [sys.executable, "-m", "cascade", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "**Cascade** is a content-addressed workflow orchestration tool that brings the power of content-addressable storage (CAS) to everyday development workflows" in result.stdout or "usage:" in result.stdout


@pytest.mark.component
def test_cli_version() -> None:
    """Test CLI --version flag."""
    result = subprocess.run(
        ["cascade", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "0.1.0" in result.stdout
