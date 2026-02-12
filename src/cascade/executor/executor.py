"""Task executor with subprocess execution and output capture."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from rich.console import Console


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


class TaskExecutionError(Exception):
    """Raised when a task execution fails."""

    def __init__(self, task_name: str, command: str, exit_code: int):
        self.task_name = task_name
        self.command = command
        self.exit_code = exit_code
        super().__init__(
            f"Task '{task_name}' failed with exit code {exit_code}\n" f"Command: {command}"
        )


class TaskExecutor:
    """Execute tasks via subprocess with output capture."""

    def __init__(self, console: Console | None = None, quiet: bool = False):
        """Initialize executor.

        Args:
            console: Rich console for output formatting (creates default if None).
            quiet: Suppress command output streaming.
        """
        self.console = console or Console()
        self.quiet = quiet

    def execute_task(
        self,
        task_name: str,
        command: str,
        env: dict[str, str] | None = None,
        working_dir: Path | None = None,
    ) -> TaskResult:
        """Execute a task command via subprocess.

        Args:
            task_name: Name of the task being executed.
            command: Shell command to execute.
            env: Additional environment variables (merged with system env).
            working_dir: Working directory for command execution.

        Returns:
            TaskResult with execution outcome.

        Raises:
            TaskExecutionError: If command exits with non-zero code.
        """
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        cwd = working_dir.resolve() if working_dir else Path.cwd()

        if not self.quiet:
            self.console.print(f"[cyan]Running:[/cyan] {task_name}")
            self.console.print(f"[dim]Command:[/dim] {command}")

        try:
            process = subprocess.run(
                command,
                shell=True,
                cwd=cwd,
                env=merged_env,
                capture_output=True,
                text=True,
                check=False,
            )

            if not self.quiet and process.stdout:
                self.console.print(process.stdout, end="")
            if not self.quiet and process.stderr:
                self.console.print(f"[yellow]{process.stderr}[/yellow]", end="")

            if process.returncode != 0:
                if not self.quiet:
                    self.console.print(
                        f"[red]✗[/red] Task '{task_name}' failed with exit code {process.returncode}"
                    )
                raise TaskExecutionError(task_name, command, process.returncode)

            if not self.quiet:
                self.console.print(f"[green]✓[/green] Task '{task_name}' completed")

            return TaskResult(
                task_name=task_name,
                state=TaskState.COMPLETED,
                exit_code=0,
                stdout=process.stdout,
                stderr=process.stderr,
            )

        except subprocess.SubprocessError as exc:
            if not self.quiet:
                self.console.print(f"[red]✗[/red] Task '{task_name}' failed: {exc}")
            raise TaskExecutionError(task_name, command, -1) from exc
