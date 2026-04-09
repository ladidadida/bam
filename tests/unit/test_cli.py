"""Unit tests for bam.cli."""

from __future__ import annotations

import os

import pytest
from typer.testing import CliRunner

from bam_tool.cli import _parse_jobs_value, app

runner = CliRunner()


def test_main_no_args_shows_help() -> None:
    """Test root command with no args shows help."""
    result = runner.invoke(app, [], env={"NO_COLOR": "1"})
    assert result.exit_code in (0, 2)
    output = (result.stdout or "") + (result.stderr or "")
    assert "Fast builds, no fluff." in output or "Usage:" in output


def test_help_lists_skeleton_commands() -> None:
    """Test that management flags are available."""
    result = runner.invoke(app, ["--help"], env={"NO_COLOR": "1"})
    assert result.exit_code == 0
    assert "--list" in result.stdout
    assert "--graph" in result.stdout
    assert "--validate" in result.stdout
    assert "--clean" in result.stdout


def test_main_help() -> None:
    """Test main() with --help flag."""
    result = runner.invoke(app, ["--help"], env={"NO_COLOR": "1"})
    assert result.exit_code == 0


def test_main_version() -> None:
    """Test main() with --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0


def test_run_command() -> None:
    """Test running a task directly from the base command."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
            file.write("version: 1\n\ntasks:\n  build:\n    command: echo 'Building project'\n")

        result = runner.invoke(app, ["build"])

    assert result.exit_code == 0
    assert "Building project" in result.stdout or "Successfully executed" in result.stdout


