"""Unit tests for task executor."""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from cascade.executor import TaskExecutionError, TaskExecutor, TaskState


def test_execute_simple_command() -> None:
    """Execute a simple successful command."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    result = executor.execute_task(
        task_name="echo-test",
        command="echo hello",
    )

    assert result.state == TaskState.COMPLETED
    assert result.exit_code == 0
    assert "hello" in result.stdout


def test_execute_failing_command() -> None:
    """Raise TaskExecutionError for non-zero exit codes."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    with pytest.raises(TaskExecutionError) as exc_info:
        executor.execute_task(
            task_name="fail-test",
            command="exit 42",
        )

    assert exc_info.value.exit_code == 42
    assert "fail-test" in str(exc_info.value)


def test_execute_with_environment_variables() -> None:
    """Pass environment variables to subprocess."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    result = executor.execute_task(
        task_name="env-test",
        command="echo $CASCADE_TEST_VAR",
        env={"CASCADE_TEST_VAR": "custom-value"},
    )

    assert result.state == TaskState.COMPLETED
    assert "custom-value" in result.stdout


def test_execute_with_working_directory(tmp_path: Path) -> None:
    """Execute command in specified working directory."""
    test_dir = tmp_path / "workdir"
    test_dir.mkdir()
    (test_dir / "marker.txt").write_text("found")

    executor = TaskExecutor(console=Console(file=None), quiet=True)

    result = executor.execute_task(
        task_name="pwd-test",
        command="cat marker.txt",
        working_dir=test_dir,
    )

    assert result.state == TaskState.COMPLETED
    assert "found" in result.stdout


def test_execute_captures_stderr() -> None:
    """Capture stderr output from commands."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    result = executor.execute_task(
        task_name="stderr-test",
        command="echo error-output >&2",
    )

    assert result.state == TaskState.COMPLETED
    assert "error-output" in result.stderr
