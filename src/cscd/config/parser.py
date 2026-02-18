"""Configuration discovery and parsing utilities."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from .schema import CascadeConfig

CONFIG_FILENAMES = ("cscd.yaml", ".cscd.yaml")


class ConfigurationError(Exception):
    """Raised when configuration discovery, parsing, or validation fails."""


def _expand_env(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [_expand_env(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand_env(item) for key, item in value.items()}
    return value


def _resolve_candidate(path: Path, base_dir: Path) -> Path:
    expanded = Path(os.path.expandvars(str(path))).expanduser()
    if expanded.is_absolute():
        return expanded
    return (base_dir / expanded).resolve()


def discover_config_path(
    config_path: Path | None = None,
    start_dir: Path | None = None,
) -> Path:
    """Find the config file using CLI/env/discovery priority."""
    search_root = (start_dir or Path.cwd()).resolve()

    if config_path is not None:
        resolved = _resolve_candidate(config_path, search_root)
        if resolved.is_file():
            return resolved
        raise ConfigurationError(f"Config file not found: {resolved}")

    env_config = os.getenv("CSCD_CONFIG")
    if env_config:
        resolved = _resolve_candidate(Path(env_config), search_root)
        if resolved.is_file():
            return resolved
        raise ConfigurationError(f"Config file from CSCD_CONFIG not found: {resolved}")

    for directory in (search_root, *search_root.parents):
        for filename in CONFIG_FILENAMES:
            candidate = directory / filename
            if candidate.is_file():
                return candidate

    raise ConfigurationError(
        "No cscd configuration found. Searched for 'cscd.yaml' and '.cscd.yaml' "
        f"from {search_root} upwards."
    )


def load_config(
    config_path: Path | None = None,
    start_dir: Path | None = None,
) -> tuple[Path, CascadeConfig]:
    """Load and validate Cascade configuration."""
    resolved_path = discover_config_path(config_path=config_path, start_dir=start_dir)

    try:
        raw_data = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"Invalid YAML in {resolved_path}: {exc}") from exc

    if raw_data is None:
        raw_data = {}

    if not isinstance(raw_data, dict):
        raise ConfigurationError(
            f"Invalid configuration in {resolved_path}: top-level YAML value must be a mapping."
        )

    expanded_data = _expand_env(raw_data)

    try:
        config = CascadeConfig.model_validate(expanded_data)
    except ValidationError as exc:
        raise ConfigurationError(
            f"Configuration validation failed in {resolved_path}:\n{exc}"
        ) from exc

    return resolved_path, config
