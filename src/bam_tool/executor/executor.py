"""Task executor with subprocess execution and output capture."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shlex
import shutil
import tempfile
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from rich.console import Console

from bam_tool.cache import CacheBackend, compute_cache_key
from bam_tool.config.schema import RunnerConfig


class RunnerNotFoundError(Exception):
    """Raised when a required external tool for a runner is not on PATH."""

    def __init__(self, tool: str, runner_type: str) -> None:
        self.tool = tool
        self.runner_type = runner_type
        super().__init__(
            f"Runner '{runner_type}' requires '{tool}' but it was not found on PATH. "
            f"Install {tool} and make sure it is available before running this task."
        )


def _check_tool(name: str, runner_type: str) -> None:
    """Raise RunnerNotFoundError if *name* is not on PATH."""
    if shutil.which(name) is None:
        raise RunnerNotFoundError(name, runner_type)


def _runner_cache_prefix(runner: RunnerConfig | None) -> str:
    """Return a stable string that uniquely identifies the runner configuration.

    Prepended to the command before cache-key hashing so that the same command
    run via different runners produces different cache entries.
    """
    if runner is None or runner.type == "shell":
        return ""
    if runner.type == "docker":
        return f"[runner:docker:{runner.image}]"
    if runner.type == "python-uv":
        return "[runner:python-uv]"
    return ""


@contextlib.asynccontextmanager
async def _resolve_command(
    command: str,
    runner: RunnerConfig | None,
    cwd: Path,
) -> AsyncGenerator[str]:
    """Yield the actual shell command to execute for the given runner.

    * ``shell`` / ``None`` — yields *command* unchanged.
    * ``docker`` — wraps in ``docker run`` with the cwd bind-mounted.
    * ``python-uv`` — writes the command body to a temp ``.py`` file and yields
      a ``uv run python <tmpfile>`` invocation; cleans up on exit.
    """
    if runner is None or runner.type == "shell":
        yield command
        return

    if runner.type == "docker":
        _check_tool("docker", "docker")
        cwd_str = str(cwd)
        quoted_cwd = shlex.quote(cwd_str)
        yield (
            f"docker run --rm "
            f"-v {quoted_cwd}:{quoted_cwd} "
            f"-w {quoted_cwd} "
            f"{runner.image} "
            f"sh -c {shlex.quote(command)}"
        )
        return

    if runner.type == "python-uv":
        _check_tool("uv", "python-uv")
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8")
        try:
            tmp.write(command)
            tmp.close()
            yield f"uv run python {shlex.quote(tmp.name)}"
        finally:
            Path(tmp.name).unlink(missing_ok=True)
        return

    # Fallback for future runner types
    yield command


class TaskState(StrEnum):
    """Task execution state."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TaskResult:
    """Result of task execution."""

    task_name: str
    state: TaskState
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    error_message: str | None = None
    cache_hit: bool = False


class TaskExecutionError(Exception):
    """Raised when a task execution fails."""

    def __init__(
        self,
        task_name: str,
        command: str,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
    ):
        self.task_name = task_name
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(
            f"Task '{task_name}' failed with exit code {exit_code}\nCommand: {command}"
        )


