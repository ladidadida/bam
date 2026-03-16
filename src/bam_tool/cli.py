"""CLI entry point for bam."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Annotated

import click
import networkx as nx
import typer
from rich.console import Console
from rich.live import Live
from rich.tree import Tree
from typer.core import TyperGroup

from ._version import __version__
from .cache import LocalCache, create_cache, expand_globs
from .config import BamConfig, ConfigurationError, load_config
from .executor import TaskExecutionError, TaskExecutor
from .graph import (
    CyclicDependencyError,
    MissingTaskError,
    build_task_graph,
    execution_order_for_targets,
    render_ascii_graph,
    render_dot_graph,
)


class DefaultCommandGroup(TyperGroup):
    """Typer group that falls back to 'run <token>' for unknown first tokens.

    Allows `bam <task>` as shorthand for `bam run <task>`.
    """

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        # list_commands() uses TyperGroup's lazy registry, unlike self.commands
        # which is the underlying click.Group dict and is always empty.
        if args and not args[0].startswith("-") and args[0] not in self.list_commands(ctx):
            args = ["run", *args]
        return super().parse_args(ctx, args)


app = typer.Typer(
    name="bam",
    help=(
        "Flow naturally through your build pipeline 🌊\n\n"
        "bam is a content-addressed workflow orchestration tool that brings "
        "CAS-style caching to existing development workflows. Companion to cascache."
    ),
    no_args_is_help=True,
    cls=DefaultCommandGroup,
)


def version_callback(value: bool) -> None:
    """Print version and exit when requested."""
    if value:
        typer.echo(f"bam {__version__}")
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def common_options(
    ctx: typer.Context,
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
    """Bam command group."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit(code=0)


def _parse_jobs_value(jobs: str | None) -> int:
    """Parse --jobs flag value into max_workers count.

    Args:
        jobs: Either 'auto', an integer string, or None (defaults to 'auto').

    Returns:
        Number of parallel workers (1 for sequential, >1 for parallel).
    """
    # Default to auto if not specified
    if jobs is None:
        jobs = "auto"

    if jobs == "1":
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


def _get_dependency_chain(graph: nx.DiGraph, task_name: str) -> list[str]:
    """Get the dependency chain leading to a task.

    Args:
        graph: Task dependency graph.
        task_name: Name of the task.

    Returns:
        List of task names in dependency order (roots first, task last).
    """
    # Get all ancestors (transitive dependencies)
    ancestors = nx.ancestors(graph, task_name)
    # Create subgraph with task and its dependencies
    subgraph = graph.subgraph(ancestors | {task_name})
    # Topologically sort to get dependency order
    try:
        return list(nx.topological_sort(subgraph))  # type: ignore[call-overload]
    except nx.NetworkXError:
        # Fallback if there's an issue
        return [task_name]


def _format_task_label(task_name: str, state: str, progress: int) -> str:
    """Format a task label with icon, name, progress bar, and percentage.

    Args:
        task_name: Name of the task.
        state: Task state (pending, running, completed, failed).
        progress: Task progress percentage (0-100).

    Returns:
        Formatted label string with Rich markup.
    """
    if state == "completed":
        icon = "[green]✓[/]"
        bar = "━" * 30
        return f"{icon} {task_name:20} {bar} 100%"
    elif state == "failed":
        icon = "[red]✗[/]"
        bar = "━" * 30
        return f"{icon} {task_name:20} {bar} {progress:3}%"
    elif state == "running":
        filled = int(progress * 30 / 100)
        bar = "━" * filled + "╸" + " " * (29 - filled)
        return f"[cyan]⠿[/] {task_name:20} {bar} {progress:3}%"
    else:  # pending
        bar = " " * 30
        return f"[dim]○ {task_name:20} {bar}   0%[/]"


