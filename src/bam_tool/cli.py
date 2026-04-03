"""CLI entry point for bam."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated

import networkx as nx
import typer
from rich.console import Console
from rich.live import Live
from rich.tree import Tree

from ._version import __version__
from .cache import LocalCache, create_cache, expand_globs
from .ci import generate_pipeline
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

app = typer.Typer(
    name="bam",
    no_args_is_help=False,
    context_settings={"allow_interspersed_args": True},
)

_SPINNER_FRAMES = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def version_callback(value: bool) -> None:
    """Print version and exit when requested."""
    if value:
        typer.echo(f"bam {__version__}")
        raise typer.Exit()


def _complete_task_name(incomplete: str) -> list[str]:
    """Return task names from bam.yaml that start with *incomplete*."""
    try:
        _, loaded_config = load_config()
        return [name for name in loaded_config.tasks if name.startswith(incomplete)]
    except Exception:  # noqa: BLE001
        return []


def _complete_stage_name(incomplete: str) -> list[str]:
    """Return stage names from bam.yaml that start with *incomplete*."""
    try:
        _, loaded_config = load_config()
        stages = {c.stage for c in loaded_config.tasks.values() if c.stage is not None}
        return [s for s in sorted(stages) if s.startswith(incomplete)]
    except Exception:  # noqa: BLE001
        return []


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


def _format_task_label(
    task_name: str,
    state: str,
    progress: int,
    nesting: int = 0,
    name_col: int = 24,
    start_time_mono: float | None = None,
) -> str:
    """Format a task label with icon, name, progress bar, and percentage.

    Args:
        task_name: Name of the task.
        state: Task state (pending, running, completed, failed).
        progress: Task progress percentage (0-100).
        nesting: Rich tree nesting depth (0 = direct child of root). Each level
            adds 4 chars of tree-connector prefix, so we subtract 4 per level
            from the name width to keep the bar column fixed.
        name_col: Total name-column width allocated at nesting 0. Shared across
            all labels in the tree so bars always start at the same column.
        start_time_mono: ``time.monotonic()`` value recorded when the task
            started running; used to display elapsed seconds.

    Returns:
        Formatted label string with Rich markup.
    """
    # Rich adds 4 chars of guide prefix per nesting level (├── / │   └── etc.).
    # Subtract the same amount from the name field so bars stay at one column.
    name_width = max(8, name_col - 4 * nesting)

    if state == "completed":
        icon = "[green]✓[/]"
        bar = "━" * 30
        return f"{icon} {task_name:{name_width}} {bar} 100%"
    elif state == "cached":
        icon = "[dim green]↩[/]"
        bar = "━" * 30
        return f"{icon} {task_name:{name_width}} {bar} [dim]cached[/]"
    elif state == "failed":
        icon = "[red]✗[/]"
        bar = "━" * 30
        return f"{icon} {task_name:{name_width}} {bar} {progress:3}%"
    elif state == "running":
        spinner_char = _SPINNER_FRAMES[int(time.monotonic() * 8) % len(_SPINNER_FRAMES)]
        elapsed = int(time.monotonic() - start_time_mono) if start_time_mono is not None else 0
        elapsed_str = f"[dim]{elapsed:3}s[/dim]"
        bar = "╸" + " " * 29
        return f"[cyan]{spinner_char}[/] {task_name:{name_width}} {elapsed_str} {bar}"
    else:  # pending
        bar = " " * 30
        return f"[dim]○ {task_name:{name_width}} {bar}   0%[/]"


def _measure_task_nestings(
    graph: nx.DiGraph,
    task_set: set[str],
    execution_order: list[str],
    roots: list[str],
    root_start_nesting: int,
) -> dict[str, int]:
    """DFS pre-pass: return the nesting depth for each task in task_set."""
    task_nesting: dict[str, int] = {}
    seen: set[str] = set()

    def _visit(task_name: str, nesting: int) -> None:
        if task_name in seen:
            return
        seen.add(task_name)
        task_nesting[task_name] = nesting
        for pred in sorted(
            (p for p in graph.predecessors(task_name) if p in task_set),
            key=execution_order.index,
        ):
            _visit(pred, nesting + 1)

    for root in roots:
        _visit(root, root_start_nesting)
    for task_name in execution_order:  # safety net for disconnected nodes
        if task_name not in task_nesting:
            task_nesting[task_name] = 0
    return task_nesting


def _add_dep_children(
    rich_node: Tree,
    task_name: str,
    nesting: int,
    graph: nx.DiGraph,
    task_set: set[str],
    execution_order: list[str],
    task_states: dict[str, str],
    task_progress: dict[str, int],
    visited: set[str],
    name_col: int,
    task_start_times: dict[str, float] | None = None,
) -> None:
    """Recursively add dependency children of task_name to a Rich Tree node."""
    for pred in sorted(
        (p for p in graph.predecessors(task_name) if p in task_set),
        key=execution_order.index,
    ):
        if pred not in visited:
            visited.add(pred)
            state = task_states.get(pred, "pending")
            progress = task_progress.get(pred, 0)
            start_time = task_start_times.get(pred) if task_start_times else None
            child = rich_node.add(
                _format_task_label(pred, state, progress, nesting, name_col, start_time)
            )
            _add_dep_children(
                child,
                pred,
                nesting + 1,
                graph,
                task_set,
                execution_order,
                task_states,
                task_progress,
                visited,
                name_col,
                task_start_times,
            )


def _build_task_tree(
    graph: nx.DiGraph,
    execution_order: list[str],
    task_states: dict[str, str],
    task_progress: dict[str, int],
    target_tasks: list[str] | None = None,
    task_start_times: dict[str, float] | None = None,
) -> Tree:
    """Build a Rich tree rooted at the target task(s) with dependencies as children.

    The tree is shown top-down: the explicitly requested task(s) appear at the
    root, and each task's dependencies fan out beneath it.  When a dependency
    is shared by multiple parents it is attached to the first parent visited
    (DFS, topo order) and skipped in subsequent visits so every task appears
    exactly once.

    The name-column width is computed adaptively from the longest
    ``4*nesting + len(task_name)`` value in the current task set, padded by 2
    and capped at half the terminal width.  All labels share the same
    ``name_col`` value so bars always start at the same column.

    Args:
        graph: Task dependency graph.
        execution_order: Topologically sorted task list (used for stable ordering).
        task_states: Task states (pending, running, completed, failed).
        task_progress: Task progress percentages (0-100).
        target_tasks: Explicitly requested tasks.  They form the tree root(s).
            Falls back to tasks with no successors in the execution set.
        task_start_times: Mapping of task name to ``time.monotonic()`` start
            time, used to display per-task elapsed seconds for running tasks.

    Returns:
        Rich Tree object rooted at the target task(s).
    """
    task_set = set(execution_order)

    # Determine root tasks (what the user explicitly asked to run).
    roots = target_tasks or [
        t for t in execution_order if not any(s in task_set for s in graph.successors(t))
    ]
    root_start_nesting = 0 if len(roots) == 1 else 1

    # Pre-pass: collect nesting depth of every task, then derive column width.
    task_nesting = _measure_task_nestings(
        graph, task_set, execution_order, roots, root_start_nesting
    )
    terminal_cols = shutil.get_terminal_size((80, 24)).columns
    max_effective = max(4 * n + len(name) for name, n in task_nesting.items())
    name_col = max(min(max_effective + 2, terminal_cols // 2), 8)

    # Build tree.
    visited: set[str] = set()

    def _add(node: Tree, task: str, nest: int) -> None:
        _add_dep_children(
            node,
            task,
            nest,
            graph,
            task_set,
            execution_order,
            task_states,
            task_progress,
            visited,
            name_col,
            task_start_times,
        )

    if len(roots) == 1:
        root_task = roots[0]
        visited.add(root_task)
        state = task_states.get(root_task, "pending")
        progress = task_progress.get(root_task, 0)
        start_time = task_start_times.get(root_task) if task_start_times else None
        tree = Tree(_format_task_label(root_task, state, progress, 0, name_col, start_time))
        _add(tree, root_task, 1)
    else:
        tree = Tree("📦 Tasks")
        for root_task in roots:
            if root_task not in visited:
                visited.add(root_task)
                state = task_states.get(root_task, "pending")
                progress = task_progress.get(root_task, 0)
                start_time = task_start_times.get(root_task) if task_start_times else None
                child = tree.add(
                    _format_task_label(root_task, state, progress, 1, name_col, start_time)
                )
                _add(child, root_task, 2)

    # Safety net: disconnected tasks not reached by DFS above.
    for task_name in execution_order:
        if task_name not in visited:
            state = task_states.get(task_name, "pending")
            progress = task_progress.get(task_name, 0)
            start_time = task_start_times.get(task_name) if task_start_times else None
            tree.add(_format_task_label(task_name, state, progress, 0, name_col, start_time))
    return tree


async def _execute_single_task(
    task_name: str,
    loaded_config: BamConfig,
    executor: TaskExecutor,
    timeout: float | None = None,
    on_timeout: Callable[[], Awaitable[bool]] | None = None,
) -> bool:
    """Execute a single task with its configuration.

    Args:
        task_name: Name of the task to execute.
        loaded_config: Loaded bam configuration.
        executor: Task executor instance.
        timeout: Optional timeout in seconds; None means no timeout.
        on_timeout: Async callback invoked on each timeout expiry.  Returns
            ``True`` to abort the task, ``False`` to reset the timer and
            continue waiting.  When ``None`` the task is aborted immediately.

    Raises:
        TaskExecutionError: If task execution fails.
    """
    task_config = loaded_config.tasks[task_name]

    # Resolve input and output paths
    input_paths = expand_globs(task_config.inputs) if task_config.inputs else []
    output_paths = [Path(p) for p in task_config.outputs] if task_config.outputs else []

    result = await executor.execute_task(
        task_name=task_name,
        command=task_config.command,
        inputs=input_paths,
        outputs=output_paths,
        env=task_config.env,
        runner=task_config.runner,
        timeout=timeout,
        on_timeout=on_timeout,
    )
    return result.cache_hit


async def _execute_tasks_parallel(  # noqa: C901
    graph: nx.DiGraph,
    execution_order: list[str],
    loaded_config: BamConfig,
    executor: TaskExecutor,
    max_workers: int,
    use_rich: bool = False,
    target_tasks: list[str] | None = None,
    is_interactive: bool = False,
) -> tuple[list[str], list[str], dict[str, tuple[str, str]]]:  # noqa: C901
    """Execute tasks in parallel respecting dependencies.

    Args:
        graph: Task dependency graph.
        execution_order: Topologically sorted task list.
        loaded_config: Loaded bam configuration.
        executor: Task executor instance.
        max_workers: Maximum number of concurrent tasks.
        use_rich: Whether to use rich progress display.
        target_tasks: Explicitly requested tasks (used to root the progress tree).
        is_interactive: Whether to show interactive timeout prompts.

    Returns:
        Tuple of (failed_tasks, skipped_tasks, failed_outputs) where
        failed_outputs maps task name to (stdout, stderr) captured during failure.
    """
    completed: set[str] = set()
    failed: list[str] = []
    running: dict[str, asyncio.Task] = {}
    semaphore = asyncio.Semaphore(max_workers)
    failed_outputs: dict[str, tuple[str, str]] = {}

    # Track tasks remaining to execute
    remaining = set(execution_order)

    # Task state tracking for tree view
    task_states: dict[str, str] = {task: "pending" for task in execution_order}
    task_progress_pct: dict[str, int] = {task: 0 for task in execution_order}
    task_start_times: dict[str, float] = {}
    console = Console()

    # Mutable ref so run_with_semaphore can access the Live object for timeout prompts
    _live_ref: list[Live] = []

    async def run_with_semaphore(task_name: str) -> tuple[str, bool]:
        """Run a task with semaphore limiting concurrency."""
        task_config = loaded_config.tasks[task_name]
        task_timeout = float(task_config.timeout) if task_config.timeout else None

        # Build timeout callback for interactive mode
        on_timeout: Callable[[], Awaitable[bool]] | None = None
        if task_timeout is not None and is_interactive:
            _name = task_name  # explicit capture for the closure
            _secs = task_timeout

            async def _prompt_timeout() -> bool:
                live = _live_ref[0] if _live_ref else None
                if live:
                    live.stop()
                try:
                    loop = asyncio.get_event_loop()
                    return await loop.run_in_executor(
                        None,
                        lambda: (
                            not typer.confirm(
                                f"\n⏱  '{_name}' has been running for {int(_secs)}s."
                                " Continue waiting?",
                                default=True,
                            )
                        ),
                    )
                finally:
                    if live:
                        live.start(refresh=True)

            on_timeout = _prompt_timeout

        async with semaphore:
            # Update state when starting
            task_states[task_name] = "running"
            task_progress_pct[task_name] = 0
            task_start_times[task_name] = time.monotonic()

            try:
                cache_hit = await _execute_single_task(
                    task_name,
                    loaded_config,
                    executor,
                    timeout=task_timeout,
                    on_timeout=on_timeout,
                )
                # Mark as completed or cached
                task_states[task_name] = "cached" if cache_hit else "completed"
                task_progress_pct[task_name] = 100
                return task_name, True
            except TaskExecutionError as exc:
                # Mark as failed and preserve captured output for error display
                task_states[task_name] = "failed"
                task_progress_pct[task_name] = 100
                failed_outputs[task_name] = (exc.stdout, exc.stderr)
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

    async def execute_loop() -> tuple[list[str], list[str], dict[str, tuple[str, str]]]:
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
                    return failed, skipped, failed_outputs

        return failed, [], failed_outputs

    # Execute with or without rich tree display
    if use_rich:
        # Use Live display with tree view
        async def execute_with_tree() -> tuple[list[str], list[str], dict[str, tuple[str, str]]]:
            tree = _build_task_tree(
                graph,
                execution_order,
                task_states,
                task_progress_pct,
                target_tasks,
                task_start_times,
            )
            with Live(tree, console=console, refresh_per_second=4) as live:
                _live_ref.append(live)
                # Start execution
                loop_task = asyncio.create_task(execute_loop())

                # Update tree periodically
                while not loop_task.done():
                    tree = _build_task_tree(
                        graph,
                        execution_order,
                        task_states,
                        task_progress_pct,
                        target_tasks,
                        task_start_times,
                    )
                    live.update(tree)
                    await asyncio.sleep(0.25)

                # Final update
                result = await loop_task
                tree = _build_task_tree(
                    graph,
                    execution_order,
                    task_states,
                    task_progress_pct,
                    target_tasks,
                    task_start_times,
                )
                live.update(tree)
                _live_ref.clear()
                return result

        return await execute_with_tree()
    else:
        return await execute_loop()


def _display_failed_task_details(
    graph: nx.DiGraph,
    failed_task: str,
    outputs: dict[str, tuple[str, str]],
) -> None:
    """Print captured output and dependency chain for one failed task."""
    typer.secho(f"✗ Task failed: {failed_task}", fg=typer.colors.RED, err=True)

    stdout, stderr = outputs.get(failed_task, ("", ""))
    if stdout or stderr:
        typer.secho("  Output:", fg=typer.colors.YELLOW, err=True)
        for line in stdout.splitlines():
            typer.echo(f"  {line}", err=True)
        for line in stderr.splitlines():
            typer.secho(f"  {line}", fg=typer.colors.RED, err=True)

    dep_chain = _get_dependency_chain(graph, failed_task)
    if len(dep_chain) > 1:
        typer.secho("  Dependency chain:", fg=typer.colors.YELLOW, err=True)
        for i, dep in enumerate(dep_chain):
            prefix = "    └─" if i == len(dep_chain) - 1 else "    ├─"
            typer.echo(f"{prefix} {dep}", err=True)


def _display_execution_errors(
    graph: nx.DiGraph,
    failed_tasks: list[str],
    skipped_tasks: list[str],
    failed_outputs: dict[str, tuple[str, str]] | None = None,
) -> None:
    """Display detailed error information for failed tasks.

    Replays the captured stdout/stderr of each failed task so the user always
    sees the full tool output regardless of whether rich/quiet mode was active
    during execution.

    Args:
        graph: Task dependency graph.
        failed_tasks: List of failed task names.
        skipped_tasks: List of skipped task names.
        failed_outputs: Captured (stdout, stderr) per failed task name.
    """
    outputs = failed_outputs or {}
    typer.echo()
    for failed_task in failed_tasks:
        _display_failed_task_details(graph, failed_task, outputs)

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
    task: str | None,
    stage: str | None,
    dry_run: bool,
    quiet: bool,
    no_cache: bool,
    config: Path | None,
    max_workers: int = 1,
    plain: bool = False,
) -> None:
    """Internal async implementation of run command.

    Args:
        task: Target task or stage name to execute.  When a stage name is given
            (not matching any task directly), all tasks belonging to that stage
            are executed.
        stage: Explicit stage name (from --stage/-s).  When provided, all tasks
            belonging to this stage are executed regardless of task names.
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
        if stage is not None:
            # Explicit --stage flag: run all tasks belonging to this stage.
            stage_tasks = [n for n, c in loaded_config.tasks.items() if c.stage == stage]
            if not stage_tasks:
                typer.secho(f"No tasks found in stage '{stage}'.", fg=typer.colors.RED, err=True)
                raise typer.Exit(code=1)
            targets = stage_tasks
        elif task is not None:
            # Resolve stage name → list of task names when the target is not a
            # direct task name.  Task names always take precedence.
            if task not in loaded_config.tasks:
                stage_tasks = [n for n, c in loaded_config.tasks.items() if c.stage == task]
                targets = stage_tasks if stage_tasks else [task]
            else:
                targets = [task]
        else:
            targets = []
        execution_order = execution_order_for_targets(graph, targets)
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
    failed_tasks, skipped_tasks, failed_outputs = await _execute_tasks_parallel(
        graph,
        execution_order,
        loaded_config,
        executor,
        max_workers,
        use_rich_progress,
        target_tasks=targets,
        is_interactive=is_interactive,
    )

    if failed_tasks:
        # Display detailed error information
        _display_execution_errors(graph, failed_tasks, skipped_tasks, failed_outputs)
        raise typer.Exit(code=1)

    typer.secho(
        f"\n✓ Successfully executed {len(execution_order)} task(s)",
        fg=typer.colors.GREEN,
    )


