# Bam - GitHub Copilot Instructions

## Project Context

**Bam** is a content-addressed workflow orchestration tool that brings the power of content-addressable storage (CAS) to everyday development workflows. It bridges the gap between simple task runners (like Make/Just) and complex build systems (like Bazel), providing intelligent caching without forcing teams to restructure their projects.

**Tagline:** Flow naturally through your build pipeline 🌊

**⚠️ Project Status:** Concept/Experimental - NOT production-ready  
**Development Status:** Phase 1 ✅ Complete | Phase 2 ✅ Complete | Phase 3 🔄 Planned  
**Target:** Python 3.13+ (using uv package manager)  
**Primary Use Cases:** Research, experimentation, feedback gathering  
**Cache Backend:** cascache_lib (local/hybrid cache client) + cascache_server (remote CAS)

**Purpose:** This is a proof-of-concept implementation to explore content-addressed workflow orchestration patterns. It demonstrates feasibility and gathers insights for potential future production development.

## Philosophy

**Core Principles:**
1. **Flow, Don't Fight** - Work with existing tools, don't replace them
2. **Cache Everything** - Content-addressed caching for instant rebuilds
3. **Fail Gracefully** - Degrade to local when remote unavailable
4. **Progressive Complexity** - Simple tasks simple, complex tasks possible
5. **Task Output First** - Users care about tool output, not orchestration noise

**Design Tenets:**
- Declarative over imperative (YAML configuration)
- Integration over invasion (wrap existing commands)
- Local-first, remote-optional (works offline)
- Zero-config defaults with escape hatches
- Minimal bam messages, maximum task visibility

## Architecture Overview

### Layered Design

```
┌─────────────────────────────────────┐
│     CLI Layer (click/typer)         │  - User commands
│  bam run/watch/clean/graph      │  - Argument parsing
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    Workflow Manager                 │  - Config loading
│  YAML parser, task registry         │  - Task discovery
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    Task Graph (networkx)            │  - Dependency resolution
│  Topological sort, cycle detection  │  - Execution planning
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    Task Executor                    │  - Subprocess execution
│  Parallel execution, output capture │  - Status tracking
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    Cache Manager                    │  - Content hashing
│  Local + CAS backend abstraction    │  - Cache lookup/store
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    CAS Client (gRPC)                │  - Upload/download blobs
│  Connect to cascache server            │  - Authentication
└─────────────────────────────────────┘
```

### Key Components

1. **Configuration Layer** (`config/`)
   - YAML parser and validator
   - Schema definition
   - Environment variable expansion
   - Config file discovery

2. **Task Layer** (`tasks/`)
   - Task model (inputs, outputs, command, deps)
   - Task registry
   - Task validation
   - Task execution

3. **Graph Layer** (`graph/`)
   - Dependency graph builder (networkx)
   - Topological sort
   - Cycle detection
   - Graph visualization

4. **Executor Layer** (`executor/`)
   - Command execution (subprocess)
   - Parallel execution (asyncio)
   - Output handling
   - Status tracking

5. **Cache Layer** (`cache/` + `cascache_lib`)
  - Compatibility exports in `src/bam/cache/__init__.py`
  - Implementations provided by `cascache_lib`
  - Local, remote, and hybrid cache strategies
  - Content hashing and cache key computation

6. **CLI Layer** (`cli/`)
   - Command handlers
   - Output formatting (rich)
   - Progress reporting
   - Error presentation

## Code Style & Conventions

### General Python
- Use type hints everywhere (Python 3.13+ features)
- Prefer dataclasses for data structures
- Use pathlib for file operations (not os.path)
- Follow PEP 8 style guidelines
- Use descriptive variable names
- Context managers for resource management

### Async Conventions
- Use `async def` for I/O-bound operations
- Subprocess execution: `asyncio.create_subprocess_exec`
- File I/O: `aiofiles` for async file operations
- Concurrent tasks: `asyncio.gather` with proper error handling

### Configuration Format

**Preferred YAML structure:**
```yaml
# bam.yaml
version: 1

cache:
  type: cas
  url: grpc://localhost:50051
  local_fallback: true

tasks:
  build:
    inputs:
      - "src/**/*.py"
    outputs:
      - "dist/"
    command: python -m build
    
  test:
    inputs:
      - "tests/**/*.py"
      - "src/**/*.py"
    outputs: []
    command: pytest
    depends_on:
      - build
```