def _build_task_tree(
    graph: nx.DiGraph,
    execution_order: list[str],
    task_states: dict[str, str],
    task_progress: dict[str, int],
) -> Tree:
    """Build a tree visualization of task dependencies with status.

    Args:
        graph: Task dependency graph.
        execution_order: Topologically sorted task list.
        task_states: Task states (pending, running, completed, failed).
        task_progress: Task progress percentages (0-100).

    Returns:
        Rich Tree object representing the task hierarchy.
    """
    # Find root tasks (tasks with no dependencies)
    root_tasks = [t for t in execution_order if graph.in_degree(t) == 0]

    tree = Tree("📦 Tasks")
    added_tasks: set[str] = set()

    def add_task_to_tree(task_name: str, parent_node: Tree) -> None:
        """Recursively add a task and its dependents to the tree."""
        if task_name in added_tasks:
            return
        added_tasks.add(task_name)

        # Format task label based on current state
        state = task_states.get(task_name, "pending")
        progress = task_progress.get(task_name, 0)
        label = _format_task_label(task_name, state, progress)

        node = parent_node.add(label)

        # Add dependents (tasks that depend on this one)
        for successor in graph.successors(task_name):
            if successor in execution_order:
                add_task_to_tree(successor, node)

    # Add root tasks and their dependencies
    for root_task in root_tasks:
        add_task_to_tree(root_task, tree)

    # Add any remaining tasks that weren't added (shouldn't happen with valid graph)
    for task_name in execution_order:
        if task_name not in added_tasks:
            add_task_to_tree(task_name, tree)

    return tree


