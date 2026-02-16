# Cascade Concept Document

## ⚠️ Project Status

**Cascade is a proof-of-concept implementation exploring content-addressed workflow orchestration.**

- **Status:** Experimental / Research Project
- **Production Readiness:** NOT production-ready
- **Intended Use:** Research, experimentation, feedback gathering, concept validation
- **Development Phase:** Phase 3 Complete (Core + Parallelization + CAS Integration)

**Warning:** This project is designed to explore feasibility and gather insights for potential future production development. Use at your own risk.

## What is Cascade?

Cascade is a content-addressed workflow orchestration tool that bridges the gap between simple task runners (like Make/Just) and complex build systems (like Bazel). It provides intelligent caching without forcing teams to restructure their projects.

### The Problem

Modern development workflows face several challenges:

1. **Slow Builds:** Teams waste time rebuilding unchanged artifacts
2. **CI/CD Overhead:** Every pipeline run rebuilds everything from scratch
3. **Complex Migration:** Full build systems (Bazel, Buck2) require complete project restructuring
4. **Cache Invalidation:** Traditional tools use timestamps instead of content
5. **Distributed Teams:** No easy way to share build artifacts across machines

### The Solution

Cascade uses **content-addressable storage (CAS)** to cache task outputs based on their inputs' content hash, not timestamps. This enables:

- **Instant Cache Hits:** If inputs haven't changed, reuse cached outputs
- **Distributed Caching:** Share artifacts across team members and CI servers
- **Incremental Adoption:** Wrap existing commands without restructuring projects
- **Language Agnostic:** Works with any build tool (npm, cargo, maven, etc.)
- **Automatic Invalidation:** Content changes automatically invalidate cache

## Core Concepts

### 1. Content-Addressable Storage (CAS)

Content addressing means identifying data by its content (cryptographic hash) rather than location (path/URL).

```
Traditional: /path/to/artifact.tar.gz (location-based)
CAS: sha256:a3f8d9...7c2e/1024 (content-based)
```

**Benefits:**
- Same content = same hash → automatic deduplication
- Hash changes → content changed → cache invalidated
- Cryptographic verification of data integrity
- Location-independent addressing

**Cascade Implementation:**
- Uses SHA256 for content hashing
- Local cache fallback when remote unavailable
- Integration with pycas server for distributed caching

### 2. Task Dependencies

Tasks declare their dependencies explicitly in YAML configuration:

```yaml
tasks:
  build:
    inputs: ["src/**/*.py"]
    outputs: ["dist/"]
    command: python -m build
  
  test:
    inputs: ["tests/**/*.py", "src/**/*.py"]
    command: pytest
    depends_on: [build]  # Run after build
```

**Dependency Graph:**
- Cascade builds a directed acyclic graph (DAG) of tasks
- Topological sort ensures correct execution order
- Cycle detection prevents infinite loops
- Parallel execution of independent tasks

### 3. Cache Key Computation

Cache key = `hash(inputs + command + environment)`

```python
def compute_cache_key(task: Task) -> str:
    hasher = sha256()
    hasher.update(task.command.encode())
    for input_file in sorted(task.inputs):
        hasher.update(input_file.read_bytes())
    for key, value in sorted(task.env.items()):
        hasher.update(f"{key}={value}".encode())
    return hasher.hexdigest()
```

**Cache Lookup:**
1. Compute cache key from current inputs
2. Check local cache (`.cascade/cache/`)
3. Check remote CAS server (if configured)
4. Cache hit → restore outputs, skip execution
5. Cache miss → execute task, store outputs

### 4. Progressive Complexity

Cascade starts simple and adds complexity only when needed:

```yaml
# Simple: Just run a command
tasks:
  hello:
    command: echo "Hello, World!"

# Add caching: Declare inputs/outputs
tasks:
  build:
    inputs: ["src/**/*.py"]
    outputs: ["dist/"]
    command: python -m build

# Add dependencies: Chain tasks
tasks:
  build: { ... }
  test:
    command: pytest
    depends_on: [build]

# Add remote caching: Share with team
cache:
  remote:
    url: grpc://cache.company.com:50051
```

## Technology Stack

Cascade is built with modern Python technologies, prioritizing developer experience and type safety.

### Core Technologies

#### Python 3.13+
- **Website:** https://www.python.org/
- **Why:** Latest async features, improved error messages, better type system
- **Features Used:**
  - asyncio for parallel task execution
  - dataclasses for type-safe models
  - pathlib for cross-platform file operations
  - Type hints throughout (mypy strict mode)

