# Bam — Agent Instructions

> This file provides context for AI agents (GitHub Copilot, Claude, Codex, Cursor, etc.)
> working on the **bam** codebase. For end-user AI context, see [`llms.txt`](llms.txt).

## Project Context

**Bam** is a content-addressed workflow orchestration tool that brings the power of
content-addressable storage (CAS) to everyday development workflows. It bridges the gap
between simple task runners (like Make/Just) and complex build systems (like Bazel),
providing intelligent caching without forcing teams to restructure their projects.

**Tagline:** Fast builds, no fluff.

**⚠️ Project Status:** Concept/Experimental — NOT production-ready  
**Development Status:** Phase 1 ✅ | Phase 2 ✅ | Phase 3 ✅ | Phase 4 🔄 In Progress  
**Target:** Python 3.14+ (uv package manager)  
**Cache Backend:** `cascache_lib` (local/hybrid cache client) + `cascache_server` (remote CAS)

---

## Philosophy

**Core Principles:**
1. **Flow, Don't Fight** — Work with existing tools, don't replace them
2. **Cache Everything** — Content-addressed caching for instant rebuilds
3. **Fail Gracefully** — Degrade to local when remote unavailable
4. **Progressive Complexity** — Simple tasks simple, complex tasks possible
5. **Task Output First** — Users care about tool output, not orchestration noise

---

## Architecture Overview

```
┌─────────────────────────────────────┐
│     CLI Layer (typer + rich)        │  cli.py
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│    Workflow Manager                 │  config/parser.py, config/schema.py
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│    Task Graph (networkx)            │  graph/builder.py
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│    Task Executor (asyncio)          │  executor/executor.py
└─────────────┬───────────────────────┘
              ↓
┌─────────────────────────────────────┐
│    Cache Manager                    │  cache/__init__.py  (via cascache_lib)
└─────────────────────────────────────┘
```

### Module Map

| Path | Responsibility |
|------|----------------|
| `src/bam_tool/cli.py` | typer commands, rich output, progress reporting |
| `src/bam_tool/config/schema.py` | Pydantic models for `bam.yaml` |
| `src/bam_tool/config/parser.py` | YAML loading, env expansion, file discovery |
| `src/bam_tool/tasks/task.py` | Task dataclass, validation |
| `src/bam_tool/graph/builder.py` | networkx graph, topological sort, cycle detection |
| `src/bam_tool/executor/executor.py` | asyncio subprocess execution, parallel scheduling |
| `src/bam_tool/cache/__init__.py` | Compatibility exports; implementations from `cascache_lib` |
| `src/bam_tool/ci/generator.py` | GitHub Actions + GitLab CI YAML generation from task graph |
| `src/bam_tool/watcher.py` | File-system watching for `--watch` mode (watchdog) |
| `src/bam_tool/init.py` | `--init` wizard: project type detection + bam.yaml templates |

---

## Project Structure

```
bam/
├── AGENTS.md               # ← You are here
├── llms.txt                # End-user AI context file
├── src/
│   └── bam_tool/
│       ├── cli.py
│       ├── watcher.py      # --watch mode (watchdog)
│       ├── init.py         # --init wizard
│       ├── config/
│       ├── tasks/
│       ├── graph/
│       ├── executor/
│       ├── cache/
│       └── ci/             # CI pipeline generator
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── component/
│   └── integration-cascache/   # Requires running cascache_server
├── examples/
├── spec/
│   ├── roadmap.md          # ← Single source of truth for phase progress
│   └── design.md
├── docs/
│   ├── configuration.md
│   ├── cli.md
│   └── demo/               # asciinema scripts + casts
└── .github/
    └── workflows/          # CI (ci.yml, release.yml, pycas-integration.yml)
```

---

## Code Style & Conventions

- **Type hints everywhere** — Python 3.14+ features, checked with pyright
- **Pathlib** for all file operations (never `os.path`)
- **Dataclasses** for data structures
- **`async def`** for all I/O-bound operations; use `asyncio.create_subprocess_exec`
- PEP 8; `ruff` for linting

### Naming Conventions
| Item | Convention | Example |
|------|------------|---------|
| Classes | `PascalCase` | `TaskExecutor` |
| Functions/methods | `snake_case` | `build_graph` |
| Constants | `UPPER_SNAKE_CASE` | `DEFAULT_CACHE_DIR` |
| Private methods | `_leading_underscore` | `_compute_hash` |