async def _execute_single_task(
    task_name: str,
    loaded_config: BamConfig,
    executor: TaskExecutor,
) -> None:
    """Execute a single task with its configuration.

    Args:
        task_name: Name of the task to execute.
        loaded_config: Loaded bam configuration.
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
    loaded_config: BamConfig,
    executor: TaskExecutor,
    max_workers: int,
    use_rich: bool = False,
) -> tuple[list[str], list[str]]:
    """Execute tasks in parallel respecting dependencies.

    Args:
        graph: Task dependency graph.
        execution_order: Topologically sorted task list.
        loaded_config: Loaded bam configuration.
        executor: Task executor instance.
        max_workers: Maximum number of concurrent tasks.
        use_rich: Whether to use rich progress display.

    Returns:
        Tuple of (failed_tasks, skipped_tasks).
    """
    completed: set[str] = set()
    failed: list[str] = []
    running: dict[str, asyncio.Task] = {}
    semaphore = asyncio.Semaphore(max_workers)

    # Track tasks remaining to execute
    remaining = set(execution_order)

    # Task state tracking for tree view
    task_states: dict[str, str] = {task: "pending" for task in execution_order}
    task_progress_pct: dict[str, int] = {task: 0 for task in execution_order}
    console = Console()

    async def run_with_semaphore(task_name: str) -> tuple[str, bool]:
        """Run a task with semaphore limiting concurrency."""
        async with semaphore:
            # Update state when starting
            task_states[task_name] = "running"
            task_progress_pct[task_name] = 0

            try:
                await _execute_single_task(task_name, loaded_config, executor)
                # Mark as completed
                task_states[task_name] = "completed"
                task_progress_pct[task_name] = 100
                return task_name, True
            except TaskExecutionError:
                # Mark as failed
                task_states[task_name] = "failed"
                task_progress_pct[task_name] = 100
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

    async def execute_loop() -> tuple[list[str], list[str]]:
        """Main execution loop."""
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
                    # Skipped tasks are those that were never started
                    skipped = list(remaining)
                    # Cancel remaining tasks on failure
                    for pending_task in running.values():
                        pending_task.cancel()
                    # Wait for cancellations
                    await asyncio.gather(*running.values(), return_exceptions=True)
                    return failed, skipped

        return failed, []

    # Execute with or without rich tree display
    if use_rich:
        # Use Live display with tree view
        async def execute_with_tree() -> tuple[list[str], list[str]]:
            tree = _build_task_tree(graph, execution_order, task_states, task_progress_pct)
            with Live(tree, console=console, refresh_per_second=4) as live:
                # Start execution
                loop_task = asyncio.create_task(execute_loop())

                # Update tree periodically
                while not loop_task.done():
                    tree = _build_task_tree(graph, execution_order, task_states, task_progress_pct)
                    live.update(tree)
                    await asyncio.sleep(0.25)

                # Final update
                result = await loop_task
                tree = _build_task_tree(graph, execution_order, task_states, task_progress_pct)
                live.update(tree)
                return result

        return await execute_with_tree()
    else:
        return await execute_loop()


def _display_execution_errors(
    graph: nx.DiGraph,
    failed_tasks: list[str],
    skipped_tasks: list[str],
) -> None:
    """Display detailed error information for failed tasks.

    Args:
        graph: Task dependency graph.
        failed_tasks: List of failed task names.
        skipped_tasks: List of skipped task names.
    """
    typer.echo()
    for failed_task in failed_tasks:
        typer.secho(f"✗ Task failed: {failed_task}", fg=typer.colors.RED, err=True)

        # Show dependency chain
        dep_chain = _get_dependency_chain(graph, failed_task)
        if len(dep_chain) > 1:
            typer.secho("  Dependency chain:", fg=typer.colors.YELLOW, err=True)
            for i, dep in enumerate(dep_chain):
                prefix = "    └─" if i == len(dep_chain) - 1 else "    ├─"
                typer.echo(f"{prefix} {dep}", err=True)

    # Show skipped tasks if any
    if skipped_tasks:
        typer.echo()
        typer.secho(
            f"⊘ Skipped {len(skipped_tasks)} task(s) due to failure:",
            fg=typer.colors.YELLOW,
            err=True,
        )
        for skipped in skipped_tasks:
            typer.echo(f"  • {skipped}", err=True)


async def _run_task_async(
    task: str,
    dry_run: bool,
    quiet: bool,
    no_cache: bool,
    config: Path | None,
    max_workers: int = 1,
    plain: bool = False,
) -> None:
    """Internal async implementation of run command.

    Args:
        task: Target task to execute.
        dry_run: Show execution plan without running.
        quiet: Suppress output.
        no_cache: Disable caching.
        config: Path to config file.
        max_workers: Number of parallel workers.
        plain: Use plain output mode (buffered for parallel).
    """
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
    cache = None if no_cache else create_cache(loaded_config.cache)

    # Determine display mode
    is_interactive = sys.stdout.isatty() and not plain
    # Use rich progress by default in interactive mode
    use_rich_progress = is_interactive
    # Buffer output only in parallel plain mode
    use_buffered = max_workers > 1 and not use_rich_progress
    # Quiet mode when using rich progress (progress display handles feedback)
    use_quiet = quiet or use_rich_progress

    # Execute tasks
    executor = TaskExecutor(quiet=use_quiet, cache=cache, buffer_output=use_buffered)

    # Use parallel execution path for both sequential and parallel
    # (provides tree view and better progress tracking)
    failed_tasks, skipped_tasks = await _execute_tasks_parallel(
        graph, execution_order, loaded_config, executor, max_workers, use_rich_progress
    )

    if failed_tasks:
        # Display detailed error information
        _display_execution_errors(graph, failed_tasks, skipped_tasks)
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
            help="Number of parallel workers. Use 'auto' to detect CPU count, or specify a number (default: auto).",
        ),
    ] = None,
    plain: Annotated[
        bool,
        typer.Option(
            "--plain",
            help="Use plain output mode with task sections (auto-detected for non-TTY).",
        ),
    ] = False,
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=False,
            file_okay=True,
            dir_okay=False,
            help="Path to a bam configuration file.",
        ),
    ] = None,
) -> None:
    """Run a task from bam.yaml."""
    max_workers = _parse_jobs_value(jobs)

    # Auto-detect plain mode if not explicitly set
    use_plain = plain or not sys.stdout.isatty()

    asyncio.run(_run_task_async(task, dry_run, quiet, no_cache, config, max_workers, use_plain))


@app.command("list")
def list_command(
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            exists=False,
            file_okay=True,
            dir_okay=False,
            help="Path to a bam configuration file.",
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
    ] = Path(".bam/cache"),
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

    asyncio.run(cache.clear())
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
            help="Path to a bam configuration file.",
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
            help="Path to a bam configuration file.",
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
