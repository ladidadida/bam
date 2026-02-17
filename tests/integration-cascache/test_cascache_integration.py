"""Integration tests with real cascache server.

These tests require a running cascache server (via Docker Compose).
Run with: docker compose -f tests/integration-cascache/docker-compose.yml up --abort-on-container-exit

These tests are marked with @pytest.mark.cascache and are skipped by default.
To run them: pytest -m cascache
"""

from __future__ import annotations

import os
import socket
from pathlib import Path

import pytest

from cascade.cache.cas import CASCache
from cascade.cache.hash import compute_cache_key
from cascade.cache.local import LocalCache
from cascade.cache.manager import CacheManager


def compute_test_cache_key(name: str, files: list[Path]) -> str:
    """Compute a cache key for test files.

    Args:
        name: Test name identifier
        files: List of file paths

    Returns:
        64-character SHA256 hex digest
    """
    return compute_cache_key(command=f"test-{name}", inputs=files)


def is_cascache_available() -> bool:
    """Check if cascache server is available."""
    try:
        url = os.getenv("CASCADE_CAS_URL", "grpc://localhost:50051")
        host = "localhost"
        port = 50051

        if "://" in url:
            host_port = url.split("://")[1]
            if ":" in host_port:
                host, port_str = host_port.rsplit(":", 1)
                port = int(port_str)

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not is_cascache_available(),
    reason="cascache server not available (run with Docker Compose or start server manually)"
)


@pytest.fixture
def cascache_url() -> str:
    """Get cascache URL from environment."""
    return os.getenv("CASCADE_CAS_URL", "grpc://localhost:50051")


@pytest.fixture
def local_cache(tmp_path: Path) -> LocalCache:
    """Create a local cache instance."""
    return LocalCache(tmp_path / "cache")


@pytest.mark.cascache
@pytest.mark.asyncio
async def test_cascache_upload_download(cascache_url: str, tmp_path: Path):
    """Test uploading and downloading artifacts from real cascache server."""
    cas_cache = CASCache(cascache_url, timeout=10.0)

    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("Hello from Cascade!")

    # Compute proper cache key
    cache_key = compute_test_cache_key("upload", [test_file])

    try:
        # Upload to cascache
        success = await cas_cache.put(cache_key, [test_file])
        assert success, "Upload to cascache failed"

        # Delete local file
        test_file.unlink()
        assert not test_file.exists()

        # Download from cascache
        success = await cas_cache.get(cache_key, [test_file])
        assert success, "Download from cascache failed"

        # Verify content
        assert test_file.exists()
        assert test_file.read_text() == "Hello from Cascade!"

    finally:
        await cas_cache.close()


@pytest.mark.cascache
@pytest.mark.asyncio
async def test_cascache_exists(cascache_url: str, tmp_path: Path):
    """Test checking if artifact exists in cascache."""
    cas_cache = CASCache(cascache_url, timeout=10.0)

    # Create and upload test file
    test_file = tmp_path / "exists_test.txt"
    test_file.write_text("Exists check test")

    # Compute proper cache keys
    cache_key = compute_test_cache_key("exists", [test_file])
    fake_key = "0" * 64  # Valid format but nonexistent

    try:
        # Upload
        await cas_cache.put(cache_key, [test_file])

        # Check existence (should exist)
        exists = await cas_cache.exists(cache_key)
        assert exists, "Artifact should exist in cascache"

        # Check non-existent key
        exists = await cas_cache.exists(fake_key)
        assert not exists, "Nonexistent artifact should return False"

    finally:
        await cas_cache.close()


@pytest.mark.cascache
@pytest.mark.asyncio
async def test_cascache_cache_manager_integration(
    cascache_url: str, local_cache: LocalCache, tmp_path: Path
):
    """Test CacheManager with real cascache server."""
    cas_cache = CASCache(cascache_url, timeout=10.0)
    manager = CacheManager(local_cache, cas_cache, auto_upload=True)

    # Create test file
    output_file = tmp_path / "manager_test.txt"
    output_file.write_text("CacheManager integration test")

    # Compute proper cache key
    cache_key = compute_test_cache_key("manager", [output_file])

    try:
        # Store in cache (should go to both local and remote)
        assert await manager.put(cache_key, [output_file])

        # Clear local cache to force remote retrieval
        await local_cache.clear()

        # Delete local file
        output_file.unlink()

        # Retrieve from cache (should come from remote, populate local)
        assert await manager.get(cache_key, [output_file])
        assert output_file.exists()
        assert output_file.read_text() == "CacheManager integration test"

        # Check stats
        stats = manager.get_stats()
        assert stats["remote_hits"] >= 1, "Should have at least one remote hit"

    finally:
        await cas_cache.close()


