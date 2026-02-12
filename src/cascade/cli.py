"""CLI entry point for cascade."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Annotated

import networkx as nx
import typer

from ._version import __version__
from .cache import LocalCache, expand_globs
from .config import CascadeConfig, ConfigurationError, load_config
from .executor import TaskExecutionError, TaskExecutor
from .graph import (
    CyclicDependencyError,
    MissingTaskError,
    build_task_graph,
    execution_order_for_targets,
    render_ascii_graph,
    render_dot_graph,
)

app = typer.Typer(
    name="cascade",
    help=(
        "Flow naturally through your build pipeline 🌊\n\n"
        "Cascade is a content-addressed workflow orchestration tool that brings "
        "CAS-style caching to existing development workflows."
    ),
    no_args_is_help=True,
)


def version_callback(value: bool) -> None:
    """Print version and exit when requested."""
    if value:
        typer.echo(f"cascade {__version__}")
        raise typer.Exit()


@app.callback()
def common_options(
    _: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
) -> None:
    """Cascade command group."""


def _parse_jobs_value(jobs: str | None) -> int:
    """Parse --jobs flag value into max_workers count.

    Args:
        jobs: Either 'auto', an integer string, or None.

    Returns:
        Number of parallel workers (1 for sequential, >1 for parallel).
    """
    if jobs is None or jobs == "1":
        return 1

    if jobs.lower() == "auto":
        cpu_count = os.cpu_count() or 1
        # Use all CPUs but cap at reasonable limit
        return min(cpu_count, 8)

    try:
        max_workers = int(jobs)
        if max_workers < 1:
            raise ValueError("--jobs must be >= 1")
        return max_workers
    except ValueError as exc:
        raise typer.BadParameter(
            f"--jobs must be 'auto' or a positive integer, got: {jobs}"
        ) from exc


async def _execute_single_task(
    task_name: str,
    loaded_config: CascadeConfig,
    executor: TaskExecutor,
) -> None:
    """Execute a single task with its configuration.

    Args:
        task_name: Name of the task to execute.
        loaded_config: Loaded cascade configuration.
        executor: Task executor instance.

    Raises:
        TaskExecutionError: If task execution fails.
    """
    task_config = loaded_config.tasks[task_name]

    # Resolve input and output paths
    input_paths = expand_globs(task_config.inputs) if task_config.inputs else []
    output_paths = [Path(p) for p in task_config.outputs] if task_config.outputs else []

    await executor.execute_task(
        task_name=task_name,
        command=task_config.command,
        inputs=input_paths,
        outputs=output_paths,
        env=task_config.env,
    )


async def _execute_tasks_parallel(  # noqa: C901
    graph: nx.DiGraph,
    execution_order: list[str],
    loaded_config: CascadeConfig,
    executor: TaskExecutor,
    max_workers: int,
) -> list[str]:
    """Execute tasks in parallel respecting dependencies.

    Args:
        graph: Task dependency graph.
        execution_order: Topologically sorted task list.
        loaded_config: Loaded cascade configuration.
        executor: Task executor instance.
        max_workers: Maximum number of concurrent tasks.

    Returns:
        List of failed task names (empty if all succeeded).
    """
    completed: set[str] = set()
    failed: list[str] = []
    running: dict[str, asyncio.Task] = {}
    semaphore = asyncio.Semaphore(max_workers)

    # Track tasks remaining to execute
    remaining = set(execution_order)

    async def run_with_semaphore(task_name: str) -> tuple[str, bool]:
        """Run a task with semaphore limiting concurrency."""
        async with semaphore:
            try:
                await _execute_single_task(task_name, loaded_config, executor)
                return task_name, True
            except TaskExecutionError:
                return task_name, False

    def get_ready_tasks() -> list[str]:
        """Get tasks ready to execute (all dependencies completed)."""
        ready = []
        for task_name in remaining:
            # Check if all dependencies are completed
            deps = set(graph.predecessors(task_name))
            if deps.issubset(completed):
                ready.append(task_name)
        return ready

    # Main execution loop
    while remaining or running:
        # Start new tasks if workers available
        ready_tasks = get_ready_tasks()
        for task_name in ready_tasks:
            if task_name not in running:
                remaining.remove(task_name)
                task = asyncio.create_task(run_with_semaphore(task_name))
                running[task_name] = task

        if not running:
            # No tasks running and none ready - should not happen with valid graph
            break

        # Wait for at least one task to complete
        done, pending = await asyncio.wait(
            running.values(),
            return_when=asyncio.FIRST_COMPLETED,
        )

        # Process completed tasks
        for task in done:
            task_name, success = await task
            del running[task_name]

            if success:
                completed.add(task_name)
            else:
                failed.append(task_name)
                # Cancel remaining tasks on failure
                for pending_task in running.values():
                    pending_task.cancel()
                # Wait for cancellations
                await asyncio.gather(*running.values(), return_exceptions=True)
                return failed

    return failed


async def _run_task_async(
    task: str,
    dry_run: bool,
    quiet: bool,
    no_cache: bool,
    config: Path | None,
    max_workers: int = 1,
) -> None:
    """Internal async implementation of run command."""
    try:
        _, loaded_config = load_config(config_path=config)
        graph = build_task_graph(loaded_config.tasks)
        execution_order = execution_order_for_targets(graph, [task])
    except (ConfigurationError, MissingTaskError, CyclicDependencyError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if dry_run:
        typer.secho("Dry-run execution order:", fg=typer.colors.CYAN)
        for index, task_name in enumerate(execution_order, start=1):
            typer.echo(f"{index}. {task_name}")
        if max_workers > 1:
            typer.echo(f"\nParallel execution: {max_workers} workers")
        return

    # Initialize cache
    cache = None if no_cache else LocalCache()

    # Execute tasks
    executor = TaskExecutor(quiet=quiet, cache=cache)

    if max_workers > 1:
        # Parallel execution
        failed_tasks = await _execute_tasks_parallel(
            graph, execution_order, loaded_config, executor, max_workers
        )
    else:
        # Sequential execution
        failed_tasks = []
        for task_name in execution_order:
            try:
                await _execute_single_task(task_name, loaded_config, executor)
            except TaskExecutionError:
                failed_tasks.append(task_name)
                break

    if failed_tasks:
        typer.secho(
            f"\nExecution stopped due to task failure: {', '.join(failed_tasks)}",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)

    typer.secho(
        f"\n✓ Successfully executed {len(execution_order)} task(s)",
        fg=typer.colors.GREEN,
    )


@app.command("run")
def run_command(
    task: str,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show task execution plan without running commands."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress command output."),
    ] = False,
    no_cache: Annotated[
        bool,
        typer.Option("--no-cache", help="Disable caching (always run tasks)."),
    ] = False,
    jobs: Annotated[
        str | None,
        typer.Option(
            "--jobs",
            "-j",
            help="Number of parallel workers. Use 'auto' to detect CPU count, or specify a number (default: 1).",
        ),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=False,
            file_okay=True,
            dir_okay=False,
            help="Path to a cascade configuration file.",
        ),
    ] = None,
) -> None:
    """Run a task from cascade.yaml."""
    max_workers = _parse_jobs_value(jobs)
    asyncio.run(_run_task_async(task, dry_run, quiet, no_cache, config, max_workers))


@app.command("list")
def list_command(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=False,
            file_okay=True,
            dir_okay=False,
            help="Path to a cascade configuration file.",
        ),
    ] = None,
) -> None:
    """List configured tasks."""
    try:
        _, loaded_config = load_config(config_path=config)
    except ConfigurationError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if not loaded_config.tasks:
        typer.echo("No tasks configured.")
        return

    typer.secho("Available tasks:", fg=typer.colors.CYAN)
    for task_name, task_config in sorted(loaded_config.tasks.items()):
        typer.echo(f"  • {task_name}")
        if task_config.depends_on:
            typer.echo(f"    depends on: {', '.join(task_config.depends_on)}")


@app.command("clean")
def clean_command(
    cache_dir: Annotated[
        Path,
        typer.Option("--cache-dir", help="Cache directory to clean."),
    ] = Path(".cascade/cache"),
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt."),
    ] = False,
) -> None:
    """Clean local cache artifacts."""
    cache = LocalCache(cache_dir)

    if not cache.cache_dir.exists() or not list(cache.cache_dir.iterdir()):
        typer.echo("Cache is already empty.")
        return

    # Calculate cache size
    total_size = sum(f.stat().st_size for f in cache.cache_dir.rglob("*") if f.is_file())
    size_mb = total_size / (1024 * 1024)

    typer.secho(f"Cache directory: {cache.cache_dir}", fg=typer.colors.CYAN)
    typer.echo(f"Cache size: {size_mb:.2f} MB")

    if not force:
        confirmed = typer.confirm("Delete all cached artifacts?")
        if not confirmed:
            typer.echo("Aborted.")
            raise typer.Exit()

    cache.clear()
    typer.secho("✓ Cache cleared", fg=typer.colors.GREEN)


@app.command("graph")
def graph_command(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=False,
            file_okay=True,
            dir_okay=False,
            help="Path to a cascade configuration file.",
        ),
    ] = None,
    output_format: Annotated[
        str,
        typer.Option(
            "--format",
            help="Graph output format. 'ascii' shows tree view (default), 'dot' outputs Graphviz DOT format.",
        ),
    ] = "ascii",
) -> None:
    """Show task dependency graph with layers and connections."""
    normalized_format = output_format.lower().strip()
    if normalized_format not in {"ascii", "dot"}:
        typer.secho(
            "Invalid --format. Supported values: ascii, dot.", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)

    try:
        _, loaded_config = load_config(config_path=config)
        graph = build_task_graph(loaded_config.tasks)
    except (ConfigurationError, MissingTaskError, CyclicDependencyError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    if normalized_format == "dot":
        typer.echo(render_dot_graph(graph))
        return

    typer.echo(render_ascii_graph(graph))


@app.command("validate")
def validate_command(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=False,
            file_okay=True,
            dir_okay=False,
            help="Path to a cascade configuration file.",
        ),
    ] = None,
) -> None:
    """Validate configuration file and report task count."""
    try:
        config_path, loaded_config = load_config(config_path=config)
    except ConfigurationError as exc:
        typer.secho(str(exc), fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1) from exc

    typer.secho(f"Configuration is valid: {config_path}", fg=typer.colors.GREEN)
    typer.echo(f"Discovered {len(loaded_config.tasks)} task(s).")


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
