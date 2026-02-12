# Development tasks for cascade

set shell := ["bash", "-cu"]
set dotenv-load := true

default:
  @just --list

# Install development dependencies
install:
  uv sync --all-groups

# Run all tests (unit + component)
test:
  uv run pytest -v

# Run unit tests only
test-unit:
  uv run pytest -q -k "not component" tests/unit

# Run component/integration tests only
test-component:
  uv run pytest -q -m component tests/component

# Run pycas integration tests with Docker Compose
test-pycas:
  @echo "🚀 Starting pycas integration tests with Docker Compose..."
  ./tests/integration-pycas/run-tests.sh

# Run pycas integration tests (just build and up)
test-pycas-up:
  docker compose -f tests/integration-pycas/docker-compose.yml up --abort-on-container-exit --exit-code-from cascade-client

# Clean up pycas test containers
test-pycas-clean:
  docker compose -f tests/integration-pycas/docker-compose.yml down -v

# Lint with ruff
lint:
  uv run ruff check src tests

# Auto-fix lint issues
lint-fix:
  uv run ruff check --fix src tests

# Format code with ruff
format:
  uv run ruff format src tests

# Type-check with mypy
typecheck:
  uv run mypy src/cascade

# Build distribution (wheel + sdist)
build:
  uv run python -m build

# Clean build artifacts
clean:
  rm -rf build/ dist/ *.egg-info .pytest_cache .ruff_cache .pyright
  find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Run CI checks locally (lint → typecheck → test)
ci: lint typecheck test
  @echo "✓ All CI checks passed!"

# Run checks matching GitLab stages
ci-gitlab: lint typecheck test-unit test-component
  @echo "✓ GitLab CI-equivalent checks passed!"

# Create a release (bumps version, creates git tag, builds dist)
release:
  uv run semantic-release publish --no-vcs-release

