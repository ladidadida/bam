# Cascade Architecture Specification

**Version:** 1.0  
**Last Updated:** 2026-02-12  
**Status:** Phase 1 Complete

## Overview

Cascade follows a layered architecture with clear separation of concerns. Each layer has well-defined responsibilities and interfaces, making the system maintainable and testable.

## System Architecture

```
┌─────────────────────────────────────┐
│     CLI Layer (Typer + Rich)        │  Commands, output formatting
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    Configuration Parser             │  YAML loading, validation
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    Task Graph (NetworkX)            │  Dependency resolution
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    Task Executor                    │  Subprocess execution
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    Cache Manager                    │  Content hashing, storage
└─────────────────────────────────────┘
```

## Layer Details

### 1. CLI Layer

**Location:** `src/cascade/cli.py`

**Responsibilities:**
- Command parsing and argument validation
- User interaction and prompts
- Output formatting and coloring
- Progress tracking and visualization
- Error presentation

**Key Technologies:**
- Typer - CLI framework with type hints
- Rich - Terminal formatting and progress bars
- Click (via Typer) - Command structure

**Commands:**
- `cscd run [TASKS...]` - Execute tasks
- `cscd list` - Show available tasks
- `cscd graph` - Visualize dependencies
- `cscd validate` - Check configuration
- `cscd clean` - Manage cache

**Design Decisions:**
- Rich output for better UX
- Fail-fast on configuration errors
- Verbose error messages with suggestions
- Support for quiet mode (`-q`)

### 2. Configuration Layer

**Location:** `src/cascade/config/`

**Components:**
- `parser.py` - YAML parsing
- `schema.py` - Pydantic models
- `validator.py` - Validation logic
- `loader.py` - File discovery

**Responsibilities:**
- Load and parse cscd.yaml
- Validate configuration schema
- Expand environment variables
- Resolve glob patterns
- Provide default values

**Configuration Schema:**
```yaml
version: 1  # Schema version

cache:  # Optional
  type: local  # local (Phase 1), cas (Phase 2+)
  cache_dir: .cscd/cache

tasks:  # Required
  task_name:
    command: string  # Required
    inputs: list[path_pattern]  # Optional, default: []
    outputs: list[path_pattern]  # Optional, default: []
    depends_on: list[task_name]  # Optional, default: []
    env: dict[str, str]  # Optional, default: {}
    working_dir: path  # Optional, default: project root
```

**Design Decisions:**
- Pydantic for type-safe validation
- Explicit schema versioning
- Environment variable expansion: `${VAR}` or `$VAR`
- Glob pattern support via `pathlib.Path.glob()`
- Default to empty lists/dicts, not null

### 3. Task Graph Layer

**Location:** `src/cascade/graph/`

**Components:**
- `builder.py` - Graph construction
- `resolver.py` - Topological sort
- `visualizer.py` - ASCII/DOT output

**Responsibilities:**
- Build directed acyclic graph (DAG)
- Detect cycles in dependencies
- Compute execution order (topological sort)
- Resolve partial target execution
- Generate graph visualizations

**Key Technologies:**
- NetworkX - Graph data structure and algorithms

**Algorithms:**
- Cycle detection: DFS-based cycle finder
- Topological sort: Kahn's algorithm (in-degree based)
- Subgraph extraction: BFS from target tasks

**Design Decisions:**
- Fail on cycles (no automatic resolution)
- Deterministic ordering (stable sort by name)
- Support for multiple roots
- Efficient subgraph computation for partial runs

### 4. Task Executor Layer

**Location:** `src/cascade/executor/`

**Components:**
- `executor.py` - Main execution logic
- `subprocess_runner.py` - Command execution
- `environment.py` - Environment management

**Responsibilities:**
- Execute tasks in dependency order
- Manage subprocess lifecycle
- Capture stdout/stderr
- Handle exit codes
- Environment variable management
- Working directory context

