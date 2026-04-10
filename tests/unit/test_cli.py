"""Unit tests for bam.cli."""

from __future__ import annotations

import asyncio
import contextlib
import os
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from bam_tool.cli import _parse_jobs_value, _watch_async, app
from bam_tool.config.schema import BamConfig, TaskConfig

runner = CliRunner()


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-9;]*[mK]", "", text)


def test_main_no_args_shows_help() -> None:
    """Test root command with no args shows help."""
    result = runner.invoke(app, [])
    assert result.exit_code in (0, 2)
    output = _strip_ansi((result.stdout or "") + (result.stderr or ""))
    assert "Fast builds, no fluff." in output or "Usage:" in output


def test_help_lists_skeleton_commands() -> None:
    """Test that management flags are available."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    output = _strip_ansi(result.stdout)
    assert "--list" in output
    assert "--graph" in output
    assert "--validate" in output
    assert "--clean" in output


def test_main_help() -> None:
    """Test main() with --help flag."""
    result = runner.invoke(app, ["--help"])
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


# ── Interactive watch mode tests ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_interactive_watch_restarts_after_file_change(tmp_path: pytest.TempPathFactory) -> None:
    """_watch_async cancels the running interactive task and restarts it on file change."""
    from pathlib import Path

    config_file = Path("/fake/bam.yaml")
    loaded_config = BamConfig(
        tasks={"serve": TaskConfig(command="python -m http.server", interactive=True)}
    )

    run_call_count = 0

    async def fake_run_task(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        nonlocal run_call_count
        run_call_count += 1
        await asyncio.sleep(100)  # simulate long-running server

    change_call_count = 0

    async def fake_wait_for_change(*args, **kwargs) -> Path:  # type: ignore[no-untyped-def]
        nonlocal change_call_count
        change_call_count += 1
        if change_call_count == 1:
            await asyncio.sleep(0.1)  # first call: return a change quickly
            return Path("/fake/source.py")
        # subsequent calls: block until cancelled
        await asyncio.sleep(100)
        return Path("/fake/never")  # never reached

    fake_graph = MagicMock()

    with (
        patch("bam_tool.cli.load_config", return_value=(config_file, loaded_config)),
        patch("bam_tool.cli.build_task_graph", return_value=fake_graph),
        patch("bam_tool.cli.execution_order_for_targets", return_value=["serve"]),
        patch("bam_tool.cli.compute_watch_dirs", return_value={Path("/fake"): False}),
        patch("bam_tool.cli._run_task_async", side_effect=fake_run_task),
        patch("bam_tool.cli.wait_for_change", side_effect=fake_wait_for_change),
    ):
        watch_task = asyncio.create_task(
            _watch_async(
                task="serve",
                no_cache=False,
                debounce=0.05,
                config=None,
                jobs=None,
                quiet=True,
                plain=True,
            )
        )

        # Let the loop run through the first change + restart.
        await asyncio.sleep(0.5)
        watch_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watch_task

    # Must have been invoked at least twice: initial run + at least one restart.
    assert run_call_count >= 2


@pytest.mark.asyncio
async def test_non_interactive_watch_uses_sequential_loop(tmp_path: pytest.TempPathFactory) -> None:
    """_watch_async keeps the sequential run-then-wait pattern for non-interactive tasks."""
    from pathlib import Path

    config_file = Path("/fake/bam.yaml")
    loaded_config = BamConfig(
        tasks={"build": TaskConfig(command="echo hi", interactive=False)}
    )

    run_call_count = 0

    async def fake_run_task(*args, **kwargs) -> None:  # type: ignore[no-untyped-def]
        nonlocal run_call_count
        run_call_count += 1
        # Complete immediately (non-interactive)

    change_call_count = 0

    async def fake_wait_for_change(*args, **kwargs) -> Path:  # type: ignore[no-untyped-def]
        nonlocal change_call_count
        change_call_count += 1
        if change_call_count == 1:
            await asyncio.sleep(0.1)
            return Path("/fake/source.py")
        await asyncio.sleep(100)
        return Path("/fake/never")

    fake_graph = MagicMock()

    with (
        patch("bam_tool.cli.load_config", return_value=(config_file, loaded_config)),
        patch("bam_tool.cli.build_task_graph", return_value=fake_graph),
        patch("bam_tool.cli.execution_order_for_targets", return_value=["build"]),
        patch("bam_tool.cli.compute_watch_dirs", return_value={Path("/fake"): False}),
        patch("bam_tool.cli._run_task_async", side_effect=fake_run_task),
        patch("bam_tool.cli.wait_for_change", side_effect=fake_wait_for_change),
    ):
        watch_task = asyncio.create_task(
            _watch_async(
                task="build",
                no_cache=False,
                debounce=0.05,
                config=None,
                jobs=None,
                quiet=True,
                plain=True,
            )
        )

        await asyncio.sleep(0.5)
        watch_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await watch_task

    # Initial run + at least one re-run after the change.
    assert run_call_count >= 2

