"""Unit tests for cascade.cli."""

from __future__ import annotations

from typer.testing import CliRunner

from cascade.cli import app

runner = CliRunner()


def test_main_no_args_shows_help() -> None:
    """Test root command with no args shows help."""
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "Flow naturally through your build pipeline" in result.stdout


def test_help_lists_skeleton_commands() -> None:
    """Test that Day 1-2 skeleton commands are available."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "list" in result.stdout
    assert "clean" in result.stdout
    assert "graph" in result.stdout


def test_main_help() -> None:
    """Test main() with --help flag."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0


def test_main_version() -> None:
    """Test main() with --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "0.1.0" in result.stdout


def test_run_command() -> None:
    """Test run skeleton command."""
    result = runner.invoke(app, ["run", "build"])
    assert result.exit_code == 0
    assert "Running task: build" in result.stdout
