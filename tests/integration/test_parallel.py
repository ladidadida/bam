"""Integration tests for parallel task execution."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bam_tool.cli import app


@pytest.fixture
def parallel_workspace(tmp_path: Path) -> Path:
    """Create a workspace with parallel-friendly tasks."""
    workspace = tmp_path / "parallel"
    workspace.mkdir()

    config = """version: 1

tasks:
  task-a:
    inputs: []
    outputs: []
    command: echo "Task A"

  task-b:
    inputs: []
    outputs: []
    command: echo "Task B"

  task-c:
    inputs: []
    outputs: []
    command: echo "Task C"

  task-d:
    inputs: []
    outputs: []
    command: echo "Task D"
    depends_on:
      - task-a
      - task-b

  task-e:
    inputs: []
    outputs: []
    command: echo "Task E"
    depends_on:
      - task-c
"""
    (workspace / "bam.yaml").write_text(config)
    return workspace


def test_parallel_execution_with_jobs_flag(parallel_workspace: Path) -> None:
    """Test that --jobs flag enables parallel execution."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run", "--config", str(parallel_workspace / "bam.yaml"), "task-d", "--jobs", "3"],
    )

    assert result.exit_code == 0
    assert "Successfully executed" in result.stdout


def test_parallel_execution_completes_successfully(parallel_workspace: Path) -> None:
    """Test that parallel execution completes all tasks."""
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run", "--config", str(parallel_workspace / "bam.yaml"), "task-d", "--jobs", "2"],
    )

    assert result.exit_code == 0
    # task-d depends on task-a and task-b, so both should run
    assert "Task A" in result.stdout
    assert "Task B" in result.stdout
    assert "Task D" in result.stdout


def test_parallel_execution_stops_on_failure(tmp_path: Path) -> None:
    """Test that parallel execution stops when a task fails."""
    config = """version: 1

tasks:
  good-1:
    inputs: []
    outputs: []
    command: echo "Good 1"

  good-2:
    inputs: []
    outputs: []
    command: echo "Good 2"

  bad:
    inputs: []
    outputs: []
    command: exit 1

  dependent:
    inputs: []
    outputs: []
    command: echo "Should not run"
    depends_on:
      - good-1
      - good-2
      - bad
"""
    (tmp_path / "bam.yaml").write_text(config)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run", "--config", str(tmp_path / "bam.yaml"), "dependent", "--jobs", "3"],
    )

    assert result.exit_code == 1
    output = (result.stdout or "") + (result.stderr or "")
    assert "bad" in output
    # Should show skipped tasks
    assert "dependent" in output or "Skipped" in output


def test_parallel_speedup(parallel_workspace: Path) -> None:
    """Test that parallel execution is faster than sequential."""
    config = """version: 1

tasks:
  sleep-a:
    inputs: []
    outputs: []
    command: sleep 0.2

  sleep-b:
    inputs: []
    outputs: []
    command: sleep 0.2

  sleep-c:
    inputs: []
    outputs: []
    command: sleep 0.2

  final:
    inputs: []
    outputs: []
    command: echo "done"
    depends_on:
      - sleep-a
      - sleep-b
      - sleep-c
"""
    (parallel_workspace / "bam.yaml").write_text(config)

    runner = CliRunner()

    # Sequential execution
    start = time.time()
    result = runner.invoke(
        app,
        ["run", "--config", str(parallel_workspace / "bam.yaml"), "final", "--jobs", "1"],
    )
    sequential_time = time.time() - start

    assert result.exit_code == 0

    # Parallel execution
    start = time.time()
    result = runner.invoke(
        app,
        ["run", "--config", str(parallel_workspace / "bam.yaml"), "final", "--jobs", "3"],
    )
    parallel_time = time.time() - start

    assert result.exit_code == 0

    # Parallel should be at least 1.5x faster (accounting for overhead)
    # Sequential: ~0.6s (3 * 0.2s), Parallel: ~0.2s
    assert parallel_time < sequential_time * 0.7, (
        f"Parallel ({parallel_time:.2f}s) should be faster than sequential ({sequential_time:.2f}s)"
    )


def test_respects_dependency_order(tmp_path: Path) -> None:
    """Test that parallel execution respects task dependencies."""
    output_file = tmp_path / "execution_order.txt"

    config = f"""version: 1

tasks:
  first:
    inputs: []
    outputs: []
    command: echo "1" >> {output_file}

  second:
    inputs: []
    outputs: []
    command: echo "2" >> {output_file}
    depends_on:
      - first

  third:
    inputs: []
    outputs: []
    command: echo "3" >> {output_file}
    depends_on:
      - second
"""
    (tmp_path / "bam.yaml").write_text(config)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["run", "--config", str(tmp_path / "bam.yaml"), "third", "--jobs", "3"],
    )

    assert result.exit_code == 0

    # Verify execution order
    order = output_file.read_text().strip().split("\n")
    assert order == ["1", "2", "3"], f"Expected [1, 2, 3] but got {order}"
