"""Integration tests for CacheManager with local and remote caching."""

from __future__ import annotations

from pathlib import Path

import pytest

from bam_tool.cache import CacheManager, CASCache, LocalCache


@pytest.mark.asyncio
async def test_cache_manager_local_only(tmp_path: Path):
    """Test CacheManager with only local cache."""
    local_cache = LocalCache(tmp_path / "cache")
    manager = CacheManager(local_cache=local_cache, remote_cache=None)

    # Create test file
    output_file = tmp_path / "output.txt"
    output_file.write_text("test data")

    # Store in cache
    assert await manager.put("test_key", [output_file])

    # Retrieve from cache
    output_file.unlink()
    assert await manager.get("test_key", [output_file])
    assert output_file.read_text() == "test data"

    # Check stats
    stats = manager.get_stats()
    assert stats["local_hits"] == 1
    assert stats["remote_hits"] == 0
    assert stats["misses"] == 0


@pytest.mark.asyncio
async def test_cache_manager_fallback_to_local(tmp_path: Path):
    """Test CacheManager falls back to local when remote fails."""
    local_cache = LocalCache(tmp_path / "cache")

    # Create remote cache with invalid URL (will fail)
    remote_cache = CASCache("grpc://invalid-host:99999", timeout=0.1)

    manager = CacheManager(local_cache=local_cache, remote_cache=remote_cache, auto_upload=True)

    # Create test file
    output_file = tmp_path / "output.txt"
    output_file.write_text("test data")

    # Store should succeed in local (remote upload will fail but not block)
    assert await manager.put("test_key", [output_file])

    # Check stats - upload should have failed
    stats = manager.get_stats()
    assert stats["remote_upload_failures"] >= 1

    # Retrieve from local cache should work
    output_file.unlink()
    assert await manager.get("test_key", [output_file])
    assert output_file.read_text() == "test data"

    # Check stats - should be local hit
    stats = manager.get_stats()
    assert stats["local_hits"] == 1
    assert stats["remote_hits"] == 0


@pytest.mark.asyncio
async def test_cache_manager_exists_checks_both(tmp_path: Path):
    """Test exists() checks both local and remote."""
    local_cache = LocalCache(tmp_path / "cache")
    manager = CacheManager(local_cache=local_cache, remote_cache=None)

    # Non-existent key
    assert not await manager.exists("nonexistent")

    # Create and store
    output_file = tmp_path / "output.txt"
    output_file.write_text("test")
    await manager.put("test_key", [output_file])

    # Should exist in local
    assert await manager.exists("test_key")


@pytest.mark.asyncio
async def test_cache_manager_clear_local_only(tmp_path: Path):
    """Test clear() only clears local cache."""
    local_cache = LocalCache(tmp_path / "cache")
    manager = CacheManager(local_cache=local_cache, remote_cache=None)

    # Store something
    output_file = tmp_path / "output.txt"
    output_file.write_text("test")
    await manager.put("test_key", [output_file])

    # Clear
    await manager.clear()

    # Should no longer exist
    assert not await manager.exists("test_key")


@pytest.mark.asyncio
async def test_cache_manager_stats_tracking(tmp_path: Path):
    """Test statistics tracking."""
    local_cache = LocalCache(tmp_path / "cache")
    manager = CacheManager(local_cache=local_cache, remote_cache=None)

    output_file = tmp_path / "output.txt"

    # Miss
    assert not await manager.get("nonexistent", [output_file])

    # Put
    output_file.write_text("test")
    await manager.put("key1", [output_file])

    # Hit
    output_file.unlink()
    await manager.get("key1", [output_file])

    stats = manager.get_stats()
    assert stats["local_hits"] == 1
    assert stats["remote_hits"] == 0
    assert stats["misses"] == 1
    assert stats["total_requests"] == 2
    assert stats["hit_rate"] == 50.0

    # Reset stats
    manager.reset_stats()
    stats = manager.get_stats()
    assert stats["local_hits"] == 0
    assert stats["total_requests"] == 0
