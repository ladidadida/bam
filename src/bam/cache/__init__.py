"""Cache backend abstraction and implementations."""

from cascache_lib.cache import (
    CacheBackend,
    HybridCache,
    LocalCache,
    RemoteCache,
    compute_cache_key,
    create_cache,
    expand_globs,
)

CASCache = RemoteCache
CacheManager = HybridCache

__all__ = [
    "CacheBackend",
    "CASCache",
    "CacheManager",
    "LocalCache",
    "compute_cache_key",
    "create_cache",
    "expand_globs",
]
