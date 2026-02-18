"""Tests for rich progress display during parallel execution."""

from __future__ import annotations

import subprocess
from pathlib import Path


def test_rich_progress_disabled_with_plain_flag(tmp_path: Path) -> None:
    """Test that --plain flag disables rich progress and uses buffered output."""
    config = tmp_path / "cscd.yaml"
    config.write_text("""
version: 1
tasks:
  task1:
    command: echo "Task 1"
  task2:
    command: echo "Task 2"
  task3:
    command: echo "Task 3"
    depends_on: [task1, task2]
""")

    result = subprocess.run(
        ["uv", "run", "cscd", "run", "--config", str(config), "task3", "--jobs", "4", "--plain"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
        timeout=30,
    )

    assert result.returncode == 0
    # Plain mode should show sectioned output with arrows
    assert "→ task1" in result.stdout or "→ task2" in result.stdout
    assert "✓ task3" in result.stdout


def test_rich_progress_in_interactive_mode_completes() -> None:
    """Test that rich progress mode executes tasks successfully.

    Note: This test verifies execution completes but cannot verify
    the visual display since we can't capture rich output in tests.
    """
    config_path = Path(__file__).parent.parent.parent / "examples" / "parallel" / "cscd.yaml"

    result = subprocess.run(
        ["uv", "run", "cscd", "run", "--config", str(config_path), "package", "--jobs", "4"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    # Execution should succeed regardless of display mode
    assert result.returncode == 0
    assert "Successfully executed" in result.stdout


def test_rich_progress_disabled_in_non_tty() -> None:
    """Test that rich progress is automatically disabled in non-TTY environments.

    When output is piped (non-TTY), rich progress should be disabled
    and buffered plain output should be used instead.
    """
    config_path = Path(__file__).parent.parent.parent / "examples" / "parallel" / "cscd.yaml"

    result = subprocess.run(
        ["uv", "run", "cscd", "run", "--config", str(config_path), "package", "--jobs", "4"],
        capture_output=True,  # Piping output makes it non-TTY
        text=True,
        timeout=30,
    )

    assert result.returncode == 0
    # Non-TTY should automatically use buffered output
    assert "→ lint" in result.stdout or "✓ lint" in result.stdout


def test_sequential_execution_uses_streaming_output(tmp_path: Path) -> None:
    """Test that sequential execution (--jobs 1) uses streaming output."""
    config = tmp_path / "cscd.yaml"
    config.write_text("""
version: 1
tasks:
  task1:
    command: echo "Task 1 output"
  task2:
    command: echo "Task 2 output"
    depends_on: [task1]
""")

    result = subprocess.run(
        ["uv", "run", "cscd", "run", "--config", str(config), "task2", "--jobs", "1"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent.parent,
        timeout=30,
    )

    assert result.returncode == 0
    # Sequential mode shows "Running:" prefix
    assert "Running: task1" in result.stdout
    assert "Running: task2" in result.stdout
    assert "Task 1 output" in result.stdout
    assert "Task 2 output" in result.stdout
