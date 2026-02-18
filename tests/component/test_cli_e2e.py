"""Component/integration tests for cscd CLI."""

from __future__ import annotations

import subprocess
import sys

import pytest


@pytest.mark.component
def test_cli_entrypoint() -> None:
    """Test CLI entry point via console script."""
    result = subprocess.run(
        ["cscd", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "run" in result.stdout


@pytest.mark.component
def test_cli_module_invocation() -> None:
    """Test CLI via python -m invocation."""
    result = subprocess.run(
        [sys.executable, "-m", "cscd", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout
    assert "graph" in result.stdout


@pytest.mark.component
def test_cli_version() -> None:
    """Test CLI --version flag."""
    result = subprocess.run(
        ["cscd", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
