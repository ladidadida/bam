"""Task executor with subprocess execution and output capture."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shlex
import shutil
import signal
import tempfile
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
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


# Module-level registry of active subprocess process-group IDs.
# Updated by execute_task; read by the SIGTSTP/SIGCONT handlers in cli.py so
# that suspending / resuming bam also suspends / resumes all child processes.
_active_pgids: set[int] = set()


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
        timeout: float | None = None,
        on_timeout: Callable[[], Awaitable[bool]] | None = None,
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

        # Show task start
        if not self.quiet:
            if self.buffer_output:
                self.console.print(f"\n──> started: {task_name}")
            else:
                self.console.print(f"[cyan]Running:[/cyan] {task_name}")
                self.console.print(f"[dim]Command:[/dim] {command}")
        task_start = time.monotonic()

        try:
            async with _resolve_command(command, runner, cwd) as actual_command:
                # Create subprocess with asyncio
                process = await asyncio.create_subprocess_shell(
                    actual_command,
                    cwd=cwd,
                    env=merged_env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    start_new_session=True,
                )

                # Register process group so SIGTSTP/SIGCONT handlers can
                # suspend/resume it alongside bam, and CancelledError cleanup
                # can terminate it on Ctrl-C or parallel-failure cancellation.
                _pgid: int | None = None
                with contextlib.suppress(ProcessLookupError):
                    _pgid = os.getpgid(process.pid)
                if _pgid is not None:
                    _active_pgids.add(_pgid)

                # Wait for process to complete, with optional timeout loop.
                # asyncio.shield prevents cancellation of the underlying future
                # so we can keep waiting after a timeout when the user chooses to.
                _comm_future: asyncio.Future[tuple[bytes, bytes]] | None = None
                try:
                    if timeout is None:
                        stdout_bytes, stderr_bytes = await process.communicate()
                    else:
                        _comm_future = asyncio.ensure_future(process.communicate())
                        while True:
                            try:
                                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                                    asyncio.shield(_comm_future), timeout=timeout
                                )
                                break
                            except TimeoutError:
                                abort = True
                                if on_timeout is not None:
                                    abort = await on_timeout()
                                if abort:
                                    try:
                                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                                    except ProcessLookupError:
                                        process.kill()
                                    await _comm_future
                                    raise TaskExecutionError(
                                        task_name,
                                        command,
                                        -1,
                                        "",
                                        f"Task timed out after {timeout:.0f}s",
                                    )
                                # User chose to continue — reset the timer by looping
                except asyncio.CancelledError:
                    # Kill subprocess process group, then clean up the comm future
                    # before re-raising so no orphan processes are left behind.
                    with contextlib.suppress(ProcessLookupError, OSError):
                        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    with contextlib.suppress(Exception):
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    if process.returncode is None:
                        with contextlib.suppress(ProcessLookupError, OSError):
                            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                        with contextlib.suppress(Exception):
                            await process.wait()
                    if _comm_future is not None and not _comm_future.done():
                        _comm_future.cancel()
                        with contextlib.suppress(Exception):
                            await _comm_future
                    raise
                finally:
                    if _pgid is not None:
                        _active_pgids.discard(_pgid)

                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")

                # Display output based on mode
                if not self.quiet:
                    if self.buffer_output:
                        # Buffered mode: open fence, flush output
                        _fill = "─" * max(0, 72 - len(task_name) - 5)
                        self.console.print(f"\n─── {task_name} {_fill}")
                        if stdout:
                            self.console.print(stdout, end="")
                        if stderr:
                            self.console.print(f"[yellow]{stderr}[/yellow]", end="")
                    else:
                        # Streaming mode: output already shown above, just print it
                        if stdout:
                            self.console.print(stdout, end="")
                        if stderr:
                            self.console.print(f"[yellow]{stderr}[/yellow]", end="")

                # After communicate(), returncode should never be None
                exit_code = process.returncode if process.returncode is not None else -1

                if exit_code != 0:
                    if not self.quiet:
                        if self.buffer_output:
                            _elapsed = time.monotonic() - task_start
                            _label = f"──── FAILED: {task_name}  exit {exit_code}  {_elapsed:.1f}s "
                            _fill = "─" * max(0, 72 - len(_label))
                            self.console.print(f"[red]{_label}{_fill}[/]")
                        else:
                            self.console.print(f"[red]✗[/red] {task_name} (exit {exit_code})")
                    raise TaskExecutionError(task_name, command, exit_code, stdout, stderr)

                if not self.quiet:
                    if self.buffer_output:
                        _elapsed = time.monotonic() - task_start
                        _label = f"──── PASSED: {task_name}  {_elapsed:.1f}s "
                        _fill = "─" * max(0, 72 - len(_label))
                        self.console.print(f"[green]{_label}{_fill}[/]")
                    else:
                        self.console.print(f"[green]✓[/green] {task_name}")

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

        except TaskExecutionError:
            raise
        except RunnerNotFoundError:
            # Re-raise as-is — callers handle these explicitly
            raise
        except Exception as exc:
            # Catch all other exceptions (OSError, asyncio errors, etc.)
            if not self.quiet:
                self.console.print(f"[red]✗[/red] Task '{task_name}' failed: {exc}")
            raise TaskExecutionError(task_name, command, -1, "", str(exc)) from exc

    async def execute_interactive_task(
        self,
        task_name: str,
        command: str,
        env: dict[str, str] | None = None,
        working_dir: Path | None = None,
        runner: RunnerConfig | None = None,
    ) -> TaskResult:
        """Run a long-running, interactive task in the foreground.

        Unlike ``execute_task``, this method:
        * Inherits stdin / stdout / stderr from the parent process so the user
          can interact with the child directly (e.g. a dev server, REPL, watcher).
        * Never consults or writes the cache.
        * Has no timeout — it runs until the process exits or the user interrupts
          it with Ctrl-C, which sends SIGINT to the process naturally (same process
          group) and is treated as a clean exit.
        * Exits with a non-zero ``TaskResult`` only when the process returns a
          non-zero, non-signal exit code.

        Args:
            task_name: Name of the task (used for display only).
            command: Shell command to execute.
            env: Additional environment variables merged with the system env.
            working_dir: Working directory; defaults to ``Path.cwd()``.
            runner: Runner configuration (shell / docker / python-uv).

        Returns:
            TaskResult reflecting the process exit code.

        Raises:
            TaskExecutionError: If the process exits with a non-zero code that
                is not explained by a user interrupt (SIGINT / SIGTERM).
        """
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        cwd = working_dir.resolve() if working_dir else Path.cwd()

        if not self.quiet:
            self.console.print(f"[cyan]Starting:[/cyan] {task_name} [dim](interactive)[/dim]")
            self.console.print(f"[dim]Command:[/dim]  {command}")
            self.console.print("[dim]Press Ctrl-C to stop.[/dim]")

        try:
            async with _resolve_command(command, runner, cwd) as actual_command:
                # No start_new_session — we want Ctrl-C (SIGINT) to reach the
                # child naturally through the shared terminal process group.
                process = await asyncio.create_subprocess_shell(
                    actual_command,
                    cwd=cwd,
                    env=merged_env,
                    stdin=None,  # inherit terminal stdin
                    stdout=None,  # inherit terminal stdout
                    stderr=None,  # inherit terminal stderr
                )

                try:
                    exit_code = await process.wait()
                except asyncio.CancelledError:
                    # Graceful shutdown: give the process a moment to handle SIGINT
                    # (which it already received as part of the process group), then
                    # escalate to SIGTERM and finally SIGKILL if necessary.
                    with contextlib.suppress(ProcessLookupError):
                        process.terminate()
                    with contextlib.suppress(TimeoutError):
                        await asyncio.wait_for(process.wait(), timeout=5.0)
                    if process.returncode is None:
                        with contextlib.suppress(ProcessLookupError):
                            process.kill()
                        await process.wait()
                    raise

        except RunnerNotFoundError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            raise TaskExecutionError(task_name, command, -1, "", str(exc)) from exc

        # Treat SIGINT (-2) and SIGTERM (-15) as clean exits — the user stopped it.
        clean_signals = {-signal.SIGINT, -signal.SIGTERM}
        if exit_code != 0 and exit_code not in clean_signals:
            raise TaskExecutionError(task_name, command, exit_code)

        return TaskResult(
            task_name=task_name,
            state=TaskState.COMPLETED,
            exit_code=exit_code,
        )
