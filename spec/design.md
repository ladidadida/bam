# Cascade - Workflow Planning Tool - Design Document

**Project Name:** Cascade 🌊  
**Tagline:** "Flow naturally through your build pipeline"  
**Status:** Design Phase  
**Date:** 2026-02-12  
**Integration:** Python CAS Server for artifact caching  
**Repository:** TBD (new separate repo recommended)

## 1. Vision & Goals

### Vision Statement
A flexible workflow planning and execution tool that integrates seamlessly into existing development environments without enforcing rigid build system concepts. Named "Cascade" because workflows flow naturally from one step to the next, like water cascading down - smooth, continuous, and following the path of least resistance.

### The Cascade Philosophy
- **Flow, don't fight:** Work with your existing tools, not against them
- **Cache everything:** Every step's output is cached by content
- **Fail gracefully:** Errors don't break the flow, they redirect it  
- **Progressive complexity:** Start with simple tasks, scale to orchestration

### Primary Goals
1. **Flexibility First:** Integrate with any developer workflow without enforcing concepts
2. **Artifact-Centric:** Define steps by their inputs and outputs, cache everything
3. **Multi-Language:** Support polyglot projects naturally
4. **Pipeline Focus:** Excel at CI/CD prep (code generation, linting) and post-build (packaging, deployment)
5. **Progressive Complexity:** Start simple, scale to complex workflows

### Non-Goals (Initially)
- Not a replacement for language-specific build tools (gradle, npm, cargo)
- Not an opinionated framework (like Rails or Django)
- Not a container orchestrator (use Docker Compose, K8s for that)

## 2. Use Cases

### Use Case 1: Pre-Build Preparation
```
Problem: CI pipeline needs to generate code, lint, format before actual build
Current: Mix of shell scripts, make targets, custom tools
Solution: Unified workflow with caching for expensive generation steps

Workflow:
1. Generate protobuf files from .proto
2. Generate OpenAPI client from spec
3. Run code formatters (black, prettier)
4. Run linters (ruff, eslint)
5. Only then: actual build (gradle, npm, cargo)
```

### Use Case 2: Post-Build Packaging
```
Problem: After successful build, need to package, sign, upload artifacts
Current: Separate CI jobs, no dependency tracking
Solution: Workflow with artifact tracking and conditional execution

Workflow:
1. Build succeeds → produce binary
2. Create Docker image from binary
3. Sign image with cosign
4. Push to registry
5. Generate SBOM
6. Update deployment manifests
```

### Use Case 3: Development Workflow Automation
```
Problem: Developers run ad-hoc commands, inconsistent environments
Current: README with copy-paste commands, tribal knowledge
Solution: Consistent, cached workflow execution

Workflow:
1. Setup: Install dependencies, generate files
2. Dev: Watch mode for tests, hot-reload
3. Check: Run full validation suite before commit
4. Deploy: Deploy to staging environment
```

### Use Case 4: Multi-Language Projects
```
Problem: Mixing Python, Go, TypeScript, Rust in one repo
Current: Each language has its own build tool, no coordination
Solution: Orchestrate language-specific tools, share artifacts

Workflow:
1. Python: Generate gRPC stubs
2. Go: Build service using generated stubs
3. TypeScript: Build frontend consuming Go API
4. Rust: Build CLI tool
5. Package: Create distribution with all components
```

## 3. Core Concepts

### 3.1 Tasks (Steps)
The fundamental unit of work. A task:
- Has a unique name
- Declares input artifacts (files, directories, environment)
- Declares output artifacts
- Executes a command or script
- Can depend on other tasks

**Example:**
```yaml
tasks:
  generate-protos:
    inputs:
      - protos/**/*.proto
    outputs:
      - src/generated/
    command: protoc --python_out=src/generated protos/**/*.proto
```

### 3.2 Artifacts
Immutable build products identified by content hash:
- Files (single file)
- Directories (recursive tree)
- Environment values (configuration)

**Artifact Tracking:**
- Compute digest of inputs (SHA256)
- Check cache for digest
- If cached: restore outputs
- If not cached: execute task, store outputs

