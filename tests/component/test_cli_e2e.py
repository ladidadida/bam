"""Component/integration tests for bam CLI."""

from __future__ import annotations

import re
import subprocess
import sys

import pytest


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-9;]*[mK]", "", text)


@pytest.mark.component
def test_cli_entrypoint() -> None:
    """Test CLI entry point via console script."""
    result = subprocess.run(
        ["bam", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    stdout = _strip_ansi(result.stdout)
    assert "Usage:" in stdout
    assert "--list" in stdout


@pytest.mark.component
def test_cli_module_invocation() -> None:
    """Test CLI via python -m invocation."""
    result = subprocess.run(
        [sys.executable, "-m", "bam_tool", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    stdout = _strip_ansi(result.stdout)
    assert "Usage:" in stdout
    assert "--graph" in stdout


@pytest.mark.component
def test_cli_version() -> None:
    """Test CLI --version flag."""
    result = subprocess.run(
        ["bam", "--version"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
