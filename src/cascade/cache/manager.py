"""Cache manager for orchestrating local and remote caching."""

from __future__ import annotations

import logging
from pathlib import Path

from cascade.cache.backend import CacheBackend
from cascade.cache.cas import CASCache
from cascade.cache.local import LocalCache

logger = logging.getLogger(__name__)


class CacheManager(CacheBackend):
    """Manages hierarchical caching with local and optional remote cache.

    Strategy:
    - get(): Check local first (fast), then remote, populate local on remote hit
    - put(): Store in local AND upload to remote (automatic sync)
    - Gracefully fallback to local-only on remote errors
    """

    def __init__(
        self,
        local_cache: LocalCache,
        remote_cache: CASCache | None = None,
        auto_upload: bool = True,
    ):
        """Initialize cache manager.

        Args:
            local_cache: Local filesystem cache (always required)
            remote_cache: Optional remote CAS cache
            auto_upload: Whether to automatically upload to remote on put
        """
        self.local_cache = local_cache
        self.remote_cache = remote_cache
        self.auto_upload = auto_upload

        # Track cache statistics
        self.stats = {
            "local_hits": 0,
            "remote_hits": 0,
            "misses": 0,
            "remote_uploads": 0,
            "remote_upload_failures": 0,
            "remote_download_failures": 0,
        }

    async def exists(self, cache_key: str) -> bool:
        """Check if artifact exists in cache (local or remote).

        Args:
            cache_key: Cache key to check

        Returns:
            True if exists in either local or remote cache
        """
        # Check local first
        if await self.local_cache.exists(cache_key):
            return True

        # Check remote if available
        if self.remote_cache:
            try:
                return await self.remote_cache.exists(cache_key)
            except Exception as e:
                logger.debug(f"Remote cache check failed: {e}")
                return False

        return False

    async def get(self, cache_key: str, output_paths: list[Path]) -> bool:
        """Retrieve artifact from cache with local-first strategy.

        Strategy:
        1. Try local cache (fast)
        2. If miss, try remote cache
        3. If found in remote, populate local cache
        4. Fallback gracefully on errors

        Args:
            cache_key: Cache key
            output_paths: Target output paths

        Returns:
            True if successfully retrieved, False otherwise
        """
        # Try local cache first
        try:
            if await self.local_cache.get(cache_key, output_paths):
                self.stats["local_hits"] += 1
                logger.debug(f"Local cache hit: {cache_key}")
                return True
        except Exception as e:
            logger.warning(f"Local cache get failed: {e}")

        # Try remote cache if available
        if self.remote_cache:
            try:
                if await self.remote_cache.get(cache_key, output_paths):
                    self.stats["remote_hits"] += 1
                    logger.debug(f"Remote cache hit: {cache_key}")

                    # Populate local cache for future speed
                    try:
                        await self.local_cache.put(cache_key, output_paths)
                        logger.debug(f"Populated local cache from remote: {cache_key}")
                    except Exception as e:
                        logger.warning(f"Failed to populate local cache: {e}")

                    return True
            except Exception as e:
                self.stats["remote_download_failures"] += 1
                logger.warning(f"Remote cache get failed: {e}")

        # Cache miss
        self.stats["misses"] += 1
        return False

    async def put(self, cache_key: str, output_paths: list[Path]) -> bool:
        """Store artifact in cache with automatic remote sync.

        Strategy:
        1. Always store in local cache
        2. If auto_upload enabled, also upload to remote
        3. Don't fail if remote upload fails (best effort)

        Args:
            cache_key: Cache key
            output_paths: Output paths to cache

        Returns:
            True if successfully stored in at least local cache
        """
        stored_locally = False
        stored_remotely = False

        # Store in local cache (required)
        try:
            if await self.local_cache.put(cache_key, output_paths):
                stored_locally = True
                logger.debug(f"Stored in local cache: {cache_key}")
        except Exception as e:
            logger.error(f"Local cache put failed: {e}")
            return False

        # Upload to remote cache if available and enabled
        if self.remote_cache and self.auto_upload:
            try:
                if await self.remote_cache.put(cache_key, output_paths):
                    stored_remotely = True
                    self.stats["remote_uploads"] += 1
                    logger.debug(f"Uploaded to remote cache: {cache_key}")
                else:
                    self.stats["remote_upload_failures"] += 1
            except Exception as e:
                self.stats["remote_upload_failures"] += 1
                logger.warning(f"Remote cache upload failed (continuing): {e}")

        # Success if stored locally (remote is best-effort)
        return stored_locally

    async def clear(self) -> None:
        """Clear local cache only.

        Remote cache is intentionally not cleared as it's shared across machines.
        """
        try:
            await self.local_cache.clear()
            logger.info("Cleared local cache")
        except Exception as e:
            logger.error(f"Failed to clear local cache: {e}")

    async def close(self) -> None:
        """Close remote cache connections."""
        if self.remote_cache:
            try:
                await self.remote_cache.close()
                logger.debug("Closed remote cache connection")
            except Exception as e:
                logger.warning(f"Error closing remote cache: {e}")

    def get_stats(self) -> dict[str, int | float]:
        """Get cache statistics.

        Returns:
            Dictionary with cache hit/miss statistics
        """
        total = self.stats["local_hits"] + self.stats["remote_hits"] + self.stats["misses"]
        hit_rate = 0.0
        if total > 0:
            hit_rate = (self.stats["local_hits"] + self.stats["remote_hits"]) / total

        return {
            **self.stats,
            "total_requests": total,
            "hit_rate": round(hit_rate * 100, 1),
        }

    def reset_stats(self) -> None:
        """Reset cache statistics."""
        for key in self.stats:
            self.stats[key] = 0
