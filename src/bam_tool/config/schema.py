"""Pydantic schema definitions for ``bam.yaml``."""

from __future__ import annotations

from typing import Any, Literal

from cascache_lib.config import CacheConfig
from pydantic import BaseModel, ConfigDict, Field, model_validator


class RunnerConfig(BaseModel):
    """Runner configuration for a task.

    Controls *how* the task command is executed.  Three types are supported:

    * ``shell`` (default) — run the command in a local shell, unchanged.
    * ``docker`` — run the command inside a Docker container (requires ``image``).
    * ``python-uv`` — treat the command body as an inline Python script and
      execute it via ``uv run python``.
    """

    model_config = ConfigDict(extra="forbid")

    type: Literal["shell", "docker", "python-uv"] = "shell"
    image: str | None = None

    @model_validator(mode="after")
    def _image_required_for_docker(self) -> RunnerConfig:
        if self.type == "docker" and not self.image:
            raise ValueError("runner.image is required when type is 'docker'")
        return self


class TaskConfig(BaseModel):
    """Task definition loaded from configuration."""

    model_config = ConfigDict(extra="forbid")

    command: str
    runner: RunnerConfig | None = None
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
