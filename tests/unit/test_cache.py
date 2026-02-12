"""Unit tests for cache module."""

from __future__ import annotations

from pathlib import Path

import pytest

from cascade.cache import LocalCache, compute_cache_key, expand_globs


def test_compute_cache_key_deterministic(tmp_path: Path) -> None:
    """Cache keys should be deterministic for same inputs."""
    test_file = tmp_path / "input.txt"
    test_file.write_text("content", encoding="utf-8")

    key1 = compute_cache_key("echo test", [test_file], {"VAR": "value"})
    key2 = compute_cache_key("echo test", [test_file], {"VAR": "value"})

    assert key1 == key2
    assert len(key1) == 64  # SHA256 hex length


def test_compute_cache_key_changes_with_inputs(tmp_path: Path) -> None:
    """Cache key should change when inputs change."""
    test_file = tmp_path / "input.txt"
    test_file.write_text("content1", encoding="utf-8")

    key1 = compute_cache_key("echo test", [test_file])

    test_file.write_text("content2", encoding="utf-8")
    key2 = compute_cache_key("echo test", [test_file])

    assert key1 != key2


def test_expand_globs(tmp_path: Path) -> None:
    """Expand glob patterns to concrete file paths."""
    (tmp_path / "file1.txt").touch()
    (tmp_path / "file2.txt").touch()
    (tmp_path / "other.md").touch()

    paths = expand_globs(["*.txt"], base_dir=tmp_path)

    assert len(paths) == 2
    assert all(p.suffix == ".txt" for p in paths)


@pytest.mark.asyncio
async def test_local_cache_put_and_get(tmp_path: Path) -> None:
    """Store and retrieve cached outputs."""
    cache_dir = tmp_path / "cache"
    cache = LocalCache(cache_dir)

    # Create test output
    output_file = tmp_path / "output.txt"
    output_file.write_text("test output", encoding="utf-8")

    cache_key = "testkey123"

    # Store in cache
    assert await cache.put(cache_key, [output_file])
    assert await cache.exists(cache_key)

    # Remove original
    output_file.unlink()
    assert not output_file.exists()

    # Restore from cache
    assert await cache.get(cache_key, [output_file])
    assert output_file.exists()
    assert output_file.read_text(encoding="utf-8") == "test output"


@pytest.mark.asyncio
async def test_local_cache_clear(tmp_path: Path) -> None:
    """Clear all cached artifacts."""
    cache_dir = tmp_path / "cache"
    cache = LocalCache(cache_dir)

    output_file = tmp_path / "output.txt"
    output_file.write_text("data", encoding="utf-8")

    await cache.put("key1", [output_file])
    assert await cache.exists("key1")

    await cache.clear()
    assert not await cache.exists("key1")


@pytest.mark.asyncio
async def test_local_cache_nonexistent_key(tmp_path: Path) -> None:
    """Return False for nonexistent cache keys."""
    cache = LocalCache(tmp_path / "cache")

    assert not await cache.exists("nonexistent")
    assert not await cache.get("nonexistent", [tmp_path / "fake.txt"])