#### uv Package Manager
- **Website:** https://docs.astral.sh/uv/
- **GitHub:** https://github.com/astral-sh/uv
- **Why:** 10-100x faster than pip, reliable dependency resolution
- **Features Used:**
  - Virtual environment management
  - Lock file for reproducible builds
  - Tool installation (uv tool install)

#### Typer (CLI Framework)
- **Website:** https://typer.tiangolo.com/
- **GitHub:** https://github.com/tiangolo/typer
- **Why:** Type-safe CLI with automatic help generation
- **Features Used:**
  - Command routing (run, watch, clean, graph)
  - Argument parsing with validation
  - Rich integration for beautiful output

#### Rich (Terminal Output)
- **Website:** https://rich.readthedocs.io/
- **GitHub:** https://github.com/Textualize/rich
- **Why:** Beautiful, interactive terminal UI
- **Features Used:**
  - Tree view for task hierarchy (Dagger-style)
  - Progress bars with live updates
  - Colored output with symbols (✓, ✗, ⏳)
  - Automatic TTY detection for CI/CD

#### NetworkX (Graph Library)
- **Website:** https://networkx.org/
- **GitHub:** https://github.com/networkx/networkx
- **Why:** Battle-tested graph algorithms
- **Features Used:**
  - DiGraph for task dependencies
  - Topological sort for execution order
  - Cycle detection (find_cycle)
  - Graph visualization (to_dict_of_dicts)

#### Pydantic (Configuration)
- **Website:** https://docs.pydantic.dev/
- **GitHub:** https://github.com/pydantic/pydantic
- **Why:** Type-safe configuration with validation
- **Features Used:**
  - BaseModel for config schemas
  - Field validation with constraints
  - Automatic type coercion
  - JSON schema generation

### Distributed Caching

#### gRPC
- **Website:** https://grpc.io/
- **Python Docs:** https://grpc.io/docs/languages/python/
- **Why:** Efficient binary protocol for CAS communication
- **Features Used:**
  - Bidirectional streaming (large file uploads)
  - HTTP/2 multiplexing
  - Connection pooling with keepalive
  - Status codes for error handling

#### cascache (CAS Server)
- **GitLab:** https://gitlab.com/cascascade/cascache
- **Why:** Simple, standalone CAS server compatible with Bazel/Buck2 protocols
- **Features Used:**
  - Content-addressable blob storage
  - Token-based authentication
  - Filesystem backend (S3 coming soon)
  - Metrics and health checks

### Development Tools

#### pytest (Testing)
- **Website:** https://docs.pytest.org/
- **GitHub:** https://github.com/pytest-dev/pytest
- **Coverage:** 101 tests, 85%+ code coverage
- **Features Used:**
  - Fixtures for test data
  - Parametrized tests
  - Async test support (pytest-asyncio)
  - Markers for test categories (unit, integration, pycas)

#### mypy (Type Checking)
- **Website:** https://mypy-lang.org/
- **GitHub:** https://github.com/python/mypy
- **Configuration:** Strict mode, 28 files checked
- **Benefits:**
  - Catch bugs before runtime
  - Better IDE autocomplete
  - Safer refactoring

#### ruff (Linting)
- **Website:** https://docs.astral.sh/ruff/
- **GitHub:** https://github.com/astral-sh/ruff
- **Why:** 10-100x faster than flake8, all-in-one linter+formatter
- **Rules Used:**
  - PEP 8 style guide
  - Import sorting
  - Unused imports/variables
  - Complexity checks

#### just (Task Runner)
- **Website:** https://just.systems/
- **GitHub:** https://github.com/casey/just
- **Why:** Makefile alternative with better syntax
- **Usage:** Development task automation (test, lint, run)

## Architecture Overview

Cascade uses a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────┐
│     CLI Layer (typer)               │  - User commands
│  cascade run/watch/clean/graph      │  - Argument parsing
│                                     │  - Output formatting (rich)
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    Configuration Layer              │  - YAML parsing
│  cascade.yaml discovery & parsing   │  - Schema validation (pydantic)
│                                     │  - Environment expansion
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    Task Graph (networkx)            │  - Dependency resolution
│  Build DAG, topological sort         │  - Cycle detection
│                                     │  - Execution planning
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    Task Executor (asyncio)          │  - Parallel execution
│  Subprocess management               │  - Output capture
│                                     │  - Status tracking
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    Cache Manager                    │  - Content hashing (SHA256)
│  Local + Remote hierarchy           │  - Cache lookup/store
│                                     │  - Artifact compression
└─────────────────────────────────────┘
           ↓