### 3.3 Workflows
Named sequences of tasks with dependency relationships:
- Linear: A → B → C
- Parallel: A + B → C (both must complete)
- Conditional: A → B (if condition) | C (else)

**Workflow is NOT enforced:** Users define which tasks to run, tool tracks dependencies automatically.

### 3.4 Cache Integration
Uses Python CAS server as primary cache backend:
- Content-addressable: Same inputs = same hash = cache hit
- Distributed: Team shares cache via CAS server
- Fast: Local cache layer for CI performance
- Remote: Optional (fallback to local-only mode)

## 4. Configuration Format

### 4.1 Project File: `flow.yaml`

```yaml
# flow.yaml - Workflow definition
version: "1"
name: my-project

# Optional: Cache configuration
cache:
  type: cas  # or: local, disabled
  url: grpc://localhost:50051
  local_fallback: true  # Use local cache if CAS unavailable

# Optional: Default environment
env:
  NODE_ENV: development
  PYTHONPATH: src

# Task definitions
tasks:
  # Simple shell command
  install-deps:
    inputs:
      - package.json
      - package-lock.json
    outputs:
      - node_modules/
    command: npm ci

  # Multi-step task with inputs from another task
  generate-protos:
    inputs:
      - protos/**/*.proto
    outputs:
      - src/generated/proto/
    command: |
      protoc --python_out=src/generated/proto \
             --grpc_python_out=src/generated/proto \
             protos/**/*.proto
    cache: true  # Enable caching (default)

  # Task with dependencies
  lint:
    inputs:
      - src/**/*.py
      - pyproject.toml
    depends_on:
      - generate-protos  # Run after proto generation
    command: ruff check src tests
    cache: false  # Always run (fast anyway)

  # Task with environment variables
  build:
    inputs:
      - src/**/*.py
      - Dockerfile
    outputs:
      - dist/app.tar
    env:
      DOCKER_BUILDKIT: "1"
    command: |
      docker build -t myapp:latest .
      docker save myapp:latest -o dist/app.tar
    depends_on:
      - lint
      - generate-protos

  # Deployment task (not cached)
  deploy-staging:
    inputs:
      - dist/app.tar
      - deploy/staging.yaml
    command: kubectl apply -f deploy/staging.yaml
    cache: false
    depends_on:
      - build

# Named workflows (optional)
workflows:
  # Default workflow (run with: flow run)
  default:
    - install-deps
    - generate-protos
    - lint
    - build

  # CI workflow
  ci:
    - install-deps
    - generate-protos
    - lint
    - test
    - build

  # Full deployment
  deploy:
    - build
    - deploy-staging
```

### 4.2 Alternative: TOML Format

```toml
# flow.toml - Alternative format
version = "1"
name = "my-project"

[cache]
type = "cas"
url = "grpc://localhost:50051"
local_fallback = true

[tasks.install-deps]
inputs = ["package.json", "package-lock.json"]
outputs = ["node_modules/"]
command = "npm ci"

[tasks.generate-protos]
inputs = ["protos/**/*.proto"]
outputs = ["src/generated/proto/"]
command = """
protoc --python_out=src/generated/proto \
       --grpc_python_out=src/generated/proto \
       protos/**/*.proto
"""
```

## 5. CLI Design

### 5.1 Command Structure

```bash
# Initialize new project
flow init

# List available tasks
flow list

# Run specific task (with dependencies)
flow run generate-protos

# Run workflow
flow run ci

# Run multiple tasks
flow run lint test build

# Clean cache
flow clean

# Show task graph
flow graph

# Check what would run (dry-run)
flow run build --dry-run

# Force re-run (ignore cache)
flow run build --force

# Show cache statistics
flow cache stats

# Configure remote cache
flow cache config --url grpc://cas.example.com:50051
```

### 5.2 Watch Mode (Development)

```bash
# Watch for changes, auto-run tasks
flow watch test

# Watch with specific pattern
flow watch --pattern 'src/**/*.py' -- lint test
```

## 6. Execution Model

### 6.1 Task Execution Flow