@pytest.mark.cascache
@pytest.mark.asyncio
async def test_cascache_multi_file_artifact(cascache_url: str, tmp_path: Path):
    """Test uploading and downloading multi-file artifacts."""
    cas_cache = CASCache(cascache_url, timeout=10.0)

    # Create multiple test files
    files = []
    for i in range(3):
        test_file = tmp_path / f"file{i}.txt"
        test_file.write_text(f"Content of file {i}")
        files.append(test_file)

    # Compute proper cache key
    cache_key = compute_test_cache_key("multi", files)

    try:
        # Upload all files
        assert await cas_cache.put(cache_key, files)

        # Delete local files
        for f in files:
            f.unlink()

        # Download all files
        assert await cas_cache.get(cache_key, files)

        # Verify all files restored
        for i, f in enumerate(files):
            assert f.exists()
            assert f.read_text() == f"Content of file {i}"

    finally:
        await cas_cache.close()


@pytest.mark.cascache
@pytest.mark.asyncio
async def test_cascache_cache_sharing_simulation(cascache_url: str, tmp_path: Path):
    """Simulate cache sharing between two machines."""
    # Machine 1: Upload artifact
    cache1 = LocalCache(tmp_path / "machine1")
    cas1 = CASCache(cascache_url, timeout=10.0)
    manager1 = CacheManager(cache1, cas1, auto_upload=True)

    # Machine 2: Download artifact
    cache2 = LocalCache(tmp_path / "machine2")
    cas2 = CASCache(cascache_url, timeout=10.0)
    manager2 = CacheManager(cache2, cas2)

    # Create artifact on machine 1
    artifact = tmp_path / "machine1" / "shared.txt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("Shared across machines")

    # Compute proper cache key
    cache_key = compute_test_cache_key("shared", [artifact])

    try:
        # Machine 1: Upload to cascache
        assert await manager1.put(cache_key, [artifact])

        # Machine 2: Download from cascache (doesn't have local copy)
        artifact2 = tmp_path / "machine2" / "shared.txt"
        artifact2.parent.mkdir(parents=True, exist_ok=True)

        assert await manager2.get(cache_key, [artifact2])
        assert artifact2.exists()
        assert artifact2.read_text() == "Shared across machines"

        # Machine 2 should now have it in local cache
        stats2 = manager2.get_stats()
        assert stats2["remote_hits"] >= 1

    finally:
        await cas1.close()
        await cas2.close()


@pytest.mark.cascache
@pytest.mark.asyncio
async def test_cascache_large_file(cascache_url: str, tmp_path: Path):
    """Test uploading and downloading a larger file (>1MB)."""
    cas_cache = CASCache(cascache_url, timeout=30.0)

    # Create a 2MB file
    large_file = tmp_path / "large.bin"
    large_file.write_bytes(b"X" * (2 * 1024 * 1024))

    # Compute proper cache key
    cache_key = compute_test_cache_key("large", [large_file])

    try:
        # Upload
        assert await cas_cache.put(cache_key, [large_file])

        # Delete and download
        large_file.unlink()
        assert await cas_cache.get(cache_key, [large_file])

        # Verify size
        assert large_file.stat().st_size == 2 * 1024 * 1024

    finally:
        await cas_cache.close()


@pytest.mark.cascache
@pytest.mark.asyncio
async def test_cascache_connection_retry(cascache_url: str, tmp_path: Path):
    """Test that retry logic works with real cascache server."""
    # Use very short timeout to potentially trigger retries
    cas_cache = CASCache(cascache_url, timeout=1.0, max_retries=3, initial_backoff=0.1)

    test_file = tmp_path / "retry_test.txt"
    test_file.write_text("Retry test")

    # Compute proper cache key
    cache_key = compute_test_cache_key("retry", [test_file])

    try:
        # Should succeed even with short timeout due to retries
        assert await cas_cache.put(cache_key, [test_file])
        assert await cas_cache.exists(cache_key)

    finally:
        await cas_cache.close()