class TaskExecutor:
    """Execute tasks via subprocess with output capture."""

    def __init__(
        self,
        console: Console | None = None,
        quiet: bool = False,
        cache: CacheBackend | None = None,
        buffer_output: bool = False,
    ):
        """Initialize executor.

        Args:
            console: Rich console for output formatting (creates default if None).
            quiet: Suppress command output streaming.
            cache: Cache backend for artifact storage (None disables caching).
            buffer_output: Buffer output until task completes (for parallel mode).
        """
        self.console = console or Console()
        self.quiet = quiet
        self.cache = cache
        self.buffer_output = buffer_output

    async def execute_task(  # noqa: C901
        self,
        task_name: str,
        command: str,
        inputs: list[Path] | None = None,
        outputs: list[Path] | None = None,
        env: dict[str, str] | None = None,
        working_dir: Path | None = None,
        runner: RunnerConfig | None = None,
    ) -> TaskResult:
        """Execute a task command via subprocess asynchronously.

        Args:
            task_name: Name of the task being executed.
            command: Shell command (or Python script body for python-uv runner).
            inputs: List of input file paths for cache key computation.
            outputs: List of output file paths to cache.
            env: Additional environment variables (merged with system env).
            working_dir: Working directory for command execution.
            runner: Runner configuration controlling how the command is executed.

        Returns:
            TaskResult with execution outcome.

        Raises:
            TaskExecutionError: If command exits with non-zero code.
        """
        input_paths = inputs or []
        output_paths = outputs or []

        # Build cache key — includes runner config so different runners don't collide
        cache_command = _runner_cache_prefix(runner) + command

        # Check cache if enabled
        if self.cache:
            cache_key = compute_cache_key(cache_command, input_paths, env)

            if await self.cache.exists(cache_key):
                if not self.quiet:
                    self.console.print(
                        f"[green]↻[/green] Cache hit for '{task_name}' (key: {cache_key[:12]}...)"
                    )

                if await self.cache.get(cache_key, output_paths):
                    return TaskResult(
                        task_name=task_name,
                        state=TaskState.COMPLETED,
                        exit_code=0,
                        cache_hit=True,
                    )
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        cwd = working_dir.resolve() if working_dir else Path.cwd()

        # Show task start (unless buffering output)
        if not self.quiet and not self.buffer_output:
            self.console.print(f"[cyan]Running:[/cyan] {task_name}")
            self.console.print(f"[dim]Command:[/dim] {command}")

        try:
            async with _resolve_command(command, runner, cwd) as actual_command:
                # Create subprocess with asyncio
                process = await asyncio.create_subprocess_shell(
                    actual_command,
                    cwd=cwd,
                    env=merged_env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                # Wait for process to complete and capture output
                stdout_bytes, stderr_bytes = await process.communicate()
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")

                # Display output based on mode
                if not self.quiet:
                    if self.buffer_output:
                        # Buffered mode: Show task header with output
                        self.console.print(f"\n[cyan]→[/cyan] {task_name}")
                        if stdout:
                            self.console.print(stdout, end="")
                        if stderr:
                            self.console.print(f"[yellow]{stderr}[/yellow]", end="")
                    else:
                        # Streaming mode: Output already shown above, just print it
                        if stdout:
                            self.console.print(stdout, end="")
                        if stderr:
                            self.console.print(f"[yellow]{stderr}[/yellow]", end="")

                # After communicate(), returncode should never be None
                exit_code = process.returncode if process.returncode is not None else -1

                if exit_code != 0:
                    if not self.quiet:
                        status_msg = f"[red]✗[/red] {task_name} (exit {exit_code})"
                        self.console.print(status_msg)
                    raise TaskExecutionError(task_name, command, exit_code, stdout, stderr)

                if not self.quiet:
                    status_msg = f"[green]✓[/green] {task_name}"
                    self.console.print(status_msg)

                # Store outputs in cache if enabled
                if self.cache:
                    cache_key = compute_cache_key(cache_command, input_paths, env)
                    if await self.cache.put(cache_key, output_paths):
                        if not self.quiet:
                            self.console.print(
                                f"[dim]Cached outputs (key: {cache_key[:12]}...)[/dim]"
                            )

                return TaskResult(
                    task_name=task_name,
                    state=TaskState.COMPLETED,
                    exit_code=0,
                    stdout=stdout,
                    stderr=stderr,
                )

        except (TaskExecutionError, RunnerNotFoundError):
            # Re-raise as-is — callers handle these explicitly
            raise
        except Exception as exc:
            # Catch all other exceptions (OSError, asyncio errors, etc.)
            if not self.quiet:
                self.console.print(f"[red]✗[/red] Task '{task_name}' failed: {exc}")
            raise TaskExecutionError(task_name, command, -1, "", str(exc)) from exc
