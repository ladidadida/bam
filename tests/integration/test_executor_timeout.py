"""Integration tests for task executor timeout behaviour.

These tests spawn real subprocesses to verify that the kill-on-timeout path
works end-to-end, including proper process-group teardown so that child
processes (e.g. the ``sleep`` launched by the shell) are also killed and
the pipe is closed promptly.
"""

from __future__ import annotations

import pytest
from rich.console import Console

from bam_tool.executor import TaskExecutionError, TaskExecutor
from bam_tool.executor.executor import TaskState


@pytest.mark.asyncio
async def test_timeout_kills_slow_task() -> None:
    """A task that exceeds its timeout is killed and raises TaskExecutionError."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    with pytest.raises(TaskExecutionError) as exc_info:
        await executor.execute_task(
            task_name="slow-task",
            command="sleep 10",
            timeout=0.2,
        )

    assert "timed out" in exc_info.value.stderr.lower()
    assert exc_info.value.exit_code == -1


@pytest.mark.asyncio
async def test_timeout_not_triggered_for_fast_task() -> None:
    """A task that finishes within its timeout completes normally."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    result = await executor.execute_task(
        task_name="fast-task",
        command="echo done",
        timeout=5.0,
    )

    assert result.state == TaskState.COMPLETED


@pytest.mark.asyncio
async def test_timeout_callback_continue_then_abort() -> None:
    """on_timeout returning False continues, then True aborts on next expiry."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    call_count = 0

    async def on_timeout() -> bool:
        nonlocal call_count
        call_count += 1
        return call_count >= 2  # abort on second expiry

    with pytest.raises(TaskExecutionError) as exc_info:
        await executor.execute_task(
            task_name="continue-then-abort",
            command="sleep 10",
            timeout=0.2,
            on_timeout=on_timeout,
        )

    assert call_count == 2
    assert "timed out" in exc_info.value.stderr.lower()


@pytest.mark.asyncio
async def test_timeout_callback_always_continue_until_task_ends() -> None:
    """on_timeout returning False keeps waiting; task finishes on its own."""
    executor = TaskExecutor(console=Console(file=None), quiet=True)

    async def on_timeout() -> bool:
        return False  # never abort

    result = await executor.execute_task(
        task_name="short-sleep",
        command="sleep 0.1 && echo ok",
        timeout=0.05,  # fires before task finishes, but we keep waiting
        on_timeout=on_timeout,
    )

    assert result.state == TaskState.COMPLETED
    assert "ok" in result.stdout
