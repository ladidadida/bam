"""Unit tests for watch mode helpers."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from bam_tool.config.schema import BamConfig, TaskConfig
from bam_tool.watcher import compute_watch_dirs, wait_for_change


def _config(*tasks: tuple[str, list[str]]) -> BamConfig:
    """Build a minimal BamConfig with the given (name, inputs) pairs."""
    return BamConfig(
        tasks={name: TaskConfig(command="echo hi", inputs=inputs) for name, inputs in tasks}
    )


# ---------------------------------------------------------------------------
# compute_watch_dirs
# ---------------------------------------------------------------------------


def test_config_dir_always_included(tmp_path: Path) -> None:
    config_file = tmp_path / "bam.yaml"
    config_file.touch()
    loaded = _config()
    dirs = compute_watch_dirs(loaded, [], config_file)
    assert tmp_path.resolve() in dirs


def test_doublestar_glob_is_recursive(tmp_path: Path) -> None:
    config_file = tmp_path / "bam.yaml"
    config_file.touch()
    src = tmp_path / "src"
    src.mkdir()
    loaded = _config(("lint", ["src/**/*.py"]))
    dirs = compute_watch_dirs(loaded, ["lint"], config_file)
    assert dirs.get(src.resolve()) is True


def test_single_star_glob_is_non_recursive(tmp_path: Path) -> None:
    config_file = tmp_path / "bam.yaml"
    config_file.touch()
    tests = tmp_path / "tests"
    tests.mkdir()
    loaded = _config(("test", ["tests/*.py"]))
    dirs = compute_watch_dirs(loaded, ["test"], config_file)
    assert dirs.get(tests.resolve()) is False


def test_literal_file_watches_parent(tmp_path: Path) -> None:
    config_file = tmp_path / "bam.yaml"
    config_file.touch()
    readme = tmp_path / "README.md"
    readme.touch()
    loaded = _config(("docs", [str(readme)]))
    dirs = compute_watch_dirs(loaded, ["docs"], config_file)
    assert tmp_path.resolve() in dirs


def test_multiple_tasks_collect_all_dirs(tmp_path: Path) -> None:
    config_file = tmp_path / "bam.yaml"
    config_file.touch()
    src = tmp_path / "src"
    src.mkdir()
    tests = tmp_path / "tests"
    tests.mkdir()
    loaded = _config(
        ("lint", ["src/**/*.py"]),
        ("test", ["tests/*.py"]),
    )
    dirs = compute_watch_dirs(loaded, ["lint", "test"], config_file)
    assert src.resolve() in dirs
    assert tests.resolve() in dirs


def test_recursive_flag_upgrades_existing_entry(tmp_path: Path) -> None:
    """If two tasks share a root dir, recursive wins over non-recursive."""
    config_file = tmp_path / "bam.yaml"
    config_file.touch()
    src = tmp_path / "src"
    src.mkdir()
    loaded = _config(
        ("a", ["src/*.py"]),   # non-recursive
        ("b", ["src/**/*.py"]),  # recursive
    )
    dirs = compute_watch_dirs(loaded, ["a", "b"], config_file)
    assert dirs[src.resolve()] is True


# ---------------------------------------------------------------------------
# wait_for_change
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wait_for_change_file_modification(tmp_path: Path) -> None:
    watch_file = tmp_path / "input.txt"
    watch_file.write_text("initial")

    async def modify() -> None:
        await asyncio.sleep(0.15)
        watch_file.write_text("changed")

    asyncio.create_task(modify())
    changed = await wait_for_change({tmp_path: False}, debounce_seconds=0.05)
    assert changed.name == "input.txt"


@pytest.mark.asyncio
async def test_wait_for_change_new_file(tmp_path: Path) -> None:
    async def create() -> None:
        await asyncio.sleep(0.15)
        (tmp_path / "new.py").write_text("hello")

    asyncio.create_task(create())
    changed = await wait_for_change({tmp_path: False}, debounce_seconds=0.05)
    assert changed.name == "new.py"


@pytest.mark.asyncio
async def test_wait_for_change_returns_resolved_path(tmp_path: Path) -> None:
    watch_file = tmp_path / "src.py"
    watch_file.write_text("a")

    async def modify() -> None:
        await asyncio.sleep(0.15)
        watch_file.write_text("b")

    asyncio.create_task(modify())
    result = await wait_for_change({tmp_path: False}, debounce_seconds=0.05)
    assert result == result.resolve()
