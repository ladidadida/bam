"""Unit tests for CI pipeline generation."""

from __future__ import annotations

from typing import Literal

import yaml

from bam_tool.ci.generator import generate_pipeline
from bam_tool.config.schema import BamConfig, CiConfig, TaskConfig


def _make_config(
    tasks: dict,
    provider: Literal["github-actions", "gitlab-ci"] = "github-actions",
    python_version: str | None = None,
    env: dict | None = None,
    exclude: list | None = None,
) -> BamConfig:
    return BamConfig(
        tasks={name: TaskConfig(**spec) for name, spec in tasks.items()},
        ci=CiConfig(
            provider=provider,
            python_version=python_version,
            env=env or {},
            exclude=exclude or [],
        ),
    )


# ---------------------------------------------------------------------------
# generate_pipeline – basic contract
# ---------------------------------------------------------------------------


def test_no_ci_section_raises():
    config = BamConfig(tasks={"lint": TaskConfig(command="ruff check .")})
    try:
        generate_pipeline(config)
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "ci:" in str(exc)


def test_unknown_provider_raises():
    """Pydantic rejects unknown providers at config construction time."""
    from pydantic import ValidationError

    try:
        CiConfig(provider="circleci")  # type: ignore[arg-type]
        assert False, "expected ValidationError"
    except ValidationError as exc:
        assert "circleci" in str(exc)


# ---------------------------------------------------------------------------
# GitHub Actions
# ---------------------------------------------------------------------------


def test_github_actions_filename():
    config = _make_config({"lint": {"command": "ruff ."}})
    filename, _ = generate_pipeline(config)
    assert filename == ".github/workflows/ci.yml"


def test_github_actions_single_job():
    config = _make_config({"lint": {"command": "ruff ."}})
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert "lint" in data["jobs"]
    job = data["jobs"]["lint"]
    assert job["runs-on"] == "ubuntu-latest"
    # must have a step that runs the bam task via BAM_TOOL
    run_steps = [s for s in job["steps"] if s.get("run", "").startswith("$BAM_TOOL ")]
    assert run_steps, "missing '$BAM_TOOL lint' step"
    assert run_steps[0]["run"] == "$BAM_TOOL lint"


def test_github_actions_needs_wired():
    config = _make_config(
        {
            "lint": {"command": "ruff ."},
            "build": {"command": "python -m build", "depends_on": ["lint"]},
        }
    )
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert data["jobs"]["build"]["needs"] == ["lint"]
    assert "needs" not in data["jobs"]["lint"]


def test_github_actions_python_version_step():
    config = _make_config({"lint": {"command": "ruff ."}}, python_version="3.14")
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    steps = data["jobs"]["lint"]["steps"]
    setup_py = [s for s in steps if "setup-python" in str(s.get("uses", ""))]
    assert setup_py, "setup-python step missing"
    assert setup_py[0]["with"]["python-version"] == "3.14"


def test_github_actions_no_python_step_when_not_set():
    config = _make_config({"lint": {"command": "ruff ."}})
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    steps = data["jobs"]["lint"]["steps"]
    setup_py = [s for s in steps if "setup-python" in str(s.get("uses", ""))]
    assert not setup_py


def test_github_actions_workflow_env():
    config = _make_config({"lint": {"command": "ruff ."}}, env={"FOO": "bar"})
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert data["env"]["FOO"] == "bar"
    assert data["env"]["BAM_TOOL"] == "bam"


def test_github_actions_no_env_key_when_empty():
    config = _make_config({"lint": {"command": "ruff ."}})
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert data["env"]["BAM_TOOL"] == "bam"


# ---------------------------------------------------------------------------
# GitLab CI
# ---------------------------------------------------------------------------


def test_gitlab_ci_filename():
    config = _make_config({"lint": {"command": "ruff ."}}, provider="gitlab-ci")
    filename, _ = generate_pipeline(config)
    assert filename == ".gitlab-ci.yml"


def test_gitlab_ci_single_job():
    config = _make_config({"lint": {"command": "ruff ."}}, provider="gitlab-ci")
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    # Jobs are emitted as hidden templates — key must start with "."
    assert ".lint" in data
    job = data[".lint"]
    # No image — user provides their own
    assert "image" not in job
    # Script calls bam <task>
    assert "$BAM_TOOL lint" in job["script"]