def test_run_command_with_failing_task() -> None:
    """Test that a failing task sets exit code 1."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
            file.write("version: 1\n\ntasks:\n  fail:\n    command: exit 1\n")

        result = runner.invoke(app, ["fail"])

    assert result.exit_code == 1
    assert "FAILED: fail" in result.stdout or "Execution stopped" in result.stdout


def test_run_dry_run_shows_execution_plan() -> None:
    """Test --dry-run prints dependency-respecting plan."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
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

        result = runner.invoke(app, ["build", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry-run execution order:" in result.stdout
    assert "1. lint" in result.stdout
    assert "2. build" in result.stdout


def test_graph_command_ascii_output() -> None:
    """Test graph command default ASCII output."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
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

        result = runner.invoke(app, ["--graph"])

    assert result.exit_code == 0
    assert "Roots (no dependencies)" in result.stdout
    assert "build ← [lint]" in result.stdout


def test_graph_command_dot_output() -> None:
    """Test --graph-dot outputs Graphviz DOT format."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
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

        result = runner.invoke(app, ["--graph-dot"])

    assert result.exit_code == 0
    assert "digraph bam {" in result.stdout
    assert '"lint" -> "build";' in result.stdout


def test_validate_command_with_valid_config() -> None:
    """Test validate command with a valid local config file."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
            file.write("version: 1\n\ntasks:\n  build:\n    command: echo build\n")

        result = runner.invoke(app, ["--validate"])

    assert result.exit_code == 0
    assert "Configuration is valid:" in result.stdout
    assert "Discovered 1 task(s)." in result.stdout


def test_validate_command_with_invalid_config() -> None:
    """Test --validate fails with invalid config."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
            file.write("tasks: []\n")

        result = runner.invoke(app, ["--validate"])

    assert result.exit_code == 1
    assert (
        "Configuration validation failed" in result.stdout
        or "Configuration validation failed" in result.stderr
    )


def test_parse_jobs_value_none() -> None:
    """Test _parse_jobs_value with None defaults to auto (CPU count)."""
    result = _parse_jobs_value(None)
    # Should be same as auto - CPU count capped at 8
    import os

    expected = min(os.cpu_count() or 1, 8)
    assert result == expected


def test_parse_jobs_value_one() -> None:
    """Test _parse_jobs_value with '1' returns 1."""
    assert _parse_jobs_value("1") == 1


def test_parse_jobs_value_integer() -> None:
    """Test _parse_jobs_value with integer string."""
    assert _parse_jobs_value("4") == 4
    assert _parse_jobs_value("8") == 8


def test_parse_jobs_value_auto() -> None:
    """Test _parse_jobs_value with 'auto' uses CPU count."""
    result = _parse_jobs_value("auto")
    cpu_count = os.cpu_count() or 1
    expected = min(cpu_count, 8)
    assert result == expected


def test_parse_jobs_value_invalid() -> None:
    """Test _parse_jobs_value with invalid value raises BadParameter."""
    with pytest.raises(Exception):  # typer.BadParameter
        _parse_jobs_value("invalid")


def test_parse_jobs_value_negative() -> None:
    """Test _parse_jobs_value with negative value raises BadParameter."""
    with pytest.raises(Exception):  # typer.BadParameter
        _parse_jobs_value("-1")


def test_parse_jobs_value_zero() -> None:
    """Test _parse_jobs_value with zero raises BadParameter."""
    with pytest.raises(Exception):  # typer.BadParameter
        _parse_jobs_value("0")


def test_run_with_jobs_flag() -> None:
    """Test run command accepts --jobs flag."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
            file.write("version: 1\n\ntasks:\n  build:\n    command: echo build\n")

        result = runner.invoke(app, ["build", "--jobs", "2"])

    assert result.exit_code == 0


def test_run_with_jobs_auto() -> None:
    """Test run command accepts --jobs=auto."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
            file.write("version: 1\n\ntasks:\n  build:\n    command: echo build\n")

        result = runner.invoke(app, ["build", "--jobs", "auto"])

    assert result.exit_code == 0


def test_run_with_jobs_short_flag() -> None:
    """Test run command accepts -j short flag."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
            file.write("version: 1\n\ntasks:\n  build:\n    command: echo build\n")

        result = runner.invoke(app, ["build", "-j", "4"])

    assert result.exit_code == 0


def test_dry_run_with_jobs_shows_parallel_info() -> None:
    """Test --dry-run with --jobs shows parallel execution info."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as file:
            file.write("version: 1\n\ntasks:\n  build:\n    command: echo build\n")

        result = runner.invoke(app, ["build", "--dry-run", "--jobs", "4"])

    assert result.exit_code == 0
    assert "Dry-run execution order:" in result.stdout
    assert "Parallel execution: 4 workers" in result.stdout


# ── --stage / -s tests ────────────────────────────────────────────────────────

_STAGE_CONFIG = (
    "version: 1\n\n"
    "tasks:\n"
    "  test-unit:\n"
    "    command: echo unit\n"
    "    stage: test\n"
    "  test-integration:\n"
    "    command: echo integration\n"
    "    stage: test\n"
    "  lint:\n"
    "    command: echo lint\n"
    "    stage: lint\n"
)


def test_stage_flag_runs_all_tasks_in_stage() -> None:
    """--stage runs all tasks belonging to the given stage."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as f:
            f.write(_STAGE_CONFIG)

        result = runner.invoke(app, ["--stage", "test"])

    assert result.exit_code == 0
    assert "unit" in result.stdout or "Successfully executed" in result.stdout


def test_stage_short_flag() -> None:
    """-s short form is equivalent to --stage."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as f:
            f.write(_STAGE_CONFIG)

        result = runner.invoke(app, ["-s", "lint"])

    assert result.exit_code == 0


def test_stage_flag_dry_run() -> None:
    """--stage with --dry-run shows tasks in that stage."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as f:
            f.write(_STAGE_CONFIG)

        result = runner.invoke(app, ["--stage", "test", "--dry-run"])

    assert result.exit_code == 0
    assert "Dry-run execution order:" in result.stdout
    assert "test-unit" in result.stdout
    assert "test-integration" in result.stdout
    assert "lint" not in result.stdout


def test_stage_flag_unknown_stage_exits_nonzero() -> None:
    """--stage with a nonexistent stage name exits with code 1."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as f:
            f.write(_STAGE_CONFIG)

        result = runner.invoke(app, ["--stage", "nonexistent"])

    assert result.exit_code == 1
    assert "nonexistent" in (result.stdout + (result.stderr or ""))


def test_stage_and_task_together_exits_nonzero() -> None:
    """Providing both a task argument and --stage exits with code 1."""
    with runner.isolated_filesystem():
        with open("bam.yaml", "w", encoding="utf-8") as f:
            f.write(_STAGE_CONFIG)

        result = runner.invoke(app, ["lint", "--stage", "test"])

    assert result.exit_code == 1
