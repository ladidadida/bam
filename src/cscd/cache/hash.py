"""Content hashing for cache key computation."""

from __future__ import annotations

import hashlib
from pathlib import Path


def expand_globs(patterns: list[str], base_dir: Path | None = None) -> list[Path]:
    """Expand glob patterns to concrete file paths.

    Args:
        patterns: List of glob patterns or file paths.
        base_dir: Base directory for relative paths (default: cwd).

    Returns:
        List of resolved Path objects (sorted, deduplicated).
    """
    base = base_dir or Path.cwd()
    paths: set[Path] = set()

    for pattern in patterns:
        if "*" in pattern or "?" in pattern:
            # Glob pattern
            for match in base.glob(pattern):
                if match.is_file():
                    paths.add(match.resolve())
        else:
            # Direct path
            path = base / pattern
            if path.exists():
                paths.add(path.resolve())

    return sorted(paths)


def compute_cache_key(
    command: str,
    inputs: list[Path],
    env: dict[str, str] | None = None,
) -> str:
    """Compute deterministic SHA256 hash for task inputs.

    Args:
        command: Shell command string.
        inputs: List of input file paths (assumes already resolved/expanded).
        env: Environment variables dict.

    Returns:
        SHA256 hex digest string.
    """
    hasher = hashlib.sha256()

    # Hash command
    hasher.update(command.encode("utf-8"))

    # Hash environment variables (sorted for determinism)
    if env:
        for key in sorted(env.keys()):
            hasher.update(f"{key}={env[key]}".encode())

    # Hash input files (sorted for determinism)
    for input_path in sorted(inputs):
        if not input_path.exists():
            continue

        if input_path.is_file():
            hasher.update(input_path.read_bytes())
        elif input_path.is_dir():
            # Hash all files in directory recursively
            for file_path in sorted(input_path.rglob("*")):
                if file_path.is_file():
                    relative = file_path.relative_to(input_path)
                    hasher.update(str(relative).encode("utf-8"))
                    hasher.update(file_path.read_bytes())

    return hasher.hexdigest()