**Execution Flow:**
```
For each task in topological order:
  1. Check cache (compute input hash)
  2. If cache hit:
     - Restore outputs from cache
     - Skip execution
  3. If cache miss:
     - Execute command
     - Capture output
     - Check exit code
     - Store outputs in cache
  4. If failure:
     - Stop execution
     - Report error
```

**Design Decisions:**
- Sequential execution (Phase 1)
- Fail-fast on task failure
- Environment inheritance from parent
- Task-specific env vars override parent
- Working directory per task
- Full output capture for debugging

### 5. Cache Layer

**Location:** `src/cascade/cache/`

**Components:**
- `backend.py` - Abstract interface
- `local.py` - Local filesystem cache
- `hash.py` - Content hashing
- `storage.py` - Archive operations

**Cache Backend Interface:**
```python
class CacheBackend(ABC):
    @abstractmethod
    async def get(self, cache_key: str) -> Path | None:
        """Retrieve cached artifact."""
        
    @abstractmethod
    async def put(self, cache_key: str, paths: list[Path]) -> None:
        """Store artifact in cache."""
        
    @abstractmethod
    async def exists(self, cache_key: str) -> bool:
        """Check if artifact is cached."""
        
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached artifacts."""
```

**Cache Key Computation:**
```
cache_key = SHA256(
    command +
    sorted([SHA256(input_file_content) for input_file in inputs]) +
    sorted([env_var=value for env_var, value in env.items()])
)
```

**Storage Format (Local):**
- Directory: `.cscd/cache/`
- Format: `tar.gz` archives
- Naming: `{cache_key[:8]}.tar.gz`
- Index: `index.json` with metadata

**Design Decisions:**
- Content-addressable by inputs + command
- SHA256 for cryptographic strength
- Compression (gzip) for space efficiency
- Filename uses first 8 chars of hash (collision unlikely)
- Environment vars are part of cache key
- Deterministic hash computation (sorted inputs)

## Data Flow

### Task Execution Flow

```
1. CLI receives command
   ↓
2. Load and validate config
   ↓
3. Build task graph
   ↓
4. Compute topological order
   ↓
5. For each task:
   a. Compute cache key
   b. Check cache
   c. If miss: execute + store
   d. If hit: restore outputs
   ↓
6. Report results
```

### Configuration Loading Flow

```
1. Discover config file
   (CLI arg → env var → ./cscd.yaml → walk up)
   ↓
2. Read YAML file
   ↓
3. Parse with PyYAML
   ↓
4. Validate with Pydantic
   ↓
5. Expand environment variables
   ↓
6. Resolve glob patterns
   ↓
7. Return validated Config object
```

### Cache Lookup Flow

```
1. Compute input hashes
   (read all input files, hash contents)
   ↓
2. Combine command + inputs + env
   ↓
3. Compute SHA256 cache key
   ↓
4. Check cache backend
   ↓
5a. Hit: Extract tarball to workspace
5b. Miss: Mark for execution
```

## Project Structure