```
1. Parse flow.yaml
2. Build dependency graph
3. Determine which tasks to run
4. For each task (in dependency order):
   a. Compute input digest (content hash)
   b. Check cache (CAS server or local)
   c. If cached:
      - Restore outputs from cache
      - Mark complete
   d. If not cached:
      - Execute command
      - Capture outputs
      - Store in cache
   e. Update task state
5. Report results
```

### 6.2 Caching Strategy

**Input Hashing:**
- Include file content hashes
- Include environment variable values
- Include command text

**Output Storage:**
- Tar entire output directory
- Store in CAS server as single blob
- Metadata: task name, input digest, timestamp

**Cache Lookup:**
```
digest = SHA256(inputs + command + env)
if cas.exists(digest):
    outputs = cas.get(digest)
    extract outputs
    return CACHED
else:
    run command
    capture outputs
    cas.put(digest, tar(outputs))
    return EXECUTED
```

### 6.3 Parallelization

Tasks with no dependencies run in parallel:
- Max workers: CPU count (configurable)
- Topological sort for execution order
- Wait for dependencies before starting

```
      install-deps
          |
    +-----+-----+
    |           |
  gen-protos  lint
    |           |
    +-----+-----+
          |
        build
```

## 7. Differentiators from Existing Tools

### vs. Bazel
| Feature | Bazel | FlowBuild |
|---------|-------|-----------|
| Strictness | High - requires BUILD files everywhere | Low - works with existing structure |
| Learning curve | Steep - Starlark, concepts | Gentle - YAML, shell commands |
| Language support | Built-in (Java, C++, Go) | Any (shell-based) |
| Caching | Hermetic, content-addressed | Content-addressed (via CAS) |
| Focus | Compilation | Workflows around compilation |

### vs. Just
| Feature | Just | FlowBuild |
|---------|------|-----------|
| Task definition | Simple commands | Tasks with inputs/outputs |
| Caching | None | Full content-addressed caching |
| Dependencies | Basic | Graph-based with parallelization |
| Distribution | Single binary | Python + CAS server |

### vs. Dagger
| Feature | Dagger | FlowBuild |
|---------|--------|-----------|
| Runtime | Containers (BuildKit) | Native (shell commands) |
| Portability | High (containerized) | Medium (depends on installed tools) |
| Configuration | CUE/Go/Python code | YAML/TOML (declarative) |
| Learning curve | Moderate | Low |

### vs. Make
| Feature | Make | FlowBuild |
|---------|------|-----------|
| Age | 1976 | 2026 |
| Caching | Timestamp-based (flaky) | Content-hash (reliable) |
| Parallelization | -j flag | Automatic |
| Remote cache | No | Yes (CAS server) |

## 8. Architecture

### 8.1 Components

```
┌─────────────────────────────────────────┐
│          CLI (flow)                     │
│  - Parse config                         │
│  - Build task graph                     │
│  - Execute tasks                        │
│  - Report status                        │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│       Task Executor                     │
│  - Hash inputs                          │
│  - Check cache                          │
│  - Run commands                         │
│  - Capture outputs                      │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│       Cache Manager                     │
│  - CAS client                           │
│  - Local cache (optional)               │
│  - Fallback logic                       │
└─────────────────┬───────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────┐
│    Python CAS Server (remote)           │
│  - Content-addressable storage          │
│  - Team-shared cache                    │
│  - Authentication                       │
└─────────────────────────────────────────┘
```

### 8.2 Technology Stack

**Language:** Python 3.13+  
**Reasons:**
- Fast development
- Rich ecosystem (YAML, subprocess, asyncio)
- Integrates with CAS server (already Python)
- Good CLI libraries (click, typer)

**Key Libraries:**
- `pyyaml` / `toml` - Configuration parsing
- `networkx` - Dependency graph
- `grpc` - CAS server communication (reuse from pycas)
- `rich` - Beautiful CLI output
- `watchdog` - File watching for dev mode
- `asyncio` - Parallel task execution

### 8.3 File Structure

