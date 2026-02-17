"""CAS (Content-Addressable Storage) cache implementation using gRPC."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import tarfile
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import grpc

from cascade.api.generated import cas_simple_pb2, cas_simple_pb2_grpc
from cascade.cache.backend import CacheBackend

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_BACKOFF = 0.1  # 100ms
DEFAULT_MAX_BACKOFF = 5.0  # 5 seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0

# Size threshold for streaming (1MB)
STREAMING_THRESHOLD = 1024 * 1024


class CASCache(CacheBackend):
    """Remote cache implementation using Content-Addressable Storage (CAS).

    Connects to a cascache server via gRPC to store and retrieve cached artifacts.
    """

    def __init__(
        self,
        cas_url: str,
        token: str | None = None,
        timeout: float = 30.0,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
    ):
        """Initialize CAS cache client.

        Args:
            cas_url: CAS server URL (e.g., "grpc://localhost:50051")
            token: Optional authentication token
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            initial_backoff: Initial backoff delay in seconds
        """
        # Parse URL
        if cas_url.startswith("grpc://"):
            cas_url = cas_url[7:]  # Remove grpc:// prefix

        self.cas_url = cas_url
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries
        self.initial_backoff = initial_backoff
        self._channel: grpc.aio.Channel | None = None
        self._stub: cas_simple_pb2_grpc.ContentAddressableStorageStub | None = None
        self._connection_failures = 0

    async def _ensure_connected(self) -> None:
        """Ensure gRPC channel and stub are initialized."""
        if self._channel is None:
            # Create insecure channel with keepalive options for connection pooling
            options = [
                ("grpc.keepalive_time_ms", 30000),  # 30 seconds
                ("grpc.keepalive_timeout_ms", 10000),  # 10 seconds
                ("grpc.keepalive_permit_without_calls", 1),
                ("grpc.http2.max_pings_without_data", 0),
            ]
            self._channel = grpc.aio.insecure_channel(self.cas_url, options=options)
            self._stub = cas_simple_pb2_grpc.ContentAddressableStorageStub(self._channel)
            logger.debug(f"Established gRPC connection to {self.cas_url}")

    async def close(self) -> None:
        """Close gRPC channel."""
        if self._channel:
            await self._channel.close()
            self._channel = None
            self._stub = None
            logger.debug(f"Closed gRPC connection to {self.cas_url}")

    def _create_metadata(self) -> list[tuple[str, str]]:
        """Create gRPC metadata with authentication token."""
        metadata = []
        if self.token:
            metadata.append(("authorization", f"Bearer {self.token}"))
        return metadata

    def _compute_digest(self, data: bytes) -> cas_simple_pb2.Digest:
        """Compute SHA256 digest for blob data.

        Args:
            data: Blob data

        Returns:
            Digest message with hash and size
        """
        hash_value = hashlib.sha256(data).hexdigest()
        return cas_simple_pb2.Digest(hash=hash_value, size_bytes=len(data))

    async def _create_tarball(self, output_paths: list[Path]) -> bytes:
        """Create tarball of output files.

        Args:
            output_paths: List of output file paths

        Returns:
            Tarball as bytes
        """

        def _create_tar() -> bytes:
            """Create tar in executor (blocking operation)."""
            buffer = BytesIO()
            with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
                for output_path in output_paths:
                    if output_path.exists():
                        tar.add(output_path, arcname=output_path.name)
            return buffer.getvalue()

        return await asyncio.to_thread(_create_tar)

    async def _extract_tarball(self, data: bytes, output_paths: list[Path]) -> None:
        """Extract tarball to output locations.

        Args:
            data: Tarball data
            output_paths: Target output paths
        """

        def _extract() -> None:
            """Extract tar in executor (blocking operation)."""
            buffer = BytesIO(data)
            with tarfile.open(fileobj=buffer, mode="r:gz") as tar:
                for output_path in output_paths:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        member = tar.getmember(output_path.name)
                        member.name = output_path.name
                        tar.extract(member, path=output_path.parent)
                    except KeyError:
                        logger.warning(f"Output file not found in cache: {output_path}")

        await asyncio.to_thread(_extract)

    async def _retry_with_backoff(self, operation: str, func, *args, **kwargs):
        """Retry an operation with exponential backoff.

        Args:
            operation: Name of operation for logging
            func: Async function to retry
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func if successful

        Raises:
            Last exception if all retries fail
        """
        last_exception = None
        backoff = self.initial_backoff

        for attempt in range(self.max_retries):
            try:
                return await func(*args, **kwargs)
            except grpc.RpcError as e:
                last_exception = e
                status_code = e.code()

                # Don't retry on certain errors
                if status_code in (
                    grpc.StatusCode.INVALID_ARGUMENT,
                    grpc.StatusCode.UNAUTHENTICATED,
                    grpc.StatusCode.PERMISSION_DENIED,
                ):
                    logger.warning(
                        f"{operation} failed with non-retryable error: {status_code.name}"
                    )
                    raise

                # Retry on transient errors
                if attempt < self.max_retries - 1:
                    logger.debug(
                        f"{operation} failed (attempt {attempt + 1}/{self.max_retries}): "
                        f"{status_code.name}. Retrying in {backoff:.2f}s..."
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * DEFAULT_BACKOFF_MULTIPLIER, DEFAULT_MAX_BACKOFF)
                else:
                    logger.warning(
                        f"{operation} failed after {self.max_retries} attempts: {status_code.name}"
                    )

        # All retries exhausted
        if last_exception:
            raise last_exception
        raise RuntimeError(f"{operation} failed with unknown error")

    def _get_error_message(self, e: grpc.RpcError) -> str:
        """Get user-friendly error message from gRPC error.

        Args:
            e: gRPC error

        Returns:
            Formatted error message
        """
        status_code = e.code()
        details = e.details() or "No details available"

        if status_code == grpc.StatusCode.UNAVAILABLE:
            self._connection_failures += 1
            return f"CAS server unavailable at {self.cas_url} (connection failure #{self._connection_failures})"
        elif status_code == grpc.StatusCode.DEADLINE_EXCEEDED:
            return f"CAS request timeout after {self.timeout}s"
        elif status_code == grpc.StatusCode.UNAUTHENTICATED:
            return "Authentication failed - check your CAS token"
        elif status_code == grpc.StatusCode.PERMISSION_DENIED:
            return "Permission denied - insufficient privileges"
        elif status_code == grpc.StatusCode.RESOURCE_EXHAUSTED:
            return "CAS server resource exhausted - try again later"
        else:
            return f"CAS error ({status_code.name}): {details}"

    async def exists(self, cache_key: str) -> bool:
        """Check if artifact exists in remote cache.

        Args:
            cache_key: Cache key (used as digest hash)

        Returns:
            True if artifact exists, False otherwise
        """
        try:
            await self._ensure_connected()

            # Parse cache key (format: hash/size or just hash)
            if "/" in cache_key:
                hash_value, size_str = cache_key.split("/", 1)
                size_bytes = int(size_str)
            else:
                hash_value = cache_key
                size_bytes = 0  # Unknown size

            digest = cas_simple_pb2.Digest(hash=hash_value, size_bytes=size_bytes)

            async def _check_exists():
                request = cas_simple_pb2.FindMissingBlobsRequest(blob_digests=[digest])
                assert self._stub is not None
                response = await self._stub.FindMissingBlobs(
                    request,
                    metadata=self._create_metadata(),
                    timeout=self.timeout,
                )
                # If digest is in missing_blob_digests, it doesn't exist
                return len(response.missing_blob_digests) == 0

            return await self._retry_with_backoff("CAS exists check", _check_exists)

        except grpc.RpcError as e:
            logger.warning(f"CAS check failed for key {cache_key}: {self._get_error_message(e)}")
            return False
        except Exception as e:
            logger.warning(f"Unexpected error checking CAS: {e}")
            return False

    async def get(self, cache_key: str, output_paths: list[Path]) -> bool:
        """Download artifact from remote cache.

        Args:
            cache_key: Cache key (digest)
            output_paths: Target output paths

        Returns:
            True if successfully retrieved, False otherwise
        """
        try:
            await self._ensure_connected()

            # Parse cache key
            if "/" in cache_key:
                hash_value, size_str = cache_key.split("/", 1)
                size_bytes = int(size_str)
            else:
                hash_value = cache_key
                size_bytes = 0

            digest = cas_simple_pb2.Digest(hash=hash_value, size_bytes=size_bytes)

            async def _download_blob():
                request = cas_simple_pb2.BatchReadBlobsRequest(digests=[digest])
                assert self._stub is not None
                response = await self._stub.BatchReadBlobs(
                    request,
                    metadata=self._create_metadata(),
                    timeout=self.timeout,
                )

                # Check if blob was successfully downloaded
                if not response.responses:
                    logger.warning(f"No data returned for cache key: {cache_key}")
                    return None

                blob_response = response.responses[0]
                if blob_response.status_code != 0:
                    logger.warning(
                        f"Failed to download blob: {blob_response.status_message}"
                    )
                    return None

                return blob_response.data

            # Download with retry
            data = await self._retry_with_backoff("CAS download", _download_blob)
            if data is None:
                return False

            # Extract tarball to output locations
            size_mb = len(data) / (1024 * 1024)
            logger.debug(f"Downloaded {size_mb:.2f} MB from CAS: {cache_key}")
            await self._extract_tarball(data, output_paths)
            return True

        except grpc.RpcError as e:
            logger.warning(f"CAS download failed for key {cache_key}: {self._get_error_message(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during CAS download: {e}")
            return False

    async def put(self, cache_key: str, output_paths: list[Path]) -> bool:
        """Upload artifact to remote cache.

        Args:
            cache_key: Cache key for storage (must be 64-char SHA256 hex)
            output_paths: Output paths to cache

        Returns:
            True if successfully uploaded, False otherwise
        """
        try:
            await self._ensure_connected()

            # Create tarball of outputs
            tarball_data = await self._create_tarball(output_paths)
            size_mb = len(tarball_data) / (1024 * 1024)

            # Use cache_key as the digest hash (must be 64-char SHA256)
            # If cache_key is a valid 64-char hex string, use it directly
            # Otherwise, this is a programmer error - cache keys should be computed with compute_cache_key()
            if len(cache_key) != 64 or not all(c in "0123456789abcdef" for c in cache_key.lower()):
                logger.error(
                    f"Invalid cache_key '{cache_key[:20]}...': must be 64-character SHA256 hex. "
                    "Use cascade.cache.hash.compute_cache_key() to generate valid keys."
                )
                return False

            digest = cas_simple_pb2.Digest(hash=cache_key, size_bytes=len(tarball_data))

            # Log upload info
            if len(tarball_data) > STREAMING_THRESHOLD:
                logger.debug(
                    f"Uploading large artifact to CAS: {size_mb:.2f} MB "
                    f"(streaming would improve this in future)"
                )

            async def _upload_blob():
                request = cas_simple_pb2.BatchUpdateBlobsRequest.Request(
                    digest=digest,
                    data=tarball_data,
                )
                batch_request = cas_simple_pb2.BatchUpdateBlobsRequest(requests=[request])

                assert self._stub is not None
                response = await self._stub.BatchUpdateBlobs(
                    batch_request,
                    metadata=self._create_metadata(),
                    timeout=self.timeout,
                )

                # Check upload status
                if not response.responses:
                    logger.warning("No response from CAS upload")
                    return False

                upload_response = response.responses[0]
                if upload_response.status_code != 0:
                    logger.warning(f"Upload failed: {upload_response.status_message}")
                    return False

                return True

            # Upload with retry
            success = await self._retry_with_backoff("CAS upload", _upload_blob)
            if success:
                logger.debug(
                    f"Uploaded to CAS: {digest.hash}/{digest.size_bytes} ({size_mb:.2f} MB)"
                )
            return success

        except grpc.RpcError as e:
            logger.warning(f"CAS upload failed: {self._get_error_message(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during CAS upload: {e}")
            return False

    async def clear(self) -> None:
        """Clear cache (not supported for remote CAS).

        Remote CAS cache is shared across machines and should not be
        cleared by individual clients.
        """
        logger.warning("Clear operation not supported for remote CAS cache")
