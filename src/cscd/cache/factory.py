"""Factory functions for creating cache instances from configuration."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from cscd.cache.backend import CacheBackend
from cscd.cache.cas import CASCache
from cscd.cache.local import LocalCache
from cscd.cache.manager import CacheManager

if TYPE_CHECKING:
    from cscd.config.schema import CacheConfig

logger = logging.getLogger(__name__)


def create_cache(config: CacheConfig, cache_dir: Path | None = None) -> CacheBackend:
    """Create cache instance based on configuration.

    Args:
        config: Cache configuration
        cache_dir: Override default cache directory

    Returns:
        CacheBackend instance (LocalCache, CASCache, or CacheManager)
    """
    # Create local cache (always required)
    local_path = cache_dir or Path(config.local.path)
    local_cache = LocalCache(local_path) if config.local.enabled else None

    # If only local cache, return it directly
    if not config.remote.enabled:
        if local_cache:
            logger.info(f"Using local cache: {local_path}")
            return local_cache
        else:
            # No cache enabled at all - create disabled cache
            logger.warning("No cache enabled")
            return LocalCache(Path(".cascade/cache"))  # Will exist but won't be used

    # Remote cache is enabled - create CASCache
    try:
        # Read token from file if specified
        token = None
        if config.remote.token_file:
            token_path = Path(config.remote.token_file).expanduser()
            if token_path.exists():
                token = token_path.read_text().strip()
                logger.debug(f"Loaded CAS token from {token_path}")
            else:
                logger.warning(f"Token file not found: {token_path}")

        remote_cache = CASCache(
            cas_url=config.remote.url,
            token=token,
            timeout=config.remote.timeout,
            max_retries=config.remote.max_retries,
            initial_backoff=config.remote.initial_backoff,
        )
        logger.info(f"Configured remote cache: {config.remote.url}")

        # Return CacheManager if we have both local and remote
        if local_cache:
            return CacheManager(
                local_cache=local_cache,
                remote_cache=remote_cache,
                auto_upload=config.remote.upload,
            )
        else:
            # Only remote cache
            return remote_cache

    except Exception as e:
        logger.error(f"Failed to create remote cache: {e}")
        if local_cache:
            logger.info("Falling back to local cache only")
            return local_cache
        raise