┌─────────────────────────────────────┐
│    CAS Client (gRPC)                │  - pycas communication
│  Upload/download blobs               │  - Retry logic
│                                     │  - Token authentication
└─────────────────────────────────────┘
```

### Key Design Patterns

1. **Backend Abstraction** - CacheBackend interface supports multiple implementations (local, CAS)
2. **Dependency Injection** - Components receive dependencies via constructor
3. **Factory Pattern** - Config-driven object creation (create_cache, create_executor)
4. **Async/Await** - Non-blocking I/O for parallel task execution
5. **Dataclasses** - Type-safe, immutable data structures

## Current Capabilities

### Phase 1 ✅ (Core MVP)
- YAML configuration with validation
- Task model with inputs, outputs, dependencies
- Dependency graph with cycle detection
- Task execution with subprocess
- Content-addressable local caching
- Rich CLI with colored output
- Graph visualization (ASCII + DOT)

### Phase 2 ✅ (Parallelization)
- Async task execution with asyncio
- Parallel execution with `--jobs` flag
- Auto CPU detection (defaults to `--jobs auto`)
- Interactive tree view (Dagger-style)
- TTY detection for CI/CD compatibility
- Better error context with dependency chains

### Phase 3 ✅ (CAS Integration)
- gRPC client for pycas server
- Remote cache with automatic fallback
- Retry logic with exponential backoff
- Connection pooling with keepalive
- Token-based authentication
- User-friendly error messages

### Test Coverage
- 101 tests passing (unit, integration, component)
- Docker-based pycas integration tests
- 85%+ code coverage
- Type safety validated with mypy

## Limitations & Future Work

### Current Limitations

1. **Not Production-Ready**
   - Limited testing at scale
   - No performance benchmarks
   - Missing advanced features (watch mode, metrics)

2. **Basic Cache Strategy**
   - No cache eviction policy
   - No compression optimization
   - No cache statistics

3. **Limited Error Recovery**
   - No circuit breaker pattern
   - Basic retry logic
   - Limited offline mode

4. **Single Remote Support**
   - Only one CAS server configured
   - No fallback between remotes
   - No multi-tier caching

### Phase 4+ Roadmap

**Phase 4: Developer Experience**
- Watch mode (re-run on file changes)
- Better caching strategies per task type
- Task timing and performance metrics
- Cache statistics CLI command
- Enhanced documentation

**Phase 5: Advanced Features**
- Streaming for large artifacts (>1MB)
- ActionCache support (cache entire command results)
- Per-task cache upload control
- Circuit breaker pattern
- Multi-remote support

**Phase 6: Production Hardening**
- Comprehensive error handling
- Performance benchmarks
- Scale testing
- Security audit
- Production deployment guide

## References & Related Work

### Similar Tools

- **Bazel** (https://bazel.build/) - Google's build system with remote caching
- **Buck2** (https://buck2.build/) - Meta's rewrite of Buck with better performance
- **Earthly** (https://earthly.dev/) - Makefile + Dockerfile hybrid with caching
- **Turborepo** (https://turbo.build/) - Monorepo tool with remote caching (JavaScript focus)
- **Nx** (https://nx.dev/) - Monorepo framework with computation caching

### Academic Background

- **Content-Addressable Storage:**
  - Git's object database model
  - IPFS (InterPlanetary File System)
  - Nix package manager

- **Build System Research:**
  - "Build Systems à la Carte" (Microsoft Research) - https://www.microsoft.com/en-us/research/publication/build-systems-la-carte/
  - "CloudBuild: Microsoft's Distributed and Caching Build Service" (ICSE 2016)

### Protocols & Standards

- **Remote Execution API** (Bazel) - https://github.com/bazelbuild/remote-apis
- **Content Addressable Storage Protocol** - https://github.com/bazelbuild/remote-apis/blob/main/build/bazel/remote/execution/v2/remote_execution.proto
- **gRPC Protocol** - https://grpc.io/docs/what-is-grpc/

## Getting Started

See [README.md](../README.md) for installation and usage instructions.

For detailed design decisions, see [spec/design.md](../spec/design.md).

For implementation roadmap, see [spec/roadmap.md](../spec/roadmap.md).

---

**Last Updated:** February 13, 2026  
**Status:** Phase 3 Complete - Functional but not production-ready  
**Contact:** For questions or feedback, open an issue on the repository