### Naming Conventions
- Classes: `PascalCase` (e.g., `TaskExecutor`, `CacheBackend`)
- Functions/methods: `snake_case` (e.g., `build_graph`, `execute_task`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CACHE_DIR`, `MAX_PARALLEL_TASKS`)
- Private methods: `_leading_underscore` (e.g., `_compute_hash`)
- Async functions: No special prefix (use type hints)

## Current Status & Roadmap

**Important:** For detailed implementation planning and progress tracking, always refer to `spec/roadmap.md`. This is the single source of truth for phase-by-phase task tracking, deliverables, and completion status.

### Phase 1: Core MVP ✅ COMPLETE (2026-02-12)
**Goal:** Local task runner with caching

- ✅ YAML configuration parsing with validation
- ✅ Task model with inputs, outputs, dependencies
- ✅ Dependency graph with cycle detection
- ✅ Task execution with subprocess
- ✅ Content-addressable local caching (SHA256)
- ✅ Rich CLI with colored output
- ✅ Graph visualization (ASCII + DOT)
- ✅ 85% test coverage with 101+ tests
- ✅ Complete documentation

### Phase 2: Parallelization ✅ COMPLETE (2026-02-12)
**Goal:** Parallel execution with beautiful progress display

- ✅ Async task execution with asyncio
- ✅ Parallel execution with `--jobs` flag
- ✅ Auto CPU detection (defaults to `--jobs auto`)
- ✅ Dependency-aware scheduling with semaphore pool
- ✅ Interactive tree view (Dagger-style)
  - Live progress updates with Rich
  - Hierarchical dependency visualization
  - Task states: pending, running, completed, failed
  - 30-char progress bars with percentages
- ✅ Better error context
  - Dependency chain display for failed tasks
  - List of skipped tasks due to failures
  - Clear error messages with Unicode symbols
- ✅ TTY detection for CI/CD compatibility
  - Auto-switches to plain buffered output
  - `--plain` flag for explicit control
- ✅ 101 passing tests

### Phase 3: Remote Cache Hardening (Week 4) - 🔄 NEXT
**Goal:** Harden remote caching behavior, observability, and reliability

- [ ] CacheBackend abstraction
- [ ] Refine remote/hybrid behavior via cascache_lib
- [ ] Improve retry/backoff tuning and timeout controls
- [ ] Improve metrics/observability for cache hit/miss paths
- [ ] Improve token handling and auth failure diagnostics
- [ ] Improve failure-mode fallback and user-facing errors

### Phase 4-6: See spec/roadmap.md

## Dependencies

**Core:**
- `typer>=0.12.0` - CLI framework (chosen over click)
- `pyyaml>=6.0.0` - YAML configuration
- `networkx>=3.0` - Dependency graph
- `rich>=13.0.0` - Terminal output, tree views, progress
- `pydantic>=2.0.0` - Config validation

**Async & Parallelization:**
- `asyncio` (stdlib) - Concurrent task execution

**Remote Cache Integration (Phase 3):**
- `pydantic>=2.0.0` - Config validation

**CAS Client Dependencies:**
- `grpcio>=1.64.0` - gRPC client
- `protobuf>=5.26.0` - Proto definitions (from cascache_server)

**Parallelization (Phase 3):**
- `aiofiles>=23.0.0` - Async file I/O
- `asyncio` (stdlib) - Concurrent execution

**Development:**
- `pytest>=9.0.0` - Testing
- `pytest-asyncio>=0.23.0` - Async test support
- `pytest-cov>=7.0.0` - Coverage
- `pyright>=1.1.0` - Type checking
- `ruff>=0.3.0` - Linting

## Configuration

**Environment Variables:**
- `BAM_CONFIG` - Path to bam.yaml (default: ./bam.yaml)
- `BAM_CACHE_DIR` - Local cache directory (default: ./.bam/cache)
- `BAM_CACHE_TYPE` - Cache backend: local, cas (default: local)
- `BAM_CAS_URL` - CAS server URL (default: grpc://localhost:50051)
- `BAM_CAS_TOKEN_FILE` - CAS auth token file
- `BAM_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING)
- `BAM_MAX_PARALLEL` - Max parallel tasks (default: CPU count)

**Configuration File Discovery:**
1. `--config` CLI argument
2. `BAM_CONFIG` environment variable
3. `./bam.yaml` in current directory
4. `./.bam.yaml` (hidden file)
5. Walk up directory tree to find config

## Testing Strategy

### Unit Tests (`tests/unit/`)
- Configuration parsing
- Task model validation
- Graph building and cycle detection
- Hash computation
- Cache operations
- Command execution (mocked)

