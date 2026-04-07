# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.5.4] - 2026-04-07

### Fixed

- **`requires-python` corrected to `>=3.11`** — the package metadata incorrectly advertised `>=3.14`, preventing installation on Python 3.11–3.13 even though those versions are fully tested and supported.

## [0.5.3] - 2026-04-07

### Added

- **Interactive task mode** — tasks can be marked `interactive: true` in `bam.yaml` to run as long-lived foreground processes (dev servers, REPLs, file watchers).  Stdin / stdout / stderr are inherited from the terminal, the task is never cached, has no timeout, and Ctrl-C / SIGTERM are treated as clean exits.  All `depends_on` tasks execute normally (with caching) before the foreground process starts.
- `bam --list` now shows a `[live]` badge next to interactive tasks.
- `bam <task> --dry-run` marks interactive tasks with `[live]` in the execution plan.

## [0.5.2] - 2026-04-03

### Changed

- **Python 3.11–3.14 support** — `requires-python` broadened from `>=3.14` to `>=3.11`; removed the `cascache_server` optional dependency group (blocked older Pythons); lockfile updated with required 3.11 backport packages
- **GitLab CI matrix** — test jobs (`test-unit`, `test-integration`, `test-component`) now run across all four supported Python versions (3.11, 3.12, 3.13, 3.14) via `parallel: matrix`; `build` job `needs` updated to reference all 12 expanded matrix job names

## [0.5.1] - 2026-04-03

### Changed

- **README cleanup** — removed the "PROOF OF CONCEPT" warning banner and the 🌊 emoji from the title; reordered feature list to lead with execution and visibility features

## [0.5.0] - 2026-04-03

### Added

- **Animated spinner with elapsed time** — running tasks in the rich progress tree now show a braille spinner and elapsed seconds (e.g. `⧦ lint   5s ╻`)
- **Configurable task timeout** — tasks accept a `timeout: <seconds>` field; on expiry the task is killed (CI) or the user is prompted to continue waiting (interactive)
- **Cache-hit indicator** — tasks restored from cache show `↩ cached` in the progress tree instead of the regular completion bar
- **Buffered plain-mode output structure** — parallel plain/CI output now has clear per-task fences:
  - `──> started: task-name` printed immediately when a task begins
  - `─── task-name ────` opens the output block when the task finishes
  - `──── PASSED: task-name  Xs ────` / `──── FAILED: task-name  exit N  Xs ────` closes it
- **Timeout integration tests** — 4 new tests in `tests/integration/test_executor_timeout.py` verifying kill-on-timeout and callback behaviour

### Changed

- **Process-group kill on timeout** — subprocess now started with `start_new_session=True`; timeout uses `os.killpg` so child processes (e.g. `sleep` launched by the shell) are also killed immediately
- **pytest output style** — `console_output_style = "classic"` in `pyproject.toml` removes the `[ 77%]` progress column from pytest output
- **Timeout tests moved to integration** — the 4 executor timeout tests were moved from `tests/unit/` to `tests/integration/test_executor_timeout.py`; unit suite now runs in < 2 s
- **`except` clause syntax** — fixed Python 2-style `except Foo, Bar:` in `executor.py` to two separate `except` blocks (in Python 3 the comma form silently binds rather than catching both types)

## [0.4.1] - 2026-04-03

### Added

- **Output path validation** — config parser now checks that `outputs` entries are valid paths and raises `ConfigurationError` with a clear message on invalid values

### Changed

- **Python 3.14** — minimum Python version bumped to 3.14; project pinned to CPython 3.14.3
- **Tagline** — updated from "Flow naturally through your build pipeline" to "Fast builds, no fluff."
- **uv** updated to v0.11.3 (required to resolve CPython 3.14 releases)

## [0.4.0] - 2026-03-20

### Added

- **Execution runners** — tasks can now declare how their command is executed via a `runner:` field
  - `shell` (default) — local shell execution, backwards-compatible
  - `docker` — runs the command inside a Docker container (`image` required)
  - `python-uv` — treats the command body as an inline Python script, executed via `uv run python`
  - Runner type and image are included in the cache key so different runners never share a cache hit
  - `RunnerNotFoundError` raised pre-flight with a clear message if `docker` or `uv` is not on PATH

### Changed

- Documentation overhaul: README, CLI reference, and configuration guide updated for v0.4.0
  - PyPI install instructions corrected: `pip install bam-tool`
  - All relative links in README replaced with absolute GitLab URLs (fixes broken links on PyPI)
  - `runner` field fully documented in `docs/configuration.md`
- Release workflow added to `AGENTS.md` for reproducible future releases

### Fixed

- `RunnerNotFoundError` was silently swallowed by the broad `except Exception` handler in the executor — now propagates correctly
- Code formatting (`ruff format`) applied to executor and test files

---

## [0.3.0] - 2026-03-19

### Changed (Breaking)

- **Flat CLI interface** — tasks are now run directly as `bam <task>` instead of `bam run <task>`
  - Management commands are now flags: `--list`, `--graph`, `--validate`, `--clean`, `--ci`
  - All old subcommands (`run`, `list`, `graph`, `clean`) have been removed

### Added

- **Interactive rich tree view** — live progress display with hierarchical dependency tree (Dagger-style)
  - Task states shown inline: pending → running → ✓ done / ✗ failed
  - TTY detection; falls back to plain output in CI/non-TTY environments
  - `--plain` flag to force plain output

- **CI pipeline generator** (`--ci`)
  - Generates GitHub Actions (`.github/workflows/bam.yml`) and GitLab CI (`.gitlab/generated.gitlab-ci.yml`) from `bam.yaml`
  - `--ci-dry-run` to preview without writing
  - `$BAM_TOOL` variable in generated scripts for flexible execution

- **Shell tab completion** — `bam <TAB>` completes task names from `bam.yaml`

- **Parallel job control** — `--jobs N` / `--jobs auto` for concurrent task execution

## [0.1.1]
### Changed

- **Renamed package from `cascade` to `bam`**
  - Package name: `cascade` → `bam` (pronounced "cascade")
  - CLI command: `cascade` → `bam`
  - Config file: `bam.yaml` / `.bam.yaml` (was `cascade.yaml`)
  - Environment variables: `BAM_*` (was `CASCADE_*`)
  - Cache directory: `.bam/cache` (was `.cascade/cache`)
  - URLs: `cascascade/bam` (was `cascascade/cascade`)
  - Reason: Original "cascade" name already taken on PyPI

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

- Python 3.14+ required
- Uses `typer` for CLI framework
- Uses `networkx` for dependency graphs
- Uses `rich` for terminal output
- Uses `pydantic` for configuration validation
- Uses `hatch-vcs` for version management from git tags

### Project Status

- ✅ Phase 1: Core MVP - Complete
- ✅ Phase 2: Parallelization - Complete
- 🔄 Phase 3: Remote Cache Hardening - Planned
- 📅 Phase 4+: See roadmap

[unreleased]: https://gitlab.com/cascascade/bam/-/compare/v0.1.1...main
[0.1.1]: https://gitlab.com/cascascade/bam/-/releases/v0.1.1
[0.1.0]: https://gitlab.com/cascascade/bam/-/releases/v0.1.0
