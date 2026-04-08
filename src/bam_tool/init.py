"""``bam --init`` wizard — detect project type and generate a starter bam.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path


class ProjectType(StrEnum):
    PYTHON_UV = "python-uv"
    PYTHON = "python"
    NODE = "node"
    GO = "go"
    RUST = "rust"
    MAKEFILE = "makefile"
    GENERIC = "generic"


@dataclass
class ProjectDetection:
    """Result of auto-detecting a project type in a directory."""

    project_type: ProjectType
    indicators: list[str] = field(default_factory=list)


def detect_project(directory: Path) -> ProjectDetection:
    """Inspect *directory* and return the most likely project type.

    Detection is done in priority order — the first match wins.
    """
    checks: list[tuple[ProjectType, list[str]]] = [
        (ProjectType.PYTHON_UV, ["pyproject.toml", "uv.lock"]),
        (ProjectType.PYTHON_UV, ["pyproject.toml"]),
        (ProjectType.PYTHON, ["requirements.txt", "setup.py"]),
        (ProjectType.PYTHON, ["requirements.txt"]),
        (ProjectType.NODE, ["package.json", "package-lock.json"]),
        (ProjectType.NODE, ["package.json", "yarn.lock"]),
        (ProjectType.NODE, ["package.json"]),
        (ProjectType.GO, ["go.mod"]),
        (ProjectType.RUST, ["Cargo.toml"]),
        (ProjectType.MAKEFILE, ["Makefile"]),
    ]

    for project_type, filenames in checks:
        present = [fn for fn in filenames if (directory / fn).exists()]
        if len(present) == len(filenames):
            return ProjectDetection(project_type=project_type, indicators=present)

    return ProjectDetection(project_type=ProjectType.GENERIC, indicators=[])


# ---------------------------------------------------------------------------
# YAML templates
# ---------------------------------------------------------------------------

_HEADER = "version: 1\n\ncache:\n  local:\n    path: .bam/cache\n\ntasks:\n"

_TEMPLATES: dict[ProjectType, str] = {
    ProjectType.PYTHON_UV: _HEADER
    + """\
  lint:
    command: uv run ruff check .
    inputs:
      - "**/*.py"
      - pyproject.toml

  typecheck:
    command: uv run pyright
    inputs:
      - "**/*.py"
      - pyproject.toml

  test:
    command: uv run pytest
    inputs:
      - "**/*.py"
      - pyproject.toml
    depends_on:
      - lint
      - typecheck

  build:
    command: uv build
    inputs:
      - "**/*.py"
      - pyproject.toml
    outputs:
      - dist/
    depends_on:
      - test
""",
    ProjectType.PYTHON: _HEADER
    + """\
  lint:
    command: ruff check .
    inputs:
      - "**/*.py"

  test:
    command: pytest
    inputs:
      - "**/*.py"
    depends_on:
      - lint

  build:
    command: python -m build
    inputs:
      - "**/*.py"
      - setup.py
      - setup.cfg
      - pyproject.toml
    outputs:
      - dist/
    depends_on:
      - test
""",
    ProjectType.NODE: _HEADER
    + """\
  install:
    command: npm ci
    inputs:
      - package.json
      - package-lock.json
    outputs:
      - node_modules/

  lint:
    command: npm run lint
    inputs:
      - "src/**/*"
      - .eslintrc.*
    depends_on:
      - install

  test:
    command: npm test
    inputs:
      - "src/**/*"
      - "tests/**/*"
    depends_on:
      - lint

  build:
    command: npm run build
    inputs:
      - "src/**/*"
      - tsconfig.json
    outputs:
      - dist/
    depends_on:
      - test
""",
    ProjectType.GO: _HEADER
    + """\
  lint:
    command: go vet ./...
    inputs:
      - "**/*.go"
      - go.mod
      - go.sum

  test:
    command: go test ./...
    inputs:
      - "**/*.go"
      - go.mod
      - go.sum
    depends_on:
      - lint

  build:
    command: go build -o bin/app ./...
    inputs:
      - "**/*.go"
      - go.mod
      - go.sum
    outputs:
      - bin/
    depends_on:
      - test
""",
    ProjectType.RUST: _HEADER
    + """\
  lint:
    command: cargo clippy -- -D warnings
    inputs:
      - "src/**/*.rs"
      - Cargo.toml
      - Cargo.lock

  test:
    command: cargo test
    inputs:
      - "src/**/*.rs"
      - Cargo.toml
    depends_on:
      - lint

  build:
    command: cargo build --release
    inputs:
      - "src/**/*.rs"
      - Cargo.toml
    outputs:
      - target/release/
    depends_on:
      - test
""",
    ProjectType.MAKEFILE: _HEADER
    + """\
  build:
    command: make
    inputs:
      - Makefile
      - "**/*.c"
      - "**/*.h"
    outputs:
      - build/

  test:
    command: make test
    inputs:
      - Makefile
      - "**/*.c"
      - "**/*.h"
    depends_on:
      - build

  clean:
    command: make clean
""",
    ProjectType.GENERIC: _HEADER
    + """\
  build:
    command: echo "Replace with your build command"
    inputs: []
    outputs: []

  test:
    command: echo "Replace with your test command"
    inputs: []
    depends_on:
      - build
""",
}

_TYPE_LABELS: dict[ProjectType, str] = {
    ProjectType.PYTHON_UV: "Python (uv)",
    ProjectType.PYTHON: "Python (pip)",
    ProjectType.NODE: "Node.js",
    ProjectType.GO: "Go",
    ProjectType.RUST: "Rust",
    ProjectType.MAKEFILE: "Makefile",
    ProjectType.GENERIC: "Generic",
}


def generate_config(project_type: ProjectType) -> str:
    """Return the YAML content for *project_type*."""
    return _TEMPLATES[project_type]


def all_project_types() -> list[ProjectType]:
    return list(ProjectType)


def label_for(project_type: ProjectType) -> str:
    return _TYPE_LABELS[project_type]