```
flowbuild/
├── src/
│   └── flowbuild/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py              # Click/Typer CLI
│       ├── config.py           # Parse flow.yaml
│       ├── task.py             # Task model
│       ├── workflow.py         # Workflow execution
│       ├── graph.py            # Dependency graph
│       ├── cache/
│       │   ├── __init__.py
│       │   ├── base.py         # Cache interface
│       │   ├── cas.py          # CAS backend
│       │   └── local.py        # Local filesystem cache
│       ├── hasher.py           # Content hashing
│       ├── executor.py         # Task execution
│       └── watch.py            # File watching
├── tests/
├── examples/
│   ├── basic/
│   │   └── flow.yaml
│   ├── multi-language/
│   │   └── flow.yaml
│   └── ci-pipeline/
│       └── flow.yaml
├── pyproject.toml
└── README.md
```

## 9. Implementation Phases

### Phase 1: MVP (Week 1-2)
- [ ] Parse YAML config
- [ ] Build dependency graph
- [ ] Execute tasks sequentially
- [ ] Basic input/output tracking
- [ ] Local cache (no CAS yet)
- [ ] CLI: init, list, run, clean

**Deliverable:** Local-only task runner with caching

### Phase 2: CAS Integration (Week 3)
- [ ] gRPC client for CAS server
- [ ] Content-address all artifacts
- [ ] Remote cache with fallback
- [ ] Team collaboration via shared cache

**Deliverable:** Distributed caching via Python CAS

### Phase 3: Parallelization (Week 4)
- [ ] Topological sort execution
- [ ] Parallel task execution
- [ ] Max workers configuration
- [ ] Progress reporting

**Deliverable:** Fast parallel execution

### Phase 4: Developer Experience (Week 5)
- [ ] Watch mode for development
- [ ] Rich CLI output with progress bars
- [ ] Task graph visualization
- [ ] Better error messages

**Deliverable:** Great local dev experience

### Phase 5: CI/CD Features (Week 6)
- [ ] Environment variable expansion
- [ ] Conditional tasks
- [ ] Retry logic
- [ ] Timeout support
- [ ] Artifact publishing

**Deliverable:** Production-ready CI integration

## 10. Example: Complete Project

### Project Structure
```
my-service/
├── flow.yaml
├── protos/
│   ├── service.proto
│   └── types.proto
├── src/
│   ├── main.py
│   ├── generated/  # Generated by flow
│   └── api/
├── tests/
├── Dockerfile
└── deploy/
    └── k8s.yaml
```

### flow.yaml
```yaml
version: "1"
name: my-service

cache:
  type: cas
  url: grpc://cas.company.com:50051
  token_file: ~/.cas/token

tasks:
  generate-protos:
    inputs:
      - protos/**/*.proto
    outputs:
      - src/generated/
    command: |
      protoc --python_out=src/generated \
             --grpc_python_out=src/generated \
             protos/**/*.proto

  install:
    inputs:
      - pyproject.toml
      - uv.lock
    outputs:
      - .venv/
    command: uv sync

  lint:
    inputs:
      - src/**/*.py
      - tests/**/*.py
    depends_on: [generate-protos, install]
    command: uv run ruff check .

  test:
    inputs:
      - src/**/*.py
      - tests/**/*.py
    depends_on: [generate-protos, install]
    command: uv run pytest

  build:
    inputs:
      - src/**/*.py
      - Dockerfile
    outputs:
      - dist/image.tar
    depends_on: [lint, test]
    command: |
      docker build -t myservice:latest .
      docker save myservice:latest -o dist/image.tar

  deploy:
    inputs:
      - dist/image.tar
      - deploy/k8s.yaml
    depends_on: [build]
    cache: false
    command: |
      docker load -i dist/image.tar
      kubectl apply -f deploy/k8s.yaml

workflows:
  ci:
    - generate-protos
    - install
    - lint
    - test
    - build

  dev:
    - generate-protos
    - install
    - test
```

### Usage
```bash
# Developer workflow
flow run dev

# Watch mode during development
flow watch test

# CI workflow
flow run ci

# Deploy after CI pass
flow run deploy

# Check what would run
flow run build --dry-run

# See task graph
flow graph ci
```

## 11. Open Questions

