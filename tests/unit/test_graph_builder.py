"""Unit tests for task graph builder utilities."""

from __future__ import annotations

import pytest

from cscd.config.schema import TaskConfig
from cscd.graph import (
    CyclicDependencyError,
    MissingTaskError,
    build_task_graph,
    execution_order_for_targets,
    render_ascii_graph,
    render_dot_graph,
)


def test_build_task_graph_and_execution_order() -> None:
    """Build graph and return deterministic topological order."""
    tasks = {
        "build": TaskConfig(command="echo build", depends_on=["lint"]),
        "lint": TaskConfig(command="echo lint"),
        "test": TaskConfig(command="echo test", depends_on=["build"]),
    }

    graph = build_task_graph(tasks)

    assert list(graph.nodes) == ["build", "lint", "test"]
    assert execution_order_for_targets(graph, ["test"]) == ["lint", "build", "test"]


def test_build_task_graph_missing_dependency() -> None:
    """Raise a clear error when dependencies reference unknown task names."""
    tasks = {
        "test": TaskConfig(command="echo test", depends_on=["build"]),
    }

    with pytest.raises(MissingTaskError):
        build_task_graph(tasks)


def test_build_task_graph_cycle_detection() -> None:
    """Raise cycle error when graph is not a DAG."""
    tasks = {
        "a": TaskConfig(command="echo a", depends_on=["b"]),
        "b": TaskConfig(command="echo b", depends_on=["a"]),
    }

    with pytest.raises(CyclicDependencyError):
        build_task_graph(tasks)


def test_render_ascii_and_dot_graph() -> None:
    """Render deterministic ASCII and DOT graph output."""
    tasks = {
        "build": TaskConfig(command="echo build", depends_on=["lint"]),
        "lint": TaskConfig(command="echo lint"),
    }

    graph = build_task_graph(tasks)

    ascii_output = render_ascii_graph(graph)
    dot_output = render_dot_graph(graph)

    assert "Roots (no dependencies)" in ascii_output
    assert "lint" in ascii_output
    assert "build ← [lint]" in ascii_output
    assert '"lint" -> "build";' in dot_output
