"""Cache backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class CacheBackend(ABC):
    """Abstract cache backend interface for storing task outputs.

    Backends can be implemented synchronously or asynchronously.
    Async implementations should override the async methods.
    """

    @abstractmethod
    async def exists(self, cache_key: str) -> bool:
        """Check if cached artifact exists for given key."""
        pass

    @abstractmethod
    async def get(self, cache_key: str, output_paths: list[Path]) -> bool:
        """Restore cached outputs to their target locations.

        Args:
            cache_key: Content hash key.
            output_paths: List of output file/directory paths to restore.

        Returns:
            True if restoration succeeded, False otherwise.
        """
        pass

    @abstractmethod
    async def put(self, cache_key: str, output_paths: list[Path]) -> bool:
        """Store task outputs in cache.

        Args:
            cache_key: Content hash key.
            output_paths: List of output file/directory paths to cache.

        Returns:
            True if storage succeeded, False otherwise.
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached artifacts."""
        pass