---

## Key Design Patterns

### Backend Abstraction
```python
from abc import ABC, abstractmethod

class CacheBackend(ABC):
    @abstractmethod
    async def get(self, cache_key: str, output_paths: list[Path]) -> bool: ...

    @abstractmethod
    async def put(self, cache_key: str, output_paths: list[Path]) -> bool: ...

    @abstractmethod
    async def exists(self, key: str) -> bool: ...
```

### Dependency Injection
```python
class WorkflowRunner:
    def __init__(self, executor: TaskExecutor, cache: CacheBackend, config: BamConfig):
        ...
```

### Factory Pattern
```python
def create_cache_backend(config: CacheConfig) -> CacheBackend:
    match config.type:
        case "local": return LocalCache(config.cache_dir)
        case "cas":   return CASCache(config.cas_url, config.token_file)
```

### Content Hashing
```python
def compute_input_hash(inputs: list[Path], command: str) -> str:
    hasher = hashlib.sha256()
    hasher.update(command.encode())
    for path in sorted(inputs):
        if path.is_file():
            hasher.update(path.read_bytes())
    return hasher.hexdigest()
```

---

## Error Types

| Exception | When |
|-----------|------|
| `ConfigurationError` | Invalid YAML or missing required fields |
| `TaskDefinitionError` | Invalid task configuration |
| `TaskExecutionError` | Command non-zero exit; include task, command, exit code |
| `CyclicDependencyError` | Circular dependency; include cycle path |
| `MissingTaskError` | `depends_on` references undefined task |

Cache errors should **log warnings** and fall back gracefully — never fail the workflow.

---

## Current Roadmap Status

> Always check `spec/roadmap.md` for the authoritative phase-by-phase task list.

| Phase | Status | Goal |
|-------|--------|------|
| Phase 1 | ✅ Complete | Local task runner with caching |
| Phase 2 | ✅ Complete | Parallel execution + interactive tree view |
| Phase 3 | ✅ Complete | Remote cache hardening (cascache_lib integration) |
| Phase 4 | 🔄 In Progress | Developer experience: watch mode, init wizard, Rich CLI |

Phase 3 delivered: `CacheBackend` abstraction, `CacheManager` (local+remote), retry/backoff, token auth, graceful fallback.
Phase 4 delivered so far: `--watch`/`-w` mode (watchdog), `--init` wizard (7 templates, auto-detect).

---

## Development Commands

```bash
uv sync                                          # Install dependencies
uv run pytest                                    # Run all tests
uv run pytest --cov=bam_tool --cov-report=html   # Coverage report
uv run pyright                                   # Type checking
uv run ruff check src/bam_tool                   # Linting
uv run bam --help                                # Run CLI
```

---

## Testing Strategy

```
tests/
  unit/            # Isolated unit tests (mocked I/O)
  integration/     # Full workflow execution tests
  component/       # CLI entrypoint / module invocation
  integration-cascache/  # Real cascache_server (docker-compose, optional)
```

Target: **80%+ code coverage**. Async tests use `pytest-asyncio`.

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BAM_CONFIG` | `./bam.yaml` | Path to config file |
| `BAM_CACHE_DIR` | `./.bam/cache` | Local cache directory |
| `BAM_CACHE_TYPE` | `local` | `local` or `cas` |
| `BAM_CAS_URL` | `grpc://localhost:50051` | CAS server URL |
| `BAM_CAS_TOKEN_FILE` | — | Auth token file path |
| `BAM_LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` |
| `BAM_MAX_PARALLEL` | CPU count | Max concurrent tasks |

---

## cascache Integration

```python
from cascache_lib.cache import RemoteCache

cache = RemoteCache(
    cas_url="grpc://localhost:50051",
    token=None,
    timeout=30.0,
)
```

Cache key format: `{sha256_hex}/{size_bytes}` (e.g. `a3f8d9...7c2e/1024`)

Companion repos:
- `cascache_lib`: https://gitlab.com/cascascade/cascache_lib
- `cascache_server`: https://gitlab.com/cascascade/cascache_server

---

## Release Workflow

Follow these steps in order when cutting a new release:

### 1. Sync tags from origin

```bash
git fetch --tags origin
```

This ensures the local tag list is complete so `hatch-vcs` derives the correct
version and you don't accidentally reuse or skip a tag.

### 2. Run full CI checks