def test_gitlab_ci_needs_wired():
    config = _make_config(
        {
            "lint": {"command": "ruff ."},
            "build": {"command": "python -m build", "depends_on": ["lint"]},
        },
        provider="gitlab-ci",
    )
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert data[".build"]["needs"] == ["lint"]
    assert "needs" not in data[".lint"]


def test_gitlab_ci_has_standard_rules():
    """Template jobs include standard MR / branch / tag rules."""
    config = _make_config({"lint": {"command": "ruff ."}}, provider="gitlab-ci")
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    rules = data[".lint"]["rules"]
    assert any("merge_request_event" in str(r) for r in rules)
    assert any("CI_COMMIT_BRANCH" in str(r) for r in rules)
    assert any("CI_COMMIT_TAG" in str(r) for r in rules)


def test_gitlab_ci_stage_field():
    """stage: is included in the template when the task declares a stage."""
    config = _make_config({"lint": {"command": "ruff .", "stage": "lint"}}, provider="gitlab-ci")
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert data[".lint"]["stage"] == "lint"


def test_gitlab_ci_stages_block():
    """stages: list is derived from task stages in declaration order."""
    config = _make_config(
        {
            "lint": {"command": "ruff .", "stage": "lint"},
            "test": {"command": "pytest", "stage": "test"},
        },
        provider="gitlab-ci",
    )
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert data["stages"] == ["lint", "test"]


def test_gitlab_ci_no_stages_when_none_set():
    """stages: is omitted when no task declares a stage."""
    config = _make_config({"lint": {"command": "ruff ."}}, provider="gitlab-ci")
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert "stages" not in data


def test_gitlab_ci_artifacts_from_outputs():
    """Task outputs are reflected in artifacts: paths."""
    config = _make_config(
        {"test": {"command": "pytest", "outputs": ["dist/", "coverage.xml"]}},
        provider="gitlab-ci",
    )
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert data[".test"]["artifacts"]["paths"] == ["dist/", "coverage.xml"]


def test_gitlab_ci_no_artifacts_when_no_outputs():
    """artifacts: is omitted when a task has no outputs."""
    config = _make_config({"lint": {"command": "ruff ."}}, provider="gitlab-ci")
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert "artifacts" not in data[".lint"]


def test_gitlab_ci_variables():
    config = _make_config(
        {"lint": {"command": "ruff ."}},
        provider="gitlab-ci",
        env={"MY_VAR": "hello"},
    )
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert data["variables"]["MY_VAR"] == "hello"
    assert data["variables"]["BAM_TOOL"] == "bam"


# ---------------------------------------------------------------------------
# ci.exclude — task filtering
# ---------------------------------------------------------------------------


def test_github_actions_exclude_removes_job():
    config = _make_config(
        {
            "lint": {"command": "ruff ."},
            "format": {"command": "ruff format ."},
            "ci-checks": {"command": "echo done"},
        },
        exclude=["format", "ci-checks"],
    )
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert "lint" in data["jobs"]
    assert "format" not in data["jobs"]
    assert "ci-checks" not in data["jobs"]


def test_github_actions_exclude_empty_keeps_all():
    config = _make_config({"lint": {"command": "ruff ."}, "test": {"command": "pytest"}})
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert "lint" in data["jobs"]
    assert "test" in data["jobs"]


def test_gitlab_ci_exclude_removes_template():
    config = _make_config(
        {
            "lint": {"command": "ruff .", "stage": "lint"},
            "ci-checks": {"command": "echo done", "stage": "lint"},
        },
        provider="gitlab-ci",
        exclude=["ci-checks"],
    )
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert ".lint" in data
    assert ".ci-checks" not in data


def test_gitlab_ci_exclude_drops_orphaned_stages():
    """A stage that becomes empty after exclusion must not appear in stages:."""
    config = _make_config(
        {
            "lint": {"command": "ruff .", "stage": "lint"},
            "local": {"command": "echo hi", "stage": "local-only"},
        },
        provider="gitlab-ci",
        exclude=["local"],
    )
    _, content = generate_pipeline(config)
    data = yaml.safe_load(content)
    assert data["stages"] == ["lint"]
    assert "local-only" not in data["stages"]
