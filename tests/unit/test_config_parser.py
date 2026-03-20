"""Unit tests for configuration discovery and parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from bam_tool.config import (
    RESERVED_TASK_NAMES,
    ConfigurationError,
    discover_config_path,
    load_config,
)


def test_discover_config_in_parent_directory(sample_workspace: Path) -> None:
    """Find bam.yaml when invoked from nested directory."""
    config_path = sample_workspace / "bam.yaml"
    config_path.write_text("version: 1\n", encoding="utf-8")

    nested = sample_workspace / "apps" / "api"
    nested.mkdir(parents=True)

    discovered = discover_config_path(start_dir=nested)

    assert discovered == config_path


def test_load_config_expands_environment_variables(
    sample_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expand ${VAR} placeholders in loaded YAML values."""
    monkeypatch.setenv("BAM_GREETING", "hello")

    config_path = sample_workspace / "bam.yaml"
    config_path.write_text(
        "version: 1\n\ntasks:\n  greet:\n    command: echo ${BAM_GREETING}\n",
        encoding="utf-8",
    )

    _, config = load_config(start_dir=sample_workspace)

    assert config.tasks["greet"].command == "echo hello"


def test_bam_config_env_var_has_priority(
    sample_workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use BAM_CONFIG path before directory discovery."""
    default_config = sample_workspace / "bam.yaml"
    default_config.write_text("version: 1\n", encoding="utf-8")

    explicit_config = sample_workspace / "custom.yaml"
    explicit_config.write_text(
        "version: 1\n\ntasks:\n  from_env:\n    command: echo env\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("BAM_CONFIG", "custom.yaml")
    discovered = discover_config_path(start_dir=sample_workspace)

    assert discovered == explicit_config


def test_load_config_raises_for_invalid_yaml(sample_workspace: Path) -> None:
    """Raise ConfigurationError for malformed YAML."""
    config_path = sample_workspace / "bam.yaml"
    config_path.write_text("tasks: [\n", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(start_dir=sample_workspace)


def test_load_config_raises_for_schema_error(sample_workspace: Path) -> None:
    """Raise ConfigurationError for structurally invalid config."""
    config_path = sample_workspace / "bam.yaml"
    config_path.write_text("tasks: []\n", encoding="utf-8")

    with pytest.raises(ConfigurationError):
        load_config(start_dir=sample_workspace)


def test_reserved_task_names_contains_builtin_commands() -> None:
    """RESERVED_TASK_NAMES is now empty — no subcommands exist."""
    assert "ci" not in RESERVED_TASK_NAMES
    assert "run" not in RESERVED_TASK_NAMES
    assert "list" not in RESERVED_TASK_NAMES
    assert "validate" not in RESERVED_TASK_NAMES


def test_ordinary_task_name_not_reserved() -> None:
    """Common task names like 'build' and 'test' are not reserved."""
    assert "build" not in RESERVED_TASK_NAMES
    assert "test" not in RESERVED_TASK_NAMES
    assert "lint" not in RESERVED_TASK_NAMES


# ---------------------------------------------------------------------------
# RunnerConfig schema tests
# ---------------------------------------------------------------------------


def test_runner_config_default_is_shell() -> None:
    """RunnerConfig defaults to shell type with no image."""
    from bam_tool.config.schema import RunnerConfig

    runner = RunnerConfig()
    assert runner.type == "shell"
    assert runner.image is None


def test_runner_config_docker_requires_image() -> None:
    """Docker runner must specify an image."""
    import pydantic

    from bam_tool.config.schema import RunnerConfig

    with pytest.raises(pydantic.ValidationError, match="image"):
        RunnerConfig(type="docker")


def test_runner_config_docker_valid() -> None:
    """Docker runner with image passes validation."""
    from bam_tool.config.schema import RunnerConfig

    runner = RunnerConfig(type="docker", image="python:3.13-slim")
    assert runner.type == "docker"
    assert runner.image == "python:3.13-slim"


def test_runner_config_python_uv_valid() -> None:
    """python-uv runner needs no extra fields."""
    from bam_tool.config.schema import RunnerConfig

    runner = RunnerConfig(type="python-uv")
    assert runner.type == "python-uv"
    assert runner.image is None


def test_task_config_loads_runner_from_yaml(sample_workspace: Path) -> None:
    """Runner field is parsed from YAML and populates RunnerConfig."""
    config_path = sample_workspace / "bam.yaml"
    config_path.write_text(
        "version: 1\ntasks:\n  analyse:\n    command: print('hi')\n"
        "    runner:\n      type: python-uv\n",
        encoding="utf-8",
    )

    _, config = load_config(start_dir=sample_workspace)
    runner = config.tasks["analyse"].runner
    assert runner is not None
    assert runner.type == "python-uv"


def test_task_config_runner_defaults_to_none(sample_workspace: Path) -> None:
    """Tasks without a runner field have runner=None."""
    config_path = sample_workspace / "bam.yaml"
    config_path.write_text(
        "version: 1\ntasks:\n  lint:\n    command: ruff check .\n",
        encoding="utf-8",
    )

    _, config = load_config(start_dir=sample_workspace)
    assert config.tasks["lint"].runner is None

