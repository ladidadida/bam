"""Dependency graph construction and visualization helpers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

import networkx as nx

from cscd.config.schema import TaskConfig


class MissingTaskError(Exception):
    """Raised when a task references an undefined dependency."""


class CyclicDependencyError(Exception):
    """Raised when a task graph contains dependency cycles."""


def build_task_graph(tasks: Mapping[str, TaskConfig]) -> nx.DiGraph:
    """Create a directed graph with edges from dependency -> task."""
    graph: nx.DiGraph = nx.DiGraph()

    for task_name in sorted(tasks):
        graph.add_node(task_name)

    for task_name in sorted(tasks):
        task_config = tasks[task_name]
        for dependency in sorted(task_config.depends_on):
            if dependency not in tasks:
                raise MissingTaskError(
                    f"Task '{task_name}' depends on missing task '{dependency}'."
                )
            graph.add_edge(dependency, task_name)

    _raise_if_cycle(graph)
    return graph


def execution_order_for_targets(graph: nx.DiGraph, targets: Sequence[str]) -> list[str]:
    """Return topological order needed to run the requested targets."""
    for target in targets:
        if target not in graph:
            raise MissingTaskError(f"Task '{target}' is not defined in the task graph.")

    required_nodes: set[str] = set()
    for target in targets:
        required_nodes.add(target)
        required_nodes.update(nx.ancestors(graph, target))

    subgraph = cast(nx.DiGraph, graph.subgraph(sorted(required_nodes)).copy())
    _raise_if_cycle(subgraph)

    return list(nx.topological_sort(subgraph))


def render_ascii_graph(graph: nx.DiGraph) -> str:
    """Render a tree-style ASCII dependency graph with box drawing characters."""
    # Group tasks by topological layers
    layers: list[list[str]] = []
    remaining = set(graph.nodes)

    while remaining:
        # Find tasks with no unprocessed dependencies
        current_layer = sorted(
            node
            for node in remaining
            if all(pred not in remaining for pred in graph.predecessors(node))
        )
        if not current_layer:
            break
        layers.append(current_layer)
        remaining -= set(current_layer)

    lines: list[str] = []
    for layer_idx, layer in enumerate(layers):
        is_last_layer = layer_idx == len(layers) - 1

        if layer_idx == 0:
            lines.append("┌─ Roots (no dependencies)")
        elif is_last_layer:
            lines.append(f"└─ Layer {layer_idx}")
        else:
            lines.append(f"├─ Layer {layer_idx}")

        for task_idx, task_name in enumerate(layer):
            is_last_in_layer = task_idx == len(layer) - 1
            prefix = "└──" if is_last_in_layer else "├──"
            vertical = "   " if is_last_layer else "│  "

            dependencies = sorted(graph.predecessors(task_name))
            dependents = sorted(graph.successors(task_name))

            task_line = f"{vertical}{prefix} {task_name}"
            if dependencies:
                task_line += f" ← [{', '.join(dependencies)}]"
            if dependents:
                task_line += f" → [{', '.join(dependents)}]"

            lines.append(task_line)

    return "\n".join(lines)


def render_dot_graph(graph: nx.DiGraph) -> str:
    """Render the graph in DOT format."""
    lines = ["digraph cascade {"]

    for task_name in sorted(graph.nodes):
        lines.append(f'  "{task_name}";')

    for source, target in sorted(graph.edges):
        lines.append(f'  "{source}" -> "{target}";')

    lines.append("}")
    return "\n".join(lines)


def _raise_if_cycle(graph: nx.DiGraph) -> None:
    if nx.is_directed_acyclic_graph(graph):
        return

    cycle_edges = nx.find_cycle(graph, orientation="original")
    cycle_nodes = [edge[0] for edge in cycle_edges]
    cycle_nodes.append(cycle_edges[0][0])
    cycle_path = " -> ".join(cycle_nodes)
    raise CyclicDependencyError(f"Cyclic dependency detected: {cycle_path}")
