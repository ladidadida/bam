"""Unit tests for task executor."""

from __future__ import annotations

from pathlib import Path

import pytest
from rich.console import Console

from bam_tool.cache import LocalCache
from bam_tool.executor import RunnerNotFoundError, TaskExecutionError, TaskExecutor, TaskState


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
        command="echo $BAM_TEST_VAR",
        env={"BAM_TEST_VAR": "custom-value"},
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


@pytest.mark.asyncio
async def test_execute_with_cache_no_outputs(tmp_path: Path) -> None:
    """Cache tasks that produce no outputs (e.g. lint, typecheck)."""
    cache_dir = tmp_path / "cache"
    cache = LocalCache(cache_dir)

    input_file = tmp_path / "input.txt"
    input_file.write_text("data", encoding="utf-8")

    executor = TaskExecutor(console=Console(file=None), quiet=True, cache=cache)

    # First run: should execute and store an empty cache entry
    result1 = await executor.execute_task(
        task_name="lint-test",
        command="echo lint-ok",
        inputs=[input_file],
        outputs=[],
    )
    assert result1.state == TaskState.COMPLETED
    assert not result1.cache_hit

    # Second run: same inputs → cache hit, command not re-executed
    result2 = await executor.execute_task(
        task_name="lint-test",
        command="echo lint-ok",
        inputs=[input_file],
        outputs=[],
    )
    assert result2.state == TaskState.COMPLETED
    assert result2.cache_hit

    # Changing input content should invalidate the cache
    input_file.write_text("changed", encoding="utf-8")
    result3 = await executor.execute_task(
        task_name="lint-test",
        command="echo lint-ok",
        inputs=[input_file],
        outputs=[],
    )
    assert result3.state == TaskState.COMPLETED
    assert not result3.cache_hit


# ---------------------------------------------------------------------------
# Runner tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shell_runner_executes_normally() -> None:
    """Explicit shell runner behaves like no runner at all."""
    from bam_tool.config.schema import RunnerConfig

    executor = TaskExecutor(console=Console(file=None), quiet=True)
    result = await executor.execute_task(
        task_name="shell-runner-test",
        command="echo shell-ok",
        runner=RunnerConfig(type="shell"),
    )
    assert result.state == TaskState.COMPLETED
    assert "shell-ok" in result.stdout


@pytest.mark.asyncio
async def test_python_uv_runner_executes_inline_script() -> None:
    """python-uv runner treats command body as an inline Python script."""
    from bam_tool.config.schema import RunnerConfig

    executor = TaskExecutor(console=Console(file=None), quiet=True)
    result = await executor.execute_task(
        task_name="python-runner-test",
        command='print("hello from python")',
        runner=RunnerConfig(type="python-uv"),
    )
    assert result.state == TaskState.COMPLETED
    assert "hello from python" in result.stdout


@pytest.mark.asyncio
async def test_python_uv_runner_multiline_script() -> None:
    """python-uv runner handles multiline scripts."""
    from bam_tool.config.schema import RunnerConfig

    script = "x = 6 * 7\nprint(f'answer={x}')"
    executor = TaskExecutor(console=Console(file=None), quiet=True)
    result = await executor.execute_task(
        task_name="python-multiline-test",
        command=script,
        runner=RunnerConfig(type="python-uv"),
    )
    assert result.state == TaskState.COMPLETED
    assert "answer=42" in result.stdout


@pytest.mark.asyncio
async def test_python_uv_runner_cleans_up_tempfile() -> None:
    """python-uv runner removes the temp script file after execution."""
    import glob
    import tempfile

    from bam_tool.config.schema import RunnerConfig

    tmpdir = tempfile.gettempdir()
    before = set(glob.glob(f"{tmpdir}/*.py"))

    executor = TaskExecutor(console=Console(file=None), quiet=True)
    await executor.execute_task(
        task_name="cleanup-test",
        command="pass",
        runner=RunnerConfig(type="python-uv"),
    )

    after = set(glob.glob(f"{tmpdir}/*.py"))
    # No new .py tempfiles should remain
    assert not (after - before)


def test_runner_cache_keys_differ_by_runner_type() -> None:
    """Different runners produce different cache keys for the same command."""
    from bam_tool.config.schema import RunnerConfig
    from bam_tool.executor.executor import _runner_cache_prefix

    shell_prefix = _runner_cache_prefix(None)
    uv_prefix = _runner_cache_prefix(RunnerConfig(type="python-uv"))
    docker_prefix = _runner_cache_prefix(RunnerConfig(type="docker", image="python:3.14"))

    command = "echo hello"
    assert shell_prefix + command != uv_prefix + command
    assert shell_prefix + command != docker_prefix + command
    assert uv_prefix + command != docker_prefix + command


def test_runner_cache_key_includes_docker_image() -> None:
    """Two docker runners with different images produce different cache prefixes."""
    from bam_tool.config.schema import RunnerConfig
    from bam_tool.executor.executor import _runner_cache_prefix

    prefix_a = _runner_cache_prefix(RunnerConfig(type="docker", image="python:3.13"))
    prefix_b = _runner_cache_prefix(RunnerConfig(type="docker", image="python:3.14"))
    assert prefix_a != prefix_b


# ---------------------------------------------------------------------------
# Missing-tool error tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_docker_runner_raises_when_docker_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RunnerNotFoundError is raised before attempting execution when docker is absent."""
    import shutil

    from bam_tool.config.schema import RunnerConfig

    monkeypatch.setattr(shutil, "which", lambda name: None)

    executor = TaskExecutor(console=Console(file=None), quiet=True)
    with pytest.raises(RunnerNotFoundError) as exc_info:
        await executor.execute_task(
            task_name="docker-missing",
            command="echo hi",
            runner=RunnerConfig(type="docker", image="python:3.14-slim"),
        )

    assert exc_info.value.tool == "docker"
    assert exc_info.value.runner_type == "docker"
    assert "docker" in str(exc_info.value).lower()
    assert "PATH" in str(exc_info.value)


@pytest.mark.asyncio
async def test_python_uv_runner_raises_when_uv_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """RunnerNotFoundError is raised before attempting execution when uv is absent."""
    import shutil

    from bam_tool.config.schema import RunnerConfig

    monkeypatch.setattr(shutil, "which", lambda name: None)

    executor = TaskExecutor(console=Console(file=None), quiet=True)
    with pytest.raises(RunnerNotFoundError) as exc_info:
        await executor.execute_task(
            task_name="uv-missing",
            command="print('hi')",
            runner=RunnerConfig(type="python-uv"),
        )

    assert exc_info.value.tool == "uv"
    assert exc_info.value.runner_type == "python-uv"
