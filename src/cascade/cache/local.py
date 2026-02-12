"""Local filesystem cache implementation."""

from __future__ import annotations

import json
import shutil
import tarfile
from pathlib import Path

from .backend import CacheBackend


class LocalCache(CacheBackend):
    """Local filesystem cache with tar.gz compression."""

    def __init__(self, cache_dir: Path | None = None):
        """Initialize local cache.

        Args:
            cache_dir: Cache directory path (default: .cascade/cache).
        """
        self.cache_dir = cache_dir or Path(".cascade/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def exists(self, cache_key: str) -> bool:
        """Check if cache entry exists."""
        entry_dir = self.cache_dir / cache_key
        return (entry_dir / "outputs.tar.gz").exists()

    def get(self, cache_key: str, output_paths: list[Path]) -> bool:
        """Restore cached outputs."""
        entry_dir = self.cache_dir / cache_key
        archive_path = entry_dir / "outputs.tar.gz"


        if not archive_path.exists():
            return False

        try:
            # Extract archive to temporary location then move
            temp_extract = entry_dir / "restore"
            temp_extract.mkdir(exist_ok=True)

            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(temp_extract, filter="data")

            # Move extracted files to target locations
            for output_path in output_paths:
                cached_item = temp_extract / output_path.name
                if not cached_item.exists():
                    continue

                # Remove existing output if present
                if output_path.exists():
                    if output_path.is_dir():
                        shutil.rmtree(output_path)
                    else:
                        output_path.unlink()

                # Move from cache to target
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(cached_item), str(output_path))

            # Cleanup temp extraction
            shutil.rmtree(temp_extract, ignore_errors=True)

            return True

        except (OSError, tarfile.TarError, json.JSONDecodeError):
            return False

    def put(self, cache_key: str, output_paths: list[Path]) -> bool:
        """Store task outputs in cache."""
        entry_dir = self.cache_dir / cache_key
        entry_dir.mkdir(parents=True, exist_ok=True)

        archive_path = entry_dir / "outputs.tar.gz"
        metadata_path = entry_dir / "metadata.json"

        try:
            # Create archive
            with tarfile.open(archive_path, "w:gz") as tar:
                for output_path in output_paths:
                    if output_path.exists():
                        tar.add(output_path, arcname=output_path.name)

            # Write metadata
            metadata = {
                "cache_key": cache_key,
                "outputs": [str(p) for p in output_paths],
            }
            metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

            return True

        except (OSError, tarfile.TarError):
            return False

    def clear(self) -> None:
        """Clear all cached artifacts."""
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
