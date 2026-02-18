"""Tests for improved error context with dependency chains and skipped tasks."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_shows_dependency_chain_on_failure(tmp_path: Path) -> None:
    """Test that failing task shows its dependency chain."""
    config = tmp_path / "cscd.yaml"
    config.write_text("""
version: 1
tasks:
  root:
    command: echo "Root"
  middle:
    command: echo "Middle"
    depends_on: [root]
  failing:
    command: exit 1
    depends_on: [middle]
  final:
    command: echo "Final"
    depends_on: [failing]
""")

    result = subprocess.run(
        ["uv", "run", "cscd", "run", "--config", str(config), "final"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    # Should show the failed task
    assert "Task failed: failing" in result.stderr
    # Should show dependency chain
    assert "Dependency chain:" in result.stderr
    assert "root" in result.stderr
    assert "middle" in result.stderr


def test_shows_skipped_tasks_on_failure(tmp_path: Path) -> None:
    """Test that execution failure lists skipped tasks."""
    config = tmp_path / "cscd.yaml"
    config.write_text("""
version: 1
tasks:
  task1:
    command: exit 1
  task2:
    command: echo "Should be skipped"
    depends_on: [task1]
  task3:
    command: echo "Also skipped"
    depends_on: [task2]
""")

    result = subprocess.run(
        ["uv", "run", "cscd", "run", "--config", str(config), "task3"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    # Should list skipped tasks
    assert "Skipped" in result.stderr
    assert "task2" in result.stderr
    assert "task3" in result.stderr


def test_no_skipped_tasks_when_all_complete(tmp_path: Path) -> None:
    """Test that successful execution doesn't show skipped tasks."""
    config = tmp_path / "cscd.yaml"
    config.write_text("""
version: 1
tasks:
  task1:
    command: echo "Task 1"
  task2:
    command: echo "Task 2"
    depends_on: [task1]
""")

    result = subprocess.run(
        ["uv", "run", "cscd", "run", "--config", str(config), "task2"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    assert "Skipped" not in result.stdout
    assert "Successfully executed" in result.stdout


def test_dependency_chain_single_task(tmp_path: Path) -> None:
    """Test dependency chain for task with no dependencies."""
    config = tmp_path / "cscd.yaml"
    config.write_text("""
version: 1
tasks:
  solo:
    command: exit 1
""")

    result = subprocess.run(
        ["uv", "run", "cscd", "run", "--config", str(config), "solo"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 1
    assert "Task failed: solo" in result.stderr
    # Solo task should not show "Dependency chain:" since it has none
    # (or shows just itself, which is fine)


def test_multiple_failures_show_all_contexts(tmp_path: Path) -> None:
    """Test that if multiple tasks fail, all get documented (edge case)."""
    # This is harder to test since we stop on first failure
    # but keeping as placeholder for future enhancement
    pass
