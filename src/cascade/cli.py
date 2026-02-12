"""CLI entry point for cascade."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ._version import __version__

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
def run_command(task: str) -> None:
    """Run a task from cascade.yaml."""
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
def graph_command() -> None:
    """Show task dependency graph."""
    typer.echo("Task graph is not implemented yet.")


def main() -> None:
    """Run the CLI application."""
    app()


if __name__ == "__main__":
    main()