1. **Error Handling:** How to handle partial failures? Retry? Fail fast?
2. **Security:** How to prevent malicious cache poisoning?
3. **Versioning:** How to handle flow.yaml format evolution?
4. **Secrets:** How to handle secrets in tasks? Environment? Vault integration?
5. **Artifacts:** Should we support artifact metadata (size, hash, creator)?
6. **Remote Execution:** Future feature - execute tasks on remote workers?
7. **Language API:** Python API for programmatic task definition?

## 12. Success Metrics

**Developer Experience:**
- Time to first successful run: <5 minutes
- Config file size: <100 lines for typical project
- Cache hit rate in CI: >80%

**Performance:**
- Overhead vs. direct command: <100ms for cache hit
- Parallel speedup: 2-4x for independent tasks
- Cache restore: <10s for typical project

**Adoption:**
- Can replace existing shell scripts without major changes
- Works alongside existing build tools (not replacement)
- Valuable even with just local cache (no CAS server required)

## 13. Next Steps

### Immediate Actions
1. ✅ **Naming decided:** Cascade
2. ⏳ **Repository setup:** Create new repository `cascade`
3. ⏳ **Initial structure:** Project skeleton with uv
4. ⏳ **Design refinement:** Finalize open questions
5. ⏳ **Prototype:** MVP implementation

### Repository Strategy

**Recommended: Separate Repository**

Create new repo: `github.com/[org]/cascade`

**Reasons:**
- Different audiences (developers vs ops)
- Independent versioning and releases  
- Clear dependency: cascade → pycas (client to server)
- Focused development and CI
- Separate documentation and examples

**Integration:**
- Cascade uses pycas as remote cache backend
- Reuse gRPC client code from pycas
- Share proto definitions
- Cross-reference documentation

**Project Structure:**
```
cascade/                    # New repository
├── src/cascade/
├── tests/
├── examples/
├── docs/
└── pyproject.toml

python-cas/                 # Existing repository
├── src/pycas/             # Server stays here
└── docs/
    └── cascade-design.md  # Planning doc (move to cascade repo later)
```

---

## 14. Detailed Roadmap

### Timeline Overview

```
Week 1-2: Core MVP        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 1
Week 3:   CAS Integration ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 2  
Week 4:   Parallelization ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 3
Week 5:   Dev Experience  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 4
Week 6:   CI/CD Features  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 5
Week 7+:  Advanced        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 6+
```

### Phase 1: Core MVP (Week 1-2) - Local Task Runner

**Goal:** Execute tasks with dependency tracking and local caching

**Day 1-2: Project Setup**
- [ ] Create new repository `cascade`
- [ ] Initialize with uv package manager
- [ ] Define project structure
- [ ] Set up testing infrastructure (pytest)
- [ ] Basic CLI framework (click/typer)
- [ ] README with vision statement

**Day 3-4: Configuration Parsing**
- [ ] Implement YAML parser for `cascade.yaml`
- [ ] Task model: inputs, outputs, command, dependencies
- [ ] Config validation
- [ ] Schema definition
- [ ] Example configurations
- [ ] Config file discovery (cascade.yaml, .cascade.yaml)

**Day 5-6: Task Graph**
- [ ] Dependency graph builder (networkx)
- [ ] Topological sort for execution order
- [ ] Cycle detection
- [ ] `cascade graph` command (visualize dependencies)
- [ ] Dry-run mode

**Day 7-9: Task Execution**
- [ ] Command executor (subprocess)
- [ ] Environment variable handling
- [ ] Working directory management
- [ ] Output capture (stdout, stderr)
- [ ] Exit code handling
- [ ] Task state tracking (pending, running, completed, failed)

**Day 10-12: Local Caching**
- [ ] Content hashing (SHA256)
- [ ] Input fingerprinting (files + command + env)
- [ ] Local cache directory structure (.cascade/cache/)
- [ ] Cache lookup and restore
- [ ] Cache storage format (tar.gz)
- [ ] `cascade clean` command

**Day 13-14: Testing & Documentation**
- [ ] Unit tests for all components
- [ ] Integration tests (full workflow execution)
- [ ] Example projects
- [ ] CLI documentation
- [ ] Configuration reference

