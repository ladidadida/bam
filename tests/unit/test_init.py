"""Unit tests for bam --init wizard logic."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from bam_tool.init import (
    ProjectType,
    all_project_types,
    detect_project,
    generate_config,
    label_for,
)

# ---------------------------------------------------------------------------
# detect_project
# ---------------------------------------------------------------------------


def test_detect_python_uv_with_lock(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "uv.lock").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.PYTHON_UV
    assert "uv.lock" in result.indicators


def test_detect_python_uv_pyproject_only(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.PYTHON_UV


def test_detect_python_pip(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.PYTHON


def test_detect_python_pip_with_setup(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").touch()
    (tmp_path / "setup.py").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.PYTHON
    assert "setup.py" in result.indicators


def test_detect_node_npm(tmp_path: Path) -> None:
    (tmp_path / "package.json").touch()
    (tmp_path / "package-lock.json").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.NODE
    assert "package-lock.json" in result.indicators


def test_detect_node_yarn(tmp_path: Path) -> None:
    (tmp_path / "package.json").touch()
    (tmp_path / "yarn.lock").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.NODE


def test_detect_node_package_only(tmp_path: Path) -> None:
    (tmp_path / "package.json").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.NODE


def test_detect_go(tmp_path: Path) -> None:
    (tmp_path / "go.mod").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.GO


def test_detect_rust(tmp_path: Path) -> None:
    (tmp_path / "Cargo.toml").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.RUST


def test_detect_makefile(tmp_path: Path) -> None:
    (tmp_path / "Makefile").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.MAKEFILE


def test_detect_generic_empty_dir(tmp_path: Path) -> None:
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.GENERIC
    assert result.indicators == []


def test_detect_uv_takes_priority_over_pip(tmp_path: Path) -> None:
    """pyproject.toml + requirements.txt → PYTHON_UV wins (higher priority)."""
    (tmp_path / "pyproject.toml").touch()
    (tmp_path / "requirements.txt").touch()
    result = detect_project(tmp_path)
    assert result.project_type == ProjectType.PYTHON_UV


# ---------------------------------------------------------------------------
# generate_config
# ---------------------------------------------------------------------------


def _parse(content: str) -> dict:
    return yaml.safe_load(content)  # type: ignore[no-any-return]


@pytest.mark.parametrize("project_type", list(ProjectType))
def test_generated_config_is_valid_yaml(project_type: ProjectType) -> None:
    content = generate_config(project_type)
    data = _parse(content)
    assert isinstance(data, dict)


@pytest.mark.parametrize("project_type", list(ProjectType))
def test_generated_config_has_version(project_type: ProjectType) -> None:
    data = _parse(generate_config(project_type))
    assert data["version"] == 1


@pytest.mark.parametrize("project_type", list(ProjectType))
def test_generated_config_has_tasks(project_type: ProjectType) -> None:
    data = _parse(generate_config(project_type))
    assert "tasks" in data
    assert len(data["tasks"]) >= 1


def test_python_uv_template_has_expected_tasks() -> None:
    data = _parse(generate_config(ProjectType.PYTHON_UV))
    assert set(data["tasks"]) >= {"lint", "typecheck", "test", "build"}


def test_python_uv_test_depends_on_lint_and_typecheck() -> None:
    data = _parse(generate_config(ProjectType.PYTHON_UV))
    deps = data["tasks"]["test"]["depends_on"]
    assert "lint" in deps
    assert "typecheck" in deps


def test_node_template_has_install_task() -> None:
    data = _parse(generate_config(ProjectType.NODE))
    assert "install" in data["tasks"]
    assert "outputs" in data["tasks"]["install"]


def test_rust_template_has_clippy() -> None:
    data = _parse(generate_config(ProjectType.RUST))
    assert "lint" in data["tasks"]
    assert "clippy" in data["tasks"]["lint"]["command"]


def test_generic_template_has_build_and_test() -> None:
    data = _parse(generate_config(ProjectType.GENERIC))
    assert "build" in data["tasks"]
    assert "test" in data["tasks"]


# ---------------------------------------------------------------------------
# all_project_types / label_for
# ---------------------------------------------------------------------------


def test_all_project_types_returns_all_variants() -> None:
    types = all_project_types()
    assert set(types) == set(ProjectType)


def test_label_for_all_types_non_empty() -> None:
    for pt in ProjectType:
        label = label_for(pt)
        assert label and isinstance(label, str)


def test_label_for_python_uv() -> None:
    assert label_for(ProjectType.PYTHON_UV) == "Python (uv)"