```bash
uv run bam ci-checks
```

This runs linting (`ruff`), type checking (`pyright`), and the full test suite
in one go — the same checks that run in CI. All must pass before proceeding.

To see what `ci-checks` includes:

```bash
bam --graph
```

### 3. Update documentation

- **`CHANGELOG.md`** — Add a new `## [vX.Y.Z] — YYYY-MM-DD` section with a
  summary of changes grouped by Added / Changed / Fixed / Removed.
- **`README.md`** — Update test count, feature list, and phase status if
  anything changed.
- **`docs/cli.md`** — Update the `**Version:** X.Y.Z` footer.
- **`docs/configuration.md`** — Update the `**Version:** X.Y.Z` and
  `**Last Updated:** YYYY-MM-DD` footer.
- **`AGENTS.md`** — Update `**Last Updated:**` at the bottom.

Version numbers in docs must match the new tag you are about to create.

### 4. Commit the documentation changes

```bash
git add CHANGELOG.md README.md docs/cli.md docs/configuration.md AGENTS.md
git commit -m "docs: prepare release vX.Y.Z"
```

### 5. Create an annotated tag with a release message

The tag message becomes the release note shown in GitLab / PyPI. Keep it short
but informative — one sentence summary, then a bullet list of highlights:

```bash
git tag -a vX.Y.Z -m "vX.Y.Z — <one-line summary>

## Highlights
- <change 1>
- <change 2>
- <change 3>

See CHANGELOG.md for the full list of changes."
```

Use semantic versioning (`vMAJOR.MINOR.PATCH`):
- **PATCH** — bug fixes, docs, minor improvements
- **MINOR** — new backwards-compatible features
- **MAJOR** — breaking changes

### 6. Push commits and tag

```bash
git push origin main
git push origin vX.Y.Z
```

Then mirror to GitHub:

```bash
git push github main
git push github vX.Y.Z
```

`hatch-vcs` picks up the tag automatically; the version reported by `bam --version`
and on PyPI is derived directly from it — no manual version file edits needed.

---

## Dual-Remote Setup

The repository lives on **two remotes** with different roles:

| Remote | URL | Role |
|--------|-----|------|
| `origin` | `git@gitlab.com:cascascade/bam.git` | **Primary** — active development, CI (GitLab CI), PyPI releases |
| `github` | `git@github.com:ladidadida/bam.git` | **Mirror** — GitHub Actions CI, schema publishing, future primary |

**Plan:** GitLab is currently the source of truth. The intent is to fully switch
to GitHub as the primary remote at some point. Until then, both remotes are kept
in sync manually after each meaningful push.

### Local setup

```bash
git remote -v   # should show both origin (gitlab) and github
# If github remote is missing:
git remote add github git@github.com:ladidadida/bam.git
```

### Day-to-day push

```bash
git push origin main   # push to GitLab (triggers GitLab CI)
git push github main   # mirror to GitHub (triggers GitHub Actions)
```

Or create a shell alias / git alias to push both at once:

```bash
git config alias.push-all '!git push origin "$@" && git push github "$@"'
# Then: git push-all main
```

### Tags

Always push tags to **both** remotes:

```bash
git push origin vX.Y.Z
git push github vX.Y.Z
```

Pushing the tag to `github` is what triggers the `update-schema`
`open-schemastore-pr` job in `.github/workflows/update-schema.yml`.

### CI differences

| Concern | GitLab CI (`.gitlab-ci.yml`) | GitHub Actions (`.github/workflows/`) |
|---------|-----------------------------|-----------------------------------------|
| Lint / test / build | ✅ Full matrix (Py 3.11–3.14 + free-threaded) | ✅ Single Python 3.14 |
| PyPI publish | ✅ On tag push | — |
| Schema auto-commit | ✅ `update-schema` job | ✅ `update-schema.yml` (mirror only) |
| SchemaStore PR | ✅ `open-schemastore-pr` job (on tag) | — (deferred to GitLab while it is primary) |

---

## When In Doubt

1. **Check `spec/roadmap.md` first** — authoritative source for what to implement next
2. **Keep it simple** — minimal implementation, add complexity when needed
3. **Fail fast with helpful messages** — error early with clear guidance
4. **Log extensively** — `DEBUG` for troubleshooting, `INFO` for user feedback
5. **Test before optimizing** — correctness first

**Last Updated:** 2026-04-24 (v0.6.1)