### Integration Tests (`tests/integration/`)
- Full workflow execution
- Multi-task dependencies
- Cache hit/miss scenarios
- Parallel execution
- Error recovery

### Component Tests (`tests/component/`)
- CLI entrypoint and module invocation
- Version/help output behavior

### CAS Integration Tests (`tests/integration-cascache/`)
- Real cascache_server integration (optional)
- Docker-compose based test environment

**Target:** 80%+ code coverage

### Test Organization
```
tests/
  unit/
    test_cache.py
    test_cli.py
    test_config_parser.py
    test_executor.py
    test_graph_builder.py
    cache/
      test_cas_retry.py
  integration/
    test_cache_manager.py
    test_error_context.py
    test_errors.py
    test_parallel.py
    test_rich_progress.py
    test_workflows.py
  integration-cascache/
    test_cascache_integration.py
    docker-compose.yml
    run-tests.sh
  component/
    test_cli_e2e.py
  conftest.py
```

## Error Handling

**Configuration Errors:**
- Raise `ConfigurationError` for invalid YAML
- Provide helpful error messages with line numbers
- Suggest fixes for common mistakes

**Task Errors:**
- Raise `TaskDefinitionError` for invalid tasks
- Raise `TaskExecutionError` for command failures
- Include task name, command, and exit code in error

**Cache Errors:**
- Log warnings for cache failures, don't fail workflow
- Automatic fallback to local cache if CAS unavailable
- Retry logic for transient network errors

**Graph Errors:**
- Raise `CyclicDependencyError` with cycle path
- Raise `MissingTaskError` for undefined dependencies

## Development Workflow

### Project Structure
```
bam/
├── src/
│   └── bam/
│       ├── __init__.py
│       ├── __main__.py
│       ├── _version.py
│       ├── cli.py
│       ├── config/
│       │   ├── __init__.py
│       │   ├── parser.py
│       │   └── schema.py
│       ├── tasks/
│       │   ├── __init__.py
│       │   └── task.py
│       ├── graph/
│       │   ├── __init__.py
│       │   └── builder.py
│       ├── executor/
│       │   ├── __init__.py
│       │   └── executor.py
│       └── cache/
│           └── __init__.py
├── tests/
├── examples/
│   ├── hello-world/
│   ├── python-project/
│   └── multi-language/
├── spec/
│   ├── roadmap.md (detailed implementation plan - track progress here)
│   └── design.md (comprehensive design document)
├── docs/
│   ├── configuration.md
│   └── cli.md
├── .github/
│   ├── copilot-instructions.md (this file)
│   └── workflows/
│       └── ci.yml
├── pyproject.toml
├── README.md
└── justfile
```

### Common Commands
```bash
# Install dependencies
uv sync

# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=bam --cov-report=html

# Type checking
uv run pyright

# Linting
uv run ruff check src/bam

# Run bam CLI
uv run bam --help
uv run bam run build
```

## Key Design Patterns

### 1. Backend Abstraction (Cache)
```python
from abc import ABC, abstractmethod

class CacheBackend(ABC):
    @abstractmethod
  async def get(self, cache_key: str, output_paths: list[Path]) -> bool:
    """Restore cached outputs."""
    ...
    
    @abstractmethod
  async def put(self, cache_key: str, output_paths: list[Path]) -> bool:
    """Store task outputs in cache."""
    ...
    
    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if artifact is cached."""
        ...
```

### 2. Dependency Injection
```python
class WorkflowRunner:
    def __init__(
        self,
        executor: TaskExecutor,
        cache: CacheBackend,
        config: BamConfig,
    ):
        self.executor = executor
        self.cache = cache
        self.config = config
```

### 3. Dataclass Models
```python
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class Task:
    name: str
    command: str
    inputs: list[Path]
    outputs: list[Path]
    depends_on: list[str]
    env: dict[str, str]
```

### 4. Factory Pattern
```python
def create_cache_backend(config: CacheConfig) -> CacheBackend:
    if config.type == "local":
        return LocalCache(config.cache_dir)
    elif config.type == "cas":
        return CASCache(config.cas_url, config.token_file)
    else:
        raise ValueError(f"Unknown cache type: {config.type}")
```

## Integration with cascache ecosystem

### Companion Repositories
- cascache_lib: `https://gitlab.com/cascascade/cascache_lib`
- cascache_server: `https://gitlab.com/cascascade/cascache_server`

### Remote Cache Client
```python
from cascache_lib.cache import RemoteCache

cache = RemoteCache(
  cas_url="grpc://localhost:50051",
  token=None,
  timeout=30.0,
)
```