**Deliverable:** Working task runner with local caching

```bash
# Example usage after Phase 1
cascade init
cascade list
cascade run build
cascade run build --force
cascade clean
```

---

### Phase 2: CAS Integration (Week 3) - Distributed Caching

**Goal:** Share cached artifacts via Python CAS server

**Day 1-2: CAS Client**
- [ ] gRPC client for CAS server
- [ ] Reuse proto definitions from pycas
- [ ] Connection management
- [ ] Authentication (token-based)
- [ ] Error handling and retries

**Day 3-4: Cache Backend Abstraction**
- [ ] CacheBackend interface
- [ ] LocalCache implementation (refactor from Phase 1)
- [ ] CASCache implementation  
- [ ] Cache configuration (type, url, fallback)
- [ ] Cache selection logic

**Day 5-6: Remote Cache Operations**
- [ ] Upload artifacts to CAS
- [ ] Download artifacts from CAS
- [ ] Fallback to local on CAS failure
- [ ] Cache statistics tracking
- [ ] `cascade cache stats` command

**Day 7: Testing**
- [ ] Unit tests with mock CAS server
- [ ] Integration tests with real pycas
- [ ] Multi-machine cache sharing tests
- [ ] Network failure scenarios

**Deliverable:** Team-shared distributed caching

```bash
# Configuration for CAS
cache:
  type: cas
  url: grpc://cas.company.com:50051
  token_file: ~/.cas/token
  local_fallback: true
```

---

### Phase 3: Parallelization (Week 4) - Fast Execution

**Goal:** Execute independent tasks concurrently

**Day 1-2: Parallel Executor**
- [ ] Concurrent task execution (asyncio or threading)
- [ ] Worker pool management
- [ ] Max workers configuration
- [ ] Task scheduling algorithm

**Day 3-4: Dependencies & Coordination**
- [ ] Wait for task dependencies
- [ ] Propagate failures
- [ ] Cancel dependent tasks on failure
- [ ] Resource locking (optional)

**Day 5-6: Progress Reporting**
- [ ] Real-time task status
- [ ] Rich terminal output (progress bars)
- [ ] Parallel output handling
- [ ] Summary statistics

**Day 7: Testing & Optimization**
- [ ] Stress tests (many parallel tasks)
- [ ] Benchmark speedup measurements
- [ ] Memory profiling
- [ ] Documentation updates

**Deliverable:** 2-4x speedup for independent tasks

```bash
# Example parallel execution
cascade run --jobs 4 build  # Run up to 4 tasks in parallel
cascade run --jobs auto build  # Auto-detect CPU count
```

---

### Phase 4: Developer Experience (Week 5) - Better Workflow

**Goal:** Make daily development smooth and fast

**Day 1-3: Watch Mode**
- [ ] File watching (watchdog)
- [ ] Auto-run tasks on file changes
- [ ] Debouncing (avoid rapid re-runs)
- [ ] Filtered patterns
- [ ] `cascade watch` command

**Day 4-5: Rich CLI**
- [ ] Colored output
- [ ] Progress indicators
- [ ] Better error messages with suggestions
- [ ] Task timing breakdown
- [ ] ASCII art graph visualization

**Day 6: Shell Integration**
- [ ] Shell completions (bash, zsh, fish)
- [ ] Command aliases
- [ ] Output formatting options (json, table, minimal)

**Day 7: Developer Tooling**
- [ ] `cascade init` wizard (interactive)
- [ ] Configuration validation with helpful errors
- [ ] Task templates
- [ ] Example project scaffolding

**Deliverable:** Delightful developer experience

```bash
# Watch mode examples
cascade watch test          # Re-run tests on changes
cascade watch --pattern 'src/**/*.py' -- lint test

# Better output
cascade run build --format json
cascade run build --quiet
```

---

### Phase 5: CI/CD Features (Week 6) - Production Ready

**Goal:** Ready for production CI pipelines

**Day 1-2: Environment Handling**
- [ ] Environment variable expansion in commands
- [ ] Secret handling (from env, never logged)
- [ ] Multiple environment configs (dev, staging, prod)
- [ ] `.env` file support