```text
cascade/
├── src/cascade/
│   ├── __init__.py           # Package root
│   ├── __main__.py           # Entry point
│   ├── _version.py           # Version info
│   ├── cli.py                # CLI commands
│   │
│   ├── config/               # Configuration layer
│   │   ├── __init__.py
│   │   ├── parser.py         # YAML parsing
│   │   ├── schema.py         # Pydantic models
│   │   ├── validator.py      # Validation logic
│   │   └── loader.py         # File discovery
│   │
│   ├── tasks/                # Task models
│   │   ├── __init__.py
│   │   ├── task.py           # Task dataclass
│   │   └── registry.py       # Task storage
│   │
│   ├── graph/                # Dependency graph
│   │   ├── __init__.py
│   │   ├── builder.py        # Graph construction
│   │   ├── resolver.py       # Topological sort
│   │   └── visualizer.py     # Graph output
│   │
│   ├── executor/             # Task execution
│   │   ├── __init__.py
│   │   ├── executor.py       # Main executor
│   │   ├── subprocess_runner.py  # Command execution
│   │   └── environment.py    # Env management
│   │
│   └── cache/                # Caching system
│       ├── __init__.py
│       ├── backend.py        # Abstract interface
│       ├── local.py          # Local cache impl
│       ├── hash.py           # Content hashing
│       └── storage.py        # Archive operations
│
├── tests/
│   ├── unit/                 # Unit tests
│   │   ├── config/
│   │   ├── tasks/
│   │   ├── graph/
│   │   ├── executor/
│   │   └── cache/
│   │
│   ├── integration/          # Integration tests
│   │   ├── test_workflows.py
│   │   └── test_errors.py
│   │
│   ├── component/            # End-to-end tests
│   │   └── test_cli_e2e.py
│   │
│   └── fixtures/             # Test data
│       └── sample_configs/
│
├── examples/                 # Example projects
│   ├── hello-world/
│   ├── python-project/
│   ├── multi-language/
│   └── complex-graph/
│
├── docs/                     # User documentation
│   ├── cli.md
│   └── configuration.md
│
├── spec/                     # Technical specifications
│   ├── design.md             # Design philosophy
│   ├── roadmap.md            # Implementation plan
│   ├── architecture.md       # This file
│   └── testing.md            # Testing strategy
│
├── pyproject.toml            # Package configuration
├── pytest.ini                # Test configuration
├── pyrightconfig.json        # Type checker config
├── justfile                  # Task runner
├── LICENSE                   # MIT License
└── README.md                 # Project overview
```

## Key Technologies

### Phase 1 (Complete)

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.13+ | Main language |
| Package Manager | uv | Latest | Fast dependency management |
| CLI Framework | Typer | 0.12+ | Type-safe CLI |
| Terminal UI | Rich | 13+ | Colored output, progress |
| Config Parsing | PyYAML | 6.0+ | YAML parsing |
| Validation | Pydantic | 2.0+ | Schema validation |
| Graph Library | NetworkX | 3.0+ | Dependency graphs |
| Testing | pytest | 9.0+ | Test framework |
| Type Checking | pyright | 1.1+ | Static type checking |
| Linting | ruff | 0.3+ | Fast linting |

### Phase 2+ (Planned)

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| RPC | gRPC | 1.64+ | CAS communication |
| Async I/O | asyncio | stdlib | Parallel execution |
| Async Files | aiofiles | 23+ | Non-blocking file I/O |

## Design Principles

### 1. Separation of Concerns
- Each layer has one responsibility
- Clear interfaces between layers
- Minimal coupling

### 2. Testability
- Dependency injection for components
- Abstract interfaces for backends
- Mockable external dependencies

### 3. Type Safety
- Full type hints everywhere
- Pydantic for runtime validation
- pyright for static checking

### 4. Performance
- Lazy loading of config
- Efficient graph algorithms
- Content-addressed caching
- Minimal file I/O

### 5. Extensibility
- Abstract cache backend
- Pluggable graph visualizers
- Future: custom task executors

### 6. User Experience
- Rich terminal output
- Helpful error messages
- Progressive disclosure
- Sane defaults

### 7. Task Output Focus
- **Task output is primary:** Users care about what their tools produce (build errors, test results)
- **Cascade messages are secondary:** Orchestration messages should be minimal and unobtrusive
- **Clear separation:** Distinguish Cascade metadata from task output
- **Verbosity control:** Support different output modes for different contexts

**Output Modes:**
- `--quiet` / `-q`: Only task output, no Cascade messages
- Default: Minimal Cascade messages (task start/complete), full task output
- `--verbose` / `-v`: Include Cascade diagnostics and timing
- `--debug`: Full debug output for troubleshooting

