"""CLI entry point for cascade."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ._version import __version__
from .config import ConfigurationError, load_config
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


@app.command("run")
def run_command(
    task: str,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show task execution plan without running commands."),
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
    if dry_run:
        try:
            _, loaded_config = load_config(config_path=config)
            graph = build_task_graph(loaded_config.tasks)
            execution_order = execution_order_for_targets(graph, [task])
        except (ConfigurationError, MissingTaskError, CyclicDependencyError) as exc:
            typer.secho(str(exc), fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1) from exc

        typer.secho("Dry-run execution order:", fg=typer.colors.CYAN)
        for index, task_name in enumerate(execution_order, start=1):
            typer.echo(f"{index}. {task_name}")
        return

    typer.echo(f"Running task: {task}")


@app.command("list")
def list_command() -> None:
    """List configured tasks."""
    typer.echo("No tasks discovered yet.")


@app.command("clean")
def clean_command(
    cache_dir: Annotated[Path, typer.Option("--cache-dir", help="Cache directory to clean.")] = Path(
        ".cascade/cache"
    ),
) -> None:
    """Clean local cache artifacts."""
    typer.echo(f"Cleaning cache directory: {cache_dir}")


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
