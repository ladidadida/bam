"""Unit tests for task executor."""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from cascade.cache import LocalCache
from cascade.executor import TaskExecutionError, TaskExecutor, TaskState


@pytest.mark.asyncio
async def test_execute_simple_command() -> None:
    """Execute a simple successful command."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    result = await executor.execute_task(
        task_name="echo-test",
        command="echo hello",
    )

    assert result.state == TaskState.COMPLETED
    assert result.exit_code == 0
    assert "hello" in result.stdout


@pytest.mark.asyncio
async def test_execute_failing_command() -> None:
    """Raise TaskExecutionError for non-zero exit codes."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    with pytest.raises(TaskExecutionError) as exc_info:
        await executor.execute_task(
            task_name="fail-test",
            command="exit 42",
        )

    assert exc_info.value.exit_code == 42
    assert "fail-test" in str(exc_info.value)


@pytest.mark.asyncio
async def test_execute_with_environment_variables() -> None:
    """Pass environment variables to subprocess."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    result = await executor.execute_task(
        task_name="env-test",
        command="echo $CASCADE_TEST_VAR",
        env={"CASCADE_TEST_VAR": "custom-value"},
    )

    assert result.state == TaskState.COMPLETED
    assert "custom-value" in result.stdout


@pytest.mark.asyncio
async def test_execute_with_working_directory(tmp_path: Path) -> None:
    """Execute command in specified working directory."""
    test_dir = tmp_path / "workdir"
    test_dir.mkdir()
    (test_dir / "marker.txt").write_text("found")

    executor = TaskExecutor(console=Console(file=None), quiet=True)

    result = await executor.execute_task(
        task_name="pwd-test",
        command="cat marker.txt",
        working_dir=test_dir,
    )

    assert result.state == TaskState.COMPLETED
    assert "found" in result.stdout


@pytest.mark.asyncio
async def test_execute_captures_stderr() -> None:
    """Capture stderr output from commands."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    result = await executor.execute_task(
        task_name="stderr-test",
        command="echo error-output >&2",
    )

    assert result.state == TaskState.COMPLETED
    assert "error-output" in result.stderr


@pytest.mark.asyncio
async def test_execute_with_cache_hit(tmp_path: Path) -> None:
    """Skip execution on cache hit."""
    cache_dir = tmp_path / "cache"
    cache = LocalCache(cache_dir)

    input_file = tmp_path / "input.txt"
    input_file.write_text("data", encoding="utf-8")

    output_file = tmp_path / "output.txt"
    output_file.write_text("result", encoding="utf-8")

    executor = TaskExecutor(console=Console(file=None), quiet=True, cache=cache)

    # First run: should execute and cache
    result1 = await executor.execute_task(
        task_name="cached-test",
        command="cat input.txt > output.txt",
        inputs=[input_file],
        outputs=[output_file],
        working_dir=tmp_path,
    )

    assert result1.state == TaskState.COMPLETED
    assert not result1.cache_hit

    # Remove output to verify cache restoration
    output_file.unlink()

    # Second run: should hit cache
    result2 = await executor.execute_task(
        task_name="cached-test",
        command="cat input.txt > output.txt",
        inputs=[input_file],
        outputs=[output_file],
        working_dir=tmp_path,
    )

    assert result2.state == TaskState.COMPLETED
    assert result2.cache_hit
    assert output_file.exists()
