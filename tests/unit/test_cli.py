"""Unit tests for cascade.cli."""

from __future__ import annotations

from typer.testing import CliRunner

from cascade.cli import app

runner = CliRunner(mix_stderr=False)


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
    assert "validate" in result.stdout


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
    """Test run command executes tasks."""
    with runner.isolated_filesystem():
        with open("cascade.yaml", "w", encoding="utf-8") as file:
            file.write(
                "version: 1\n\n"
                "tasks:\n"
                "  build:\n"
                "    command: echo 'Building project'\n"
            )

        result = runner.invoke(app, ["run", "build"])

    assert result.exit_code == 0
    assert "Building project" in result.stdout or "Successfully executed" in result.stdout


def test_run_command_with_failing_task() -> None:
    """Test run command stops on task failure."""
    with runner.isolated_filesystem():
        with open("cascade.yaml", "w", encoding="utf-8") as file:
            file.write(
                "version: 1\n\n"
                "tasks:\n"
                "  fail:\n"
                "    command: exit 1\n"
            )

        result = runner.invoke(app, ["run", "fail"])

    assert result.exit_code == 1
    assert "Execution stopped" in result.stdout or "failed" in result.stdout


def test_run_dry_run_shows_execution_plan() -> None:
    """Test --dry-run prints dependency-respecting plan."""
    with runner.isolated_filesystem():
        with open("cascade.yaml", "w", encoding="utf-8") as file:
            file.write(
                "version: 1\n\n"
                "tasks:\n"
                "  lint:\n"
                "    command: echo lint\n"
                "  build:\n"
                "    command: echo build\n"
                "    depends_on:\n"
                "      - lint\n"
            )

        result = runner.invoke(app, ["run", "build", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry-run execution order:" in result.stdout
    assert "1. lint" in result.stdout
    assert "2. build" in result.stdout


def test_graph_command_ascii_output() -> None:
    """Test graph command default ASCII output."""
    with runner.isolated_filesystem():
        with open("cascade.yaml", "w", encoding="utf-8") as file:
            file.write(
                "version: 1\n\n"
                "tasks:\n"
                "  lint:\n"
                "    command: echo lint\n"
                "  build:\n"
                "    command: echo build\n"
                "    depends_on:\n"
                "      - lint\n"
            )

        result = runner.invoke(app, ["graph"])

    assert result.exit_code == 0
    assert "Roots (no dependencies)" in result.stdout
    assert "build ← [lint]" in result.stdout


def test_graph_command_dot_output() -> None:
    """Test graph command DOT output."""
    with runner.isolated_filesystem():
        with open("cascade.yaml", "w", encoding="utf-8") as file:
            file.write(
                "version: 1\n\n"
                "tasks:\n"
                "  lint:\n"
                "    command: echo lint\n"
                "  build:\n"
                "    command: echo build\n"
                "    depends_on:\n"
                "      - lint\n"
            )

        result = runner.invoke(app, ["graph", "--format", "dot"])

    assert result.exit_code == 0
    assert "digraph cascade {" in result.stdout
    assert '"lint" -> "build";' in result.stdout


def test_validate_command_with_valid_config() -> None:
    """Test validate command with a valid local config file."""
    with runner.isolated_filesystem():
        with open("cascade.yaml", "w", encoding="utf-8") as file:
            file.write(
                "version: 1\n\n"
                "tasks:\n"
                "  build:\n"
                "    command: echo build\n"
            )

        result = runner.invoke(app, ["validate"])

    assert result.exit_code == 0
    assert "Configuration is valid:" in result.stdout
    assert "Discovered 1 task(s)." in result.stdout


def test_validate_command_with_invalid_config() -> None:
    """Test validate command fails with invalid config."""
    with runner.isolated_filesystem():
        with open("cascade.yaml", "w", encoding="utf-8") as file:
            file.write("tasks: []\n")

        result = runner.invoke(app, ["validate"])

    assert result.exit_code == 1
    assert "Configuration validation failed" in result.stdout or "Configuration validation failed" in result.stderr