**Day 3-4: Advanced Task Features**
- [ ] Conditional task execution
- [ ] Task retry logic (with backoff)
- [ ] Task timeouts
- [ ] Continue-on-failure option
- [ ] Task tagging and filtering

**Day 5: CI Integration**
- [ ] GitHub Actions example
- [ ] GitLab CI example
- [ ] Jenkins integration guide
- [ ] CI-specific output formatting
- [ ] Exit codes for CI systems

**Day 6-7: Reliability Features**
- [ ] Comprehensive error recovery
- [ ] Cache corruption detection
- [ ] Network resilience
- [ ] Telemetry (optional - metrics export)
- [ ] Health checks

**Deliverable:** Production-grade CI/CD tool

```yaml
# Advanced task features
tasks:
  flaky-test:
    command: pytest integration/
    retry: 3
    timeout: 300
    continue_on_failure: true

  deploy:
    command: kubectl apply -f deploy/
    condition: branch == 'main'
    env:
      KUBECONFIG: ${{ secrets.KUBECONFIG }}
```

---

### Phase 6+: Advanced Features (Week 7+) - Optional Enhancements

**Remote Execution:**
- [ ] Execute tasks on remote workers
- [ ] Distributed task queue
- [ ] Resource allocation (CPU, memory)
- [ ] Worker management

**Language API:**
- [ ] Python API for programmatic task definition
- [ ] Task composition and reuse
- [ ] Dynamic task generation

**Plugins & Extensions:**
- [ ] Plugin system architecture
- [ ] Built-in plugins (Docker, Kubernetes, etc.)
- [ ] Community plugin registry

**Advanced Caching:**
- [ ] Incremental caching (partial updates)
- [ ] Cache compression
- [ ] Cross-platform cache sharing
- [ ] Cache analytics and insights

**Web UI:**
- [ ] Dashboard for workflow visualization
- [ ] Real-time task monitoring
- [ ] Cache statistics and management
- [ ] Historical execution data

---

## 15. Technical Decisions & Trade-offs

### Language: Python 3.13+

**✅ Pros:**
- Fast development iteration
- Rich ecosystem (YAML, async, subprocess)
- Integrates perfectly with pycas (same language)
- Excellent CLI libraries (click, rich, typer)
- Strong async support for parallel execution

**❌ Cons:**
- Slower than Go/Rust for pure execution
- Requires Python installation
- Not a single binary

**Decision: Python** - Development speed and integration with pycas outweigh performance concerns for a workflow orchestrator.

### Configuration: YAML

**✅ Pros:**
- Human-readable and widely known
- Good IDE support (IntelliSense)
- Easy for non-programmers
- Industry standard (GitHub Actions, GitLab CI, K8s)

**❌ Cons:**
- No code reuse (variables limited)
- Can become verbose
- No type safety

**Decision: YAML** - Matches user preference, best for declarative workflows. Can add Python API later for programmatic use.

### Execution: Subprocess vs Containers

**Decision: Native subprocess** (Phase 1-5)
- Works with existing tools
- No container overhead
- Simpler mental model
- Optional Docker support later

Can add containerized execution as advanced feature.

### Parallelization: asyncio vs threading

**Decision: asyncio** (Phase 3)
- Better async I/O for subprocess
- Lower memory per task
- Python 3.13+ has excellent async support
- Easier to reason about

Threading possible for CPU-bound tasks if needed.

---

## 16. Open Questions & Decisions Needed

### Critical Questions (Need answers before Phase 2)

**1. Cache Key Stability**
```
Q: How to handle non-deterministic inputs?
   - Timestamps in files
   - Random UUIDs in generated code
   - Environment-dependent paths

Options:
A) Content-only hashing (ignore metadata)
B) Explicit exclude patterns
C) Normalization layer

Decision needed: Week 1
```

**2. Failure Handling**
```
Q: What happens when task fails?
   - Stop all dependent tasks?
   - Continue independent tasks?
   - Retry automatically?

Options:
A) Default: stop dependents, continue independent
B) Configurable per-task
C) Global failure mode setting

Decision needed: Week 2
```

