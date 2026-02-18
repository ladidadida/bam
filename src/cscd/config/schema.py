"""Pydantic schema definitions for ``cscd.yaml``."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TaskConfig(BaseModel):
    """Task definition loaded from configuration."""

    model_config = ConfigDict(extra="forbid")

    command: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)


class LocalCacheConfig(BaseModel):
    """Local filesystem cache configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    path: str = ".cascade/cache"


class RemoteCacheConfig(BaseModel):
    """Remote CAS cache configuration."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = False
    type: Literal["cas"] = "cas"
    url: str = "grpc://localhost:50051"
    token_file: str | None = None
    upload: bool = True
    download: bool = True
    timeout: float = 30.0
    max_retries: int = 3  # Maximum retry attempts
    initial_backoff: float = 0.1  # Initial backoff delay in seconds


class CacheConfig(BaseModel):
    """Cache configuration with local and optional remote."""

    model_config = ConfigDict(extra="forbid")

    local: LocalCacheConfig = Field(default_factory=LocalCacheConfig)
    remote: RemoteCacheConfig = Field(default_factory=RemoteCacheConfig)


class CascadeConfig(BaseModel):
    """Root configuration model."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    cache: CacheConfig = Field(default_factory=CacheConfig)
    tasks: dict[str, TaskConfig] = Field(default_factory=dict)