**Implementation Guidelines:**
- Stream task stdout/stderr directly (don't buffer unnecessarily)
- Prefix Cascade messages with colored markers (e.g., `[cascade]`)
- Never interleave Cascade messages with task output
- For parallel execution: buffer task output, show complete on finish
- Provide `--format json` for machine-readable output

**Examples:**

**Good (minimal):**
```
$ cscd run test
============================= test session starts ==============================
platform linux -- Python 3.13.0, pytest-9.0.0
collected 60 items

tests/unit/test_config.py ........                                       [ 13%]
tests/unit/test_executor.py .........                                    [ 28%]
...
============================== 60 passed in 2.83s ==============================
```

**Bad (too much Cascade noise):**
```
$ cscd run test
[cascade] Loading configuration from cscd.yaml
[cascade] Validating task graph
[cascade] Computing cache keys
[cascade] Cache miss for task: test
[cascade] Executing task: test
[cascade] Task started at 2026-02-12 14:32:01
============================= test session starts ==============================
[cascade] Task output detected
...
[cascade] Task completed at 2026-02-12 14:32:04
[cascade] Storing outputs in cache
```

## Error Handling Strategy

### Configuration Errors
- **Type:** `ConfigurationError`
- **Handling:** Fail fast, show location
- **Examples:** Invalid YAML, missing required fields

### Graph Errors
- **Type:** `GraphError`
- **Handling:** Show cycle or missing dependency
- **Examples:** Cyclic dependencies, undefined tasks

### Execution Errors
- **Type:** `ExecutionError`
- **Handling:** Stop pipeline, show task output
- **Examples:** Non-zero exit code, command not found

### Cache Errors
- **Type:** `CacheError`
- **Handling:** Log warning, continue without cache
- **Examples:** Disk full, permission denied

## Performance Characteristics

### Phase 1 Benchmarks

| Operation | Target | Actual |
|-----------|--------|--------|
| Config load | <100ms | ~50ms |
| Graph build (100 tasks) | <50ms | ~30ms |
| Cache lookup | <10ms | ~5ms |
| Task overhead | <50ms | ~30ms |

### Memory Usage

- Baseline: ~50MB
- Per task: ~2MB additional
- 100-task graph: ~250MB total

### Cache Performance

- Hit rate: >90% on repeated builds
- Speedup: 10-100x for cached tasks
- Storage: ~1MB per cached artifact (compressed)

## Future Enhancements

### Phase 2: Parallel Execution
- Async task executor
- Worker pool management
- Resource constraints

### Phase 3: CAS Integration
- Remote cache backend (gRPC)
- Multi-machine sharing
- Bandwidth optimization

### Phase 4: Developer Experience
- Watch mode for incremental builds
- Interactive task selection
- Shell completion

### Phase 5: CI/CD Optimizations
- Build statistics
- Cache analytics
- Distributed execution

### Phase 6: Advanced Execution

**Docker Integration:**
- Task execution in Docker containers
- Isolated, reproducible build environments
- Custom image registry support
- Volume mounting for inputs/outputs
- Resource constraints (CPU, memory)

**Remote Execution:**
- Execute tasks on remote machines
- Artifact exchange via cascache
- SSH-based coordination
- Pre-configured remote environments
- Automatic input/output transfer
- Support for specialized hardware (GPU, large RAM)

**VSCode Integration:**
- Generate VSCode tasks.json from cscd.yaml
- Optional full VSCode extension
- Task explorer in IDE sidebar
- Graph visualization panel
- Integrated terminal execution

**CI Pipeline Generation:**
- Auto-generate CI configs (GitHub Actions, GitLab CI, Jenkins)
- Parse cscd.yaml to create optimized pipelines
- Automatic parallelization and caching strategies
- Platform-specific best practices
- Multi-platform support

**Benefits:**
- Reproducible builds across environments
- Utilize powerful remote infrastructure
- Team resource sharing
- Specialized build capabilities
- Reduced configuration effort
- IDE integration for better DX

## References

- [Design Document](design.md) - Philosophy and principles
- [Roadmap](roadmap.md) - Implementation phases
- [Testing Strategy](testing.md) - Test architecture
- [CLI Reference](../docs/cli.md) - User commands
- [Configuration Guide](../docs/configuration.md) - YAML format