**3. Output Validation**
```
Q: How to ensure outputs are correct?
   - Trust exit code == 0?
   - Validate output exists?  
   - Check file patterns?

Options:
A) Basic: exit code + output exists
B) Advanced: add validation commands
C) Full: schema validation

Decision needed: Week 3
```

### Important Questions (Can defer to later phases)

**4. Workflow Composition**
```
Q: How to reuse workflows across projects?
   - Import other cascade.yaml files?
   - Package and distribute workflows?
   - Workflow registry?
```

**5. Secret Management**
```
Q: How to handle secrets securely?
   - Environment variables only?
   - Integrate with vault services?
   - Encrypted cascade.yaml sections?
```

**6. Multi-Repository Projects**
```
Q: How to orchestrate across multiple repos?
   - Monorepo only?
   - Remote task references?
   - Cascade in each repo?
```

---

## 17. Success Metrics

### Phase 1 Success Criteria
- [ ] Can execute simple tasks with dependencies
- [ ] Local cache hit rate >80% on repeated runs
- [ ] Time to first run: <5 minutes (with examples)
- [ ] Config file: <50 lines for simple project

### Phase 2 Success Criteria  
- [ ] CAS integration working (upload/download)
- [ ] Cache shared across machines
- [ ] Fallback to local on CAS failure
- [ ] Team cache hit rate: >70%

### Phase 3 Success Criteria
- [ ] 2x speedup for 4 independent tasks
- [ ] No race conditions in parallel execution
- [ ] Clean parallel output

### Overall Success
- [ ] Replaces shell scripts in 3+ real projects
- [ ] Positive developer feedback
- [ ] <200ms overhead for cached tasks
- [ ] Documentation: developers understand in <30 min

---

## 18. Documentation Plan

### User Documentation
- [ ] Getting Started Guide
- [ ] Configuration Reference (cascade.yaml)
- [ ] CLI Command Reference
- [ ] Caching Guide
- [ ] CI Integration Guide
- [ ] Troubleshooting

### Developer Documentation
- [ ] Architecture Overview
- [ ] Contributing Guide
- [ ] Plugin Development (future)
- [ ] API Reference (future)

### Examples
- [ ] Hello World (single task)
- [ ] Python Project (proto gen + test + build)
- [ ] Multi-language Project (Go + TypeScript + Rust)
- [ ] CI Pipeline (full workflow)
- [ ] Monorepo (multiple services)

---

## 19. Testing Strategy

### Unit Tests
- Configuration parsing
- Task graph building
- Hash computation
- Cache operations
- Command execution

### Integration Tests
- Full workflow execution
- Multi-task dependencies
- Cache hit/miss scenarios
- CAS server integration
- Parallel execution

### End-to-End Tests
- Real project examples
- CI pipeline simulation
- Multi-machine caching
- Error recovery

**Target: 80%+ code coverage**

---

## Appendix A: Configuration Examples

### A.1 Data Processing Pipeline
```yaml
# ETL pipeline example
tasks:
  extract:
    outputs: [data/raw/]
    command: python extract.py --source prod-db

  transform:
    inputs: [data/raw/]
    outputs: [data/processed/]
    depends_on: [extract]
    command: python transform.py

  load:
    inputs: [data/processed/]
    depends_on: [transform]
    cache: false  # Always load fresh data
    command: python load.py --target warehouse
```

### A.2 Multi-Language Monorepo
```yaml
# Polyglot project
tasks:
  build-backend:
    inputs: [backend/**/*.go]
    outputs: [dist/backend]
    command: cd backend && go build -o ../dist/backend

  build-frontend:
    inputs: [frontend/**/*.ts, frontend/package.json]
    outputs: [frontend/dist/]
    command: cd frontend && npm run build

  package:
    inputs: [dist/backend, frontend/dist/]
    outputs: [release/app.tar.gz]
    depends_on: [build-backend, build-frontend]
    command: tar czf release/app.tar.gz dist/ frontend/dist/
```

---

**Document Version:** 0.1.0  
**Last Updated:** 2026-02-12  
**Status:** Early Design - Seeking Feedback
