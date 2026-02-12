"""Unit tests for cascade.cli."""

from __future__ import annotations

from cascade.cli import main


def test_main_no_args() -> None:
    """Test main() with no arguments."""
    result = main([])
    assert result == 0


def test_main_verbose() -> None:
    """Test main() with verbose flag."""
    result = main(["--verbose"])
    assert result == 0


def test_main_help() -> None:
    """Test main() with --help flag."""
    try:
        main(["--help"])
    except SystemExit as e:
        assert e.code == 0


def test_main_version() -> None:
    """Test main() with --version flag."""
    try:
        main(["--version"])
    except SystemExit as e:
        assert e.code == 0
