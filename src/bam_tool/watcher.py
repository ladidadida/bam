"""Watch mode — re-run tasks when input files change."""

from __future__ import annotations

import asyncio
from pathlib import Path

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .config.schema import BamConfig


class _ChangeHandler(FileSystemEventHandler):
    """Bridge watchdog thread events into an asyncio queue."""

    def __init__(
        self,
        queue: asyncio.Queue[Path],
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        super().__init__()
        self._queue = queue
        self._loop = loop

    def _notify(self, path: str) -> None:
        self._loop.call_soon_threadsafe(self._queue.put_nowait, Path(path))

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._notify(str(event.src_path))

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._notify(str(event.src_path))


def compute_watch_dirs(
    loaded_config: BamConfig,
    execution_order: list[str],
    config_file: Path,
) -> dict[Path, bool]:
    """Return ``{directory: recursive}`` covering all task inputs and the config file.

    For each task input pattern:

    * Glob patterns containing ``**`` are marked recursive; the watch root is
      the path portion before the first wildcard segment (e.g. ``src/** /*.py``
      → watch ``src/`` recursively).
    * Glob patterns with a single ``*`` are non-recursive; the same root
      extraction applies.
    * Literal file paths use the file's parent directory (non-recursive).

    The *config_file* parent is always included so ``bam.yaml`` changes are
    detected immediately.
    """
    roots: dict[Path, bool] = {}

    # Always watch the config file's directory (non-recursive is enough).
    config_dir = config_file.parent.resolve()
    roots[config_dir] = False

    base_dir = config_file.parent.resolve()

    for task_name in execution_order:
        task_config = loaded_config.tasks[task_name]
        for pattern in task_config.inputs:
            if "*" in pattern or "?" in pattern:
                recursive = "**" in pattern
                # Collect path segments up to (but not including) the first
                # segment that contains a wildcard.
                parts = Path(pattern).parts
                root_parts: list[str] = []
                for part in parts:
                    if "*" in part or "?" in part:
                        break
                    root_parts.append(part)
                prefix = "/".join(root_parts)
                root = Path(prefix) if prefix else Path(".")
            else:
                p = Path(pattern)
                root = p.parent if p.suffix else p
                recursive = False

            resolved = (base_dir / root).resolve()
            roots[resolved] = roots.get(resolved, False) or recursive

    return roots


async def wait_for_change(
    watch_dirs: dict[Path, bool],
    debounce_seconds: float = 0.3,
) -> Path:
    """Start a watchdog observer, wait for the first file-system change, return it.

    A simple debounce is applied: after the first event arrives the function
    sleeps *debounce_seconds* and drains any further queued events, so rapid
    saves (e.g. editor auto-save) are coalesced into a single trigger.

    Args:
        watch_dirs: Mapping of ``{directory: recursive}`` produced by
            :func:`compute_watch_dirs`.
        debounce_seconds: Quiet period after the first event before returning.

    Returns:
        Resolved path of the file that triggered the change.
    """
    loop = asyncio.get_running_loop()
    change_queue: asyncio.Queue[Path] = asyncio.Queue()
    handler = _ChangeHandler(change_queue, loop)

    observer = Observer()
    for root, recursive in watch_dirs.items():
        if root.exists():
            observer.schedule(handler, str(root), recursive=recursive)
    observer.start()

    try:
        path = await change_queue.get()
        # Debounce: let rapid-fire events settle, then return the last one.
        await asyncio.sleep(debounce_seconds)
        while not change_queue.empty():
            path = change_queue.get_nowait()
        return path.resolve()
    finally:
        observer.stop()
        observer.join()
