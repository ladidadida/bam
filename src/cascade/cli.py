"""CLI entry point for cascade."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from ._version import __version__
from .cache import LocalCache, expand_globs
from .config import ConfigurationError, load_config
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


async def _run_task_async(
    task: str,
    dry_run: bool,
    quiet: bool,
    no_cache: bool,
    config: Path | None,
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
        return

    # Initialize cache
    cache = None if no_cache else LocalCache()

    # Execute tasks in dependency order
    executor = TaskExecutor(quiet=quiet, cache=cache)
    failed_tasks: list[str] = []

    for task_name in execution_order:
        task_config = loaded_config.tasks[task_name]

        # Resolve input and output paths
        input_paths = expand_globs(task_config.inputs) if task_config.inputs else []
        output_paths = [
            Path(p) for p in task_config.outputs
        ] if task_config.outputs else []

        try:
            await executor.execute_task(
                task_name=task_name,
                command=task_config.command,
                inputs=input_paths,
                outputs=output_paths,
                env=task_config.env,
            )
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
    asyncio.run(_run_task_async(task, dry_run, quiet, no_cache, config))


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
    total_size = sum(
        f.stat().st_size
        for f in cache.cache_dir.rglob("*")
        if f.is_file()
    )
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
        typer.secho("Invalid --format. Supported values: ascii, dot.", fg=typer.colors.RED, err=True)
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
