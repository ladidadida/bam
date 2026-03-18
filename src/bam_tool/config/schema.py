"""Pydantic schema definitions for ``bam.yaml``."""

from __future__ import annotations

from typing import Any, Literal

from cascache_lib.config import CacheConfig
from pydantic import BaseModel, ConfigDict, Field


class TaskConfig(BaseModel):
    """Task definition loaded from configuration."""

    model_config = ConfigDict(extra="forbid")

    command: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    stage: str | None = None


class CiConfig(BaseModel):
    """CI pipeline generation settings.

    Controls the output of ``bam ci generate``.  Each bam task becomes one CI
    job that simply calls ``bam <task>``, with ``needs:`` wired from
    ``depends_on`` so the CI runner can parallelize at the job level.
    """

    model_config = ConfigDict(extra="forbid")

    provider: Literal["github-actions", "gitlab-ci"] = "github-actions"
    runner: str = "ubuntu-latest"
    python_version: str | None = None
    triggers: dict[str, Any] = Field(
        default_factory=lambda: {"push": {"branches": ["main"]}, "pull_request": None},
    )
    env: dict[str, str] = Field(default_factory=dict)


class BamConfig(BaseModel):
    """Root configuration model."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    cache: CacheConfig = Field(default_factory=CacheConfig)
    tasks: dict[str, TaskConfig] = Field(default_factory=dict)
    ci: CiConfig | None = None