@app.callback(invoke_without_command=True)
def _main_callback(  # noqa: C901, PLR0912, PLR0913, PLR0915
    ctx: typer.Context,
    task: Annotated[
        str | None,
        typer.Argument(autocompletion=_complete_task_name, help="Task or stage to run."),
    ] = None,
    # ── Info ──────────────────────────────────────────────────────────────
    _version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit.",
        ),
    ] = None,
    # ── Management flags ──────────────────────────────────────────────────
    list_tasks: Annotated[
        bool,
        typer.Option("--list", help="List available tasks and exit."),
    ] = False,
    validate: Annotated[
        bool,
        typer.Option("--validate", help="Validate config and report task count."),
    ] = False,
    graph: Annotated[
        bool,
        typer.Option("--graph", help="Show ASCII dependency graph and exit."),
    ] = False,
    graph_dot: Annotated[
        bool,
        typer.Option("--graph-dot", help="Show DOT dependency graph and exit."),
    ] = False,
    clean: Annotated[
        bool,
        typer.Option("--clean", help="Clean local cache artifacts (prompts for confirmation)."),
    ] = False,
    clean_force: Annotated[
        bool,
        typer.Option("--clean-force", help="Clean local cache without confirmation."),
    ] = False,
    cache_dir: Annotated[
        Path,
        typer.Option(
            "--cache-dir", help="Cache directory path (used with --clean / --clean-force)."
        ),
    ] = Path(".bam/cache"),
    ci: Annotated[
        bool,
        typer.Option("--ci", help="Generate CI pipeline file and exit."),
    ] = False,
    ci_output: Annotated[
        Path | None,
        typer.Option(
            "--ci-output", help="Write CI pipeline to this path (default: provider-specific)."
        ),
    ] = None,
    ci_dry_run: Annotated[
        bool,
        typer.Option("--ci-dry-run", help="Print CI YAML to stdout without writing a file."),
    ] = False,
    # ── Task run options ──────────────────────────────────────────────────
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
        typer.Option("--jobs", "-j", help="Parallel workers: 'auto' or a number (default: auto)."),
    ] = None,
    plain: Annotated[
        bool,
        typer.Option("--plain", help="Use plain output mode (auto-detected for non-TTY)."),
    ] = False,
    stage: Annotated[
        str | None,
        typer.Option(
            "--stage",
            "-s",
            autocompletion=_complete_stage_name,
            help="Run all tasks belonging to this stage.",
        ),
    ] = None,
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Path to a bam configuration file."),
    ] = None,
) -> None:
    """Fast builds, no fluff.

    bam is a content-addressed workflow orchestration tool that brings
    CAS-style caching to existing development workflows.

    Run a task:    bam <task>\n
    Run a stage:   bam --stage <stage>\n
    List tasks:    bam --list\n
    Show graph:    bam --graph\n
    Validate:      bam --validate\n
    Generate CI:   bam --ci\n
    Clean cache:  bam --clean
    """
    # ── --list ────────────────────────────────────────────────────────────
    if list_tasks:
        try:
            _, loaded_config = load_config(config_path=config)
        except ConfigurationError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        if not loaded_config.tasks:
            typer.echo("No tasks configured.")
            return
        typer.secho("Available tasks:", fg=typer.colors.CYAN)
        for name, cfg in sorted(loaded_config.tasks.items()):
            typer.echo(f"  • {name}")
            if cfg.depends_on:
                typer.echo(f"    depends on: {', '.join(cfg.depends_on)}")
        return

    # ── --validate ────────────────────────────────────────────────────────
    if validate:
        try:
            config_path, loaded_config = load_config(config_path=config)
        except ConfigurationError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        typer.secho(f"Configuration is valid: {config_path}", fg=typer.colors.GREEN)
        typer.echo(f"Discovered {len(loaded_config.tasks)} task(s).")
        return

    # ── --graph / --graph-dot ─────────────────────────────────────────────
    if graph or graph_dot:
        try:
            _, loaded_config = load_config(config_path=config)
            g = build_task_graph(loaded_config.tasks)
        except (ConfigurationError, MissingTaskError, CyclicDependencyError) as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        if graph_dot:
            typer.echo(render_dot_graph(g))
        else:
            typer.echo(render_ascii_graph(g))
        return

    # ── --clean / --clean-force ───────────────────────────────────────────
    if clean or clean_force:
        cache_obj = LocalCache(cache_dir)
        if not cache_obj.cache_dir.exists() or not list(cache_obj.cache_dir.iterdir()):
            typer.echo("Cache is already empty.")
            return
        total_size = sum(f.stat().st_size for f in cache_obj.cache_dir.rglob("*") if f.is_file())
        size_mb = total_size / (1024 * 1024)
        typer.secho(f"Cache directory: {cache_obj.cache_dir}", fg=typer.colors.CYAN)
        typer.echo(f"Cache size: {size_mb:.2f} MB")
        if not clean_force:
            confirmed = typer.confirm("Delete all cached artifacts?")
            if not confirmed:
                typer.echo("Aborted.")
                return
        asyncio.run(cache_obj.clear())
        typer.secho("✓ Cache cleared", fg=typer.colors.GREEN)
        return

    # ── --ci / --ci-dry-run / --ci-output ─────────────────────────────────
    if ci or ci_dry_run or ci_output is not None:
        try:
            _, loaded_config = load_config(config_path=config)
        except ConfigurationError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        try:
            default_path, content = generate_pipeline(loaded_config)
        except ValueError as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc
        if ci_dry_run:
            typer.echo(content)
            return
        out_path = Path(ci_output) if ci_output else Path(default_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content)
        typer.secho(f"✓ Generated {out_path}", fg=typer.colors.GREEN)
        return

    # ── task / stage execution ─────────────────────────────────────────────
    if task and stage:
        typer.secho(
            "Cannot specify both a task argument and --stage.", fg=typer.colors.RED, err=True
        )
        raise typer.Exit(code=1)
    if task or stage:
        max_workers = _parse_jobs_value(jobs)
        use_plain = plain or not sys.stdout.isatty()
        asyncio.run(
            _run_task_async(task, stage, dry_run, quiet, no_cache, config, max_workers, use_plain)
        )
        return

    # No task and no management flag: show help.
    typer.echo(ctx.get_help())
    raise typer.Exit(code=0)


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
