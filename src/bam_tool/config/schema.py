"""Pydantic schema definitions for ``bam.yaml``."""

from __future__ import annotations

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


class BamConfig(BaseModel):
    """Root configuration model."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    cache: CacheConfig = Field(default_factory=CacheConfig)
    tasks: dict[str, TaskConfig] = Field(default_factory=dict)
