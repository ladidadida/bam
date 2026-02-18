# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.1] - 2026-02-18

### Fixed

- GitLab CI pipeline configuration
  - Fixed gitlab ci

## [0.1.0] - 2026-02-18

### Added

- **Core Workflow Engine**
  - YAML configuration parser with validation
  - Task model with inputs, outputs, and dependencies
  - Dependency graph builder with cycle detection
  - Task execution with subprocess management
  - Content-addressable local caching (SHA256)

- **Parallel Execution**
  - Async task execution with asyncio
  - Configurable parallel jobs with `--jobs` flag
  - Auto CPU core detection (`--jobs auto`)
  - Dependency-aware scheduling with semaphore pool

- **Rich CLI Experience**
  - Interactive tree view (Dagger-style) with live progress
  - Hierarchical dependency visualization
  - Task states: pending, running, completed, failed
  - 30-char progress bars with percentages
  - TTY detection for CI/CD compatibility
  - `--plain` flag for explicit plain output mode

- **Error Handling & Context**
  - Dependency chain display for failed tasks
  - List of skipped tasks due to failures
  - Clear error messages with Unicode symbols
  - Comprehensive error recovery

- **Cache System**
  - Local content-addressable cache backend
  - Cache key computation based on inputs and commands
  - Cache hit/miss tracking
  - Automatic cache directory management

- **Graph Visualization**
  - ASCII tree visualization of task dependencies
  - DOT format export for Graphviz
  - Cycle detection and reporting

- **CLI Commands**
  - `cascade run <task>` - Run tasks with dependencies
  - `cascade list` - List available tasks
  - `cascade graph` - Visualize dependency graph
  - `cascade clean` - Clean cache and build artifacts
  - `cascade --version` - Show version information

- **Configuration Features**
  - Glob pattern support for inputs
  - Environment variable expansion
  - Task-level environment variables
  - Workspace-relative paths
  - Optional inputs/outputs

- **Quality Assurance**
  - 85% test coverage with 101 passing tests
  - Unit, integration, and component tests
  - Type checking with pyright
  - Linting with ruff
  - CI/CD pipeline (GitLab CI)

- **Documentation**
  - Comprehensive README with examples
  - CLI reference documentation
  - Configuration guide
  - Concept documentation
  - Multiple example projects

### Technical Details

- Python 3.13+ required
- Uses `typer` for CLI framework
- Uses `networkx` for dependency graphs
- Uses `rich` for terminal output
- Uses `pydantic` for configuration validation
- Uses `hatch-vcs` for version management from git tags

### Project Status

- ✅ Phase 1: Core MVP - Complete
- ✅ Phase 2: Parallelization - Complete
- 🔄 Phase 3: CAS Integration - Planned
- 📅 Phase 4+: See roadmap

[unreleased]: https://gitlab.com/cascascade/cascade/-/compare/v0.1.0...main
[0.1.0]: https://gitlab.com/cascascade/cascade/-/releases/v0.1.0
