"""Integration tests with real pycas server.

These tests require a running pycas server (via Docker Compose).
Run with: docker compose -f tests/integration-pycas/docker-compose.yml up --abort-on-container-exit
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from cascade.cache.cas import CASCache
from cascade.cache.manager import CacheManager
from cascade.cache.local import LocalCache


@pytest.fixture
def pycas_url() -> str:
    """Get pycas URL from environment."""
    return os.getenv("CASCADE_CAS_URL", "grpc://localhost:50051")


@pytest.fixture
def local_cache(tmp_path: Path) -> LocalCache:
    """Create a local cache instance."""
    return LocalCache(tmp_path / "cache")


@pytest.mark.asyncio
async def test_pycas_upload_download(pycas_url: str, tmp_path: Path):
    """Test uploading and downloading artifacts from real pycas server."""
    cas_cache = CASCache(pycas_url, timeout=10.0)

    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello from Cascade!")

    try:
        # Upload to pycas
        success = await cas_cache.put("test_upload", [test_file])
        assert success, "Upload to pycas failed"

        # Delete local file
        test_file.unlink()
        assert not test_file.exists()

        # Download from pycas
        success = await cas_cache.get("test_upload", [test_file])
        assert success, "Download from pycas failed"

        # Verify content
        assert test_file.exists()
        assert test_file.read_text() == "Hello from Cascade!"

    finally:
        await cas_cache.close()


@pytest.mark.asyncio
async def test_pycas_exists(pycas_url: str, tmp_path: Path):
    """Test checking if artifact exists in pycas."""
    cas_cache = CASCache(pycas_url, timeout=10.0)

    # Create and upload test file
    test_file = tmp_path / "exists_test.txt"
    test_file.write_text("Exists check test")

    try:
        # Upload
        await cas_cache.put("exists_check", [test_file])

        # Check existence (should exist)
        exists = await cas_cache.exists("exists_check")
        assert exists, "Artifact should exist in pycas"

        # Check non-existent key
        exists = await cas_cache.exists("nonexistent_key")
        assert not exists, "Nonexistent artifact should return False"

    finally:
        await cas_cache.close()


@pytest.mark.asyncio
async def test_pycas_cache_manager_integration(
    pycas_url: str, local_cache: LocalCache, tmp_path: Path
):
    """Test CacheManager with real pycas server."""
    cas_cache = CASCache(pycas_url, timeout=10.0)
    manager = CacheManager(local_cache, cas_cache, auto_upload=True)

    # Create test file
    output_file = tmp_path / "manager_test.txt"
    output_file.write_text("CacheManager integration test")

    try:
        # Store in cache (should go to both local and remote)
        assert await manager.put("manager_test", [output_file])

        # Clear local cache to force remote retrieval
        await local_cache.clear()

        # Delete local file
        output_file.unlink()

        # Retrieve from cache (should come from remote, populate local)
        assert await manager.get("manager_test", [output_file])
        assert output_file.exists()
        assert output_file.read_text() == "CacheManager integration test"

        # Check stats
        stats = manager.get_stats()
        assert stats["remote_hits"] >= 1, "Should have at least one remote hit"

    finally:
        await cas_cache.close()


@pytest.mark.asyncio
async def test_pycas_multi_file_artifact(pycas_url: str, tmp_path: Path):
    """Test uploading and downloading multi-file artifacts."""
    cas_cache = CASCache(pycas_url, timeout=10.0)

    # Create multiple test files
    files = []
    for i in range(3):
        test_file = tmp_path / f"file{i}.txt"
        test_file.write_text(f"Content of file {i}")
        files.append(test_file)

    try:
        # Upload all files
        assert await cas_cache.put("multi_file_test", files)

        # Delete local files
        for f in files:
            f.unlink()

        # Download all files
        assert await cas_cache.get("multi_file_test", files)

        # Verify all files restored
        for i, f in enumerate(files):
            assert f.exists()
            assert f.read_text() == f"Content of file {i}"

    finally:
        await cas_cache.close()


@pytest.mark.asyncio
async def test_pycas_cache_sharing_simulation(pycas_url: str, tmp_path: Path):
    """Simulate cache sharing between two machines."""
    # Machine 1: Upload artifact
    cache1 = LocalCache(tmp_path / "machine1")
    cas1 = CASCache(pycas_url, timeout=10.0)
    manager1 = CacheManager(cache1, cas1, auto_upload=True)

    # Machine 2: Download artifact
    cache2 = LocalCache(tmp_path / "machine2")
    cas2 = CASCache(pycas_url, timeout=10.0)
    manager2 = CacheManager(cache2, cas2)

    # Create artifact on machine 1
    artifact = tmp_path / "machine1" / "shared.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("Shared across machines")

    try:
        # Machine 1: Upload to pycas
        assert await manager1.put("shared_key", [artifact])

        # Machine 2: Download from pycas (doesn't have local copy)
        artifact2 = tmp_path / "machine2" / "shared.txt"
        artifact2.parent.mkdir(parents=True, exist_ok=True)

        assert await manager2.get("shared_key", [artifact2])
        assert artifact2.exists()
        assert artifact2.read_text() == "Shared across machines"

        # Machine 2 should now have it in local cache
        stats2 = manager2.get_stats()
        assert stats2["remote_hits"] >= 1

    finally:
        await cas1.close()
        await cas2.close()


@pytest.mark.asyncio
async def test_pycas_large_file(pycas_url: str, tmp_path: Path):
    """Test uploading and downloading a larger file (>1MB)."""
    cas_cache = CASCache(pycas_url, timeout=30.0)

    # Create a 2MB file
    large_file = tmp_path / "large.bin"
    large_file.write_bytes(b"X" * (2 * 1024 * 1024))

    try:
        # Upload
        assert await cas_cache.put("large_file", [large_file])

        # Delete and download
        large_file.unlink()
        assert await cas_cache.get("large_file", [large_file])

        # Verify size
        assert large_file.stat().st_size == 2 * 1024 * 1024

    finally:
        await cas_cache.close()


@pytest.mark.asyncio
async def test_pycas_connection_retry(pycas_url: str, tmp_path: Path):
    """Test that retry logic works with real pycas server."""
    # Use very short timeout to potentially trigger retries
    cas_cache = CASCache(pycas_url, timeout=1.0, max_retries=3, initial_backoff=0.1)

    test_file = tmp_path / "retry_test.txt"
    test_file.write_text("Retry test")

    try:
        # Should succeed even with short timeout due to retries
        assert await cas_cache.put("retry_test", [test_file])
        assert await cas_cache.exists("retry_test")

    finally:
        await cas_cache.close()
