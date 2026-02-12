"""Task model used by planning and execution layers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Task:
    """Executable task definition."""

    name: str
    command: str
    inputs: list[Path]
    outputs: list[Path]
    depends_on: list[str]
    env: dict[str, str]
