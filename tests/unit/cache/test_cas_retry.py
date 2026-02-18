"""Tests for CASCache retry logic and error handling."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import grpc
import pytest

from cscd.cache.cas import CASCache

# Valid 64-character SHA256 hex for testing
TEST_DIGEST = "a" * 64
TEST_CACHE_KEY = f"{TEST_DIGEST}/1024"


@pytest.fixture
def cas_cache():
    """Create a CASCache instance for testing."""
    return CASCache(
        cas_url="grpc://localhost:50051",
        token="test-token",
        timeout=5.0,
        max_retries=3,
        initial_backoff=0.01,  # Fast retries for tests
    )


@pytest.mark.asyncio
async def test_retry_on_unavailable(cas_cache, tmp_path):
    """Test retry logic on UNAVAILABLE error."""
    # Mock the stub to fail twice then succeed
    mock_stub = AsyncMock()
    call_count = 0

    async def mock_find_missing(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            # Fail first two attempts
            error = grpc.RpcError()
            error.code = lambda: grpc.StatusCode.UNAVAILABLE
            error.details = lambda: "Connection refused"
            raise error
        # Succeed on third attempt
        response = MagicMock()
        response.missing_blob_digests = []
        return response

    mock_stub.FindMissingBlobs = mock_find_missing

    with patch.object(cas_cache, "_ensure_connected"):
        cas_cache._stub = mock_stub
        result = await cas_cache.exists(TEST_CACHE_KEY)

    assert result is True
    assert call_count == 3  # Should have retried twice


@pytest.mark.asyncio
async def test_no_retry_on_authentication_error(cas_cache):
    """Test that authentication errors are not retried."""
    mock_stub = AsyncMock()
    call_count = 0

    async def mock_find_missing(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        error = grpc.RpcError()
        error.code = lambda: grpc.StatusCode.UNAUTHENTICATED
        error.details = lambda: "Invalid token"
        raise error

    mock_stub.FindMissingBlobs = mock_find_missing

    with patch.object(cas_cache, "_ensure_connected"):
        cas_cache._stub = mock_stub

        try:
            await cas_cache.exists(TEST_CACHE_KEY)
        except grpc.RpcError:
            pass  # Expected to raise

    assert call_count == 1  # Should not retry


@pytest.mark.asyncio
async def test_max_retries_exhausted(cas_cache):
    """Test that retries stop after max attempts."""
    mock_stub = AsyncMock()
    call_count = 0

    async def mock_find_missing(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        error = grpc.RpcError()
        error.code = lambda: grpc.StatusCode.UNAVAILABLE
        error.details = lambda: "Connection refused"
        raise error

    mock_stub.FindMissingBlobs = mock_find_missing

    with patch.object(cas_cache, "_ensure_connected"):
        cas_cache._stub = mock_stub
        result = await cas_cache.exists(TEST_CACHE_KEY)

    assert result is False
    assert call_count == 3  # Should have retried max_retries times


@pytest.mark.asyncio
async def test_exponential_backoff(cas_cache):
    """Test that backoff increases exponentially."""
    delays = []

    async def mock_sleep(delay):
        delays.append(delay)

    mock_stub = AsyncMock()

    async def mock_find_missing(*args, **kwargs):
        error = grpc.RpcError()
        error.code = lambda: grpc.StatusCode.UNAVAILABLE
        error.details = lambda: "Temporary failure"
        raise error

    mock_stub.FindMissingBlobs = mock_find_missing

    with (
        patch.object(cas_cache, "_ensure_connected"),
        patch("cscd.cache.cas.asyncio.sleep", mock_sleep),
    ):
        cas_cache._stub = mock_stub
        await cas_cache.exists(TEST_CACHE_KEY)

    # Should have 2 delays (after 1st and 2nd attempts)
    assert len(delays) == 2
    # Second delay should be ~2x first (exponential backoff)
    assert delays[1] > delays[0] * 1.5


@pytest.mark.asyncio
async def test_connection_pooling_options(cas_cache):
    """Test that connection pooling options are set."""
    with patch("cscd.cache.cas.grpc.aio.insecure_channel") as mock_channel:
        mock_channel.return_value = AsyncMock()
        await cas_cache._ensure_connected()

        # Verify keepalive options were passed
        call_args = mock_channel.call_args
        options = call_args[1]["options"]

        # Check keepalive options are present
        option_keys = [opt[0] for opt in options]
        assert "grpc.keepalive_time_ms" in option_keys
        assert "grpc.keepalive_timeout_ms" in option_keys


@pytest.mark.asyncio
async def test_error_message_unavailable(cas_cache):
    """Test user-friendly error message for UNAVAILABLE."""
    error = grpc.RpcError()
    error.code = lambda: grpc.StatusCode.UNAVAILABLE
    error.details = lambda: "Connection refused"

    message = cas_cache._get_error_message(error)

    assert "unavailable" in message.lower()
    assert cas_cache.cas_url in message


@pytest.mark.asyncio
async def test_error_message_timeout(cas_cache):
    """Test user-friendly error message for DEADLINE_EXCEEDED."""
    error = grpc.RpcError()
    error.code = lambda: grpc.StatusCode.DEADLINE_EXCEEDED
    error.details = lambda: "Deadline exceeded"

    message = cas_cache._get_error_message(error)

    assert "timeout" in message.lower()
    assert str(cas_cache.timeout) in message


@pytest.mark.asyncio
async def test_error_message_auth(cas_cache):
    """Test user-friendly error message for UNAUTHENTICATED."""
    error = grpc.RpcError()
    error.code = lambda: grpc.StatusCode.UNAUTHENTICATED
    error.details = lambda: "Invalid credentials"

    message = cas_cache._get_error_message(error)

    assert "authentication" in message.lower() or "token" in message.lower()


@pytest.mark.asyncio
async def test_download_with_retry(cas_cache, tmp_path):
    """Test download with retry on transient failure."""
    output_path = tmp_path / "output.txt"
    mock_stub = AsyncMock()
    call_count = 0

    async def mock_batch_read(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Fail first attempt
            error = grpc.RpcError()
            error.code = lambda: grpc.StatusCode.UNAVAILABLE
            error.details = lambda: "Network error"
            raise error

        # Succeed on second attempt
        response = MagicMock()
        blob_response = MagicMock()
        blob_response.status_code = 0
        blob_response.data = b"test data"
        response.responses = [blob_response]
        return response

    mock_stub.BatchReadBlobs = mock_batch_read

    with (
        patch.object(cas_cache, "_ensure_connected"),
        patch.object(cas_cache, "_extract_tarball", AsyncMock()),
    ):
        cas_cache._stub = mock_stub
        result = await cas_cache.get(TEST_CACHE_KEY, [output_path])

    assert result is True
    assert call_count == 2  # Should have retried once


@pytest.mark.asyncio
async def test_upload_with_retry(cas_cache, tmp_path):
    """Test upload with retry on transient failure."""
    output_path = tmp_path / "output.txt"
    output_path.write_text("test content")

    mock_stub = AsyncMock()
    call_count = 0

    async def mock_batch_update(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Fail first attempt
            error = grpc.RpcError()
            error.code = lambda: grpc.StatusCode.RESOURCE_EXHAUSTED
            error.details = lambda: "Server overloaded"
            raise error

        # Succeed on second attempt
        response = MagicMock()
        upload_response = MagicMock()
        upload_response.status_code = 0
        response.responses = [upload_response]
        return response

    mock_stub.BatchUpdateBlobs = mock_batch_update

    with patch.object(cas_cache, "_ensure_connected"):
        cas_cache._stub = mock_stub
        result = await cas_cache.put(TEST_DIGEST, [output_path])

    assert result is True
    assert call_count == 2  # Should have retried once


@pytest.mark.asyncio
async def test_connection_failure_tracking(cas_cache):
    """Test that connection failures are tracked."""
    mock_stub = AsyncMock()

    async def mock_find_missing(*args, **kwargs):
        error = grpc.RpcError()
        error.code = lambda: grpc.StatusCode.UNAVAILABLE
        error.details = lambda: "Connection refused"
        raise error

    mock_stub.FindMissingBlobs = mock_find_missing

    with patch.object(cas_cache, "_ensure_connected"):
        cas_cache._stub = mock_stub

        # Make multiple failed requests
        await cas_cache.exists("test1")
        await cas_cache.exists("test2")
        await cas_cache.exists("test3")

    # Connection failures should be tracked
    assert cas_cache._connection_failures > 0