### Cache Key Format
- Same as cascache: `{sha256_hash}/{size_bytes}`
- Example: `a3f8d9...7c2e/1024`

## Performance Considerations

**Phase 1 Targets:**
- Config parsing: <100ms for typical project
- Graph building: <50ms for 100 tasks
- Cache lookup: <10ms per task
- Task execution: Overhead <50ms per task

**Phase 3 Targets (Parallel):**
- 2-4x speedup for independent tasks
- Memory: <100MB baseline + <10MB per parallel task
- No race conditions in cache operations

## Security Considerations

**Phase 1:**
- Local cache only (user's filesystem permissions)
- No authentication needed
- Command injection: validate command strings

**Phase 2 (CAS Integration):**
- Token-based authentication (reuse cascache tokens)
- TLS for gRPC connections
- Validate cache keys (prevent path traversal)
- Don't log secrets from environment

## Common Patterns

### Content Hashing
```python
import hashlib
from pathlib import Path

def compute_input_hash(inputs: list[Path], command: str) -> str:
    """Compute deterministic hash of task inputs."""
    hasher = hashlib.sha256()
    
    # Hash command first
    hasher.update(command.encode('utf-8'))
    
    # Hash input files (sorted for determinism)
    for path in sorted(inputs):
        if path.is_file():
            hasher.update(path.read_bytes())
    
    return hasher.hexdigest()
```

### Progress Reporting
```python
from rich.progress import Progress

async def execute_tasks(tasks: list[Task]) -> None:
    with Progress() as progress:
        task_progress = progress.add_task(
            "[cyan]Running tasks...", 
            total=len(tasks)
        )
        
        for task in tasks:
            await execute_task(task)
            progress.advance(task_progress)
```

### Error Context
```python
class TaskExecutionError(Exception):
    def __init__(self, task_name: str, command: str, exit_code: int):
        self.task_name = task_name
        self.command = command
        self.exit_code = exit_code
        super().__init__(
            f"Task '{task_name}' failed with exit code {exit_code}\n"
            f"Command: {command}"
        )
```

## When in Doubt

1. **Check spec/roadmap.md first** - For implementation planning, progress tracking, and phase-specific tasks
2. **Keep it simple** - Start with minimal implementation, add complexity when needed
3. **Follow YAML conventions** - Match GitHub Actions/GitLab CI patterns where possible
4. **Fail fast with helpful messages** - Better to error early with guidance than fail mysteriously
5. **Log extensively** - Debug-level logs for troubleshooting, info for user feedback
6. **Test before optimizing** - Correctness first, performance second
7. **Document decisions** - Comment non-obvious code, especially cache key computation

## Resources

- **Progress Tracking:** spec/roadmap.md (use this for tracking all implementation progress)
- **Design Doc:** spec/design.md (comprehensive design document)
- **cascache_lib:** https://gitlab.com/cascascade/cascache_lib (cache client library)
- **cascache_server:** https://gitlab.com/cascascade/cascache_server (CAS server implementation)
- **Examples:** examples/ directory
- **networkx docs:** https://networkx.org/documentation/stable/
- **Rich CLI:** https://rich.readthedocs.io/
- **gRPC Python:** https://grpc.io/docs/languages/python/

## Quick Start Commands (Future)

```bash
# Initialize new project
bam init

# List available tasks
bam list

# Run specific task
bam run build

# Run with all dependencies
bam run --with-deps test

# Watch mode (re-run on changes)
bam watch test

# Visualize task graph
bam graph --output graph.png

# Clean cache
bam clean

# Check configuration
bam validate
```

## Success Criteria

**Phase 1 Complete When:**
- [x] Can execute simple tasks with dependencies
- [x] Local cache hit rate >80% on repeated runs
- [x] Time to first run: <5 minutes with examples
- [x] Config file: <50 lines for simple project
- [x] All unit tests passing
- [x] Example projects working

**Phase 2 Complete When:**
- [x] Parallel execution with dependency awareness
- [x] Auto CPU detection and `--jobs` flag
- [x] Interactive tree view with live progress
- [x] Plain output mode for CI/CD
- [x] Better error context with dependency chains
- [x] 85+ tests passing
- [x] All quality checks passing

**Overall Success:**
- Replaces shell scripts in real projects
- Positive developer feedback
- <200ms overhead for cached tasks
- Documentation: developers productive in <30 minutes

---

**Last Updated:** 2026-02-25 (bam rename + cascache_lib integration)  
**Status:** Ready for Phase 3 Remote Cache Hardening 🚀
