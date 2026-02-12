"""Cache backend abstraction and implementations."""

from .backend import CacheBackend
from .cas import CASCache
from .factory import create_cache
from .hash import compute_cache_key, expand_globs
from .local import LocalCache
from .manager import CacheManager

__all__ = [
    "CacheBackend",
    "CASCache",
    "CacheManager",
    "LocalCache",
    "compute_cache_key",
    "create_cache",
    "expand_globs",
]
