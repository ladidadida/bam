# cscd 🌊

> **Pronounced "cascade" • Companion to cascache**

> **⚠️ PROOF OF CONCEPT - NOT PRODUCTION READY**
>
> This is a **conceptual implementation** for research and development purposes.
> While it demonstrates core CAS functionality and includes comprehensive testing,
> it is **not intended for production use**. Use at your own risk.
>
> See [docs/concept.md](docs/concept.md) for more details about the concept and technologies used.

**Flow naturally through your build pipeline**

cscd (pronounced "cascade") is a content-addressed workflow orchestration tool that brings the power of content-addressable storage to everyday development workflows. It bridges the gap between simple task runners (like Make/Just) and complex build systems (like Bazel), providing intelligent caching without forcing teams to restructure their projects.
There exists a companion server app [cascache](https://gitlab.com/cascascade/cascache_server) that is used for remote caching.

**Warning**: Large parts of this tool were generated with the help of AI. Special thanks to Claude Sonnet for the excellent support!

## ✨ Features

- **🎯 Smart Caching** - Content-addressed caching with SHA256 for instant rebuilds
- **🌐 Distributed Cache** - Share cache across team with automatic retry and fallback
- **⚡ Parallel Execution** - Auto-detect CPU cores and run independent tasks concurrently
- **🌳 Interactive Tree View** - Dagger-style dependency visualization with live progress
- **📊 Dependency Graphs** - Automatic topological sorting and cycle detection
- **🔍 Rich CLI** - Beautiful tree views, error context, and progress tracking
- **⚙️ Simple Config** - Clean YAML syntax with glob patterns and env vars
- **🛡️ Type Safe** - Full type hints with pyright validation
- **🧪 Well Tested** - 85% coverage with 101 passing tests
- **📚 Documented** - Complete CLI and configuration references

## 🚀 Quick Start

### Installation

```bash
# Using uv (recommended)
uv pip install cscd

# Using pip
pip install cscd

# From source
git clone https://gitlab.com/cascascade/cscd.git
cd cascade
uv sync
```

### Your First Workflow

Create `cscd.yaml` in your project:

```yaml
version: 1

tasks:
  build:
    command: npm run build
    inputs:
      - "src/**/*.ts"
      - "package.json"
    outputs:
      - "dist/"
  
  test:
    command: npm test
    inputs:
      - "src/**/*.ts"
      - "tests/**/*.ts"
    depends_on:
      - build
```

Run your tasks:

```bash
# Execute tasks with dependencies
cscd run test

# Parallel execution (auto-detect CPUs)
cscd run test  # defaults to parallel

# Control parallelism
cscd run test --jobs 4     # use 4 workers
cscd run test --jobs 1     # sequential

# Plain output for CI/CD
cscd run test --plain

# List available tasks
cscd list

# Visualize dependency graph
cscd graph

# Validate configuration
cscd validate
```

### Distributed Caching

Share cache across your team with a remote CAS server:

```yaml
cache:
  local:
    enabled: true
    path: .cscd/cache
  remote:
    enabled: true
    type: cas
    url: grpc://cas.example.com:50051
    token_file: ~/.cscd/cas-token
    timeout: 30.0
    max_retries: 3  # Automatic retry on transient errors
```

**Features:**
- 🔄 Automatic retry with exponential backoff
- 🔌 Connection pooling for low latency
- ⚡ Local-first strategy (check local → remote → miss)
- 🛡️ Graceful fallback to local on network errors
- 📊 Statistics tracking (future: `cascade cache stats`)

See [examples/remote-cache/](examples/remote-cache/) for complete setup guide.

## 📖 Documentation

**User Guides:**
- [Concept Document](docs/concept.md) - What is Cascade? Core concepts and technology stack
- [CLI Reference](docs/cli.md) - Complete command documentation
- [Configuration Guide](docs/configuration.md) - Full cscd.yaml reference

**Technical Specifications:**
- [Architecture](spec/architecture.md) - System design and components
- [Testing Strategy](spec/testing.md) - Test organization and practices
- [Design Document](spec/design.md) - Philosophy and principles
- [Roadmap](spec/roadmap.md) - Implementation timeline and status

## 🎯 Use Cases

### Python Project

```yaml
version: 1

tasks:
  lint:
    command: ruff check src/
    inputs: ["src/**/*.py", "pyproject.toml"]
  
  typecheck:
    command: pyright
    inputs: ["src/**/*.py"]
  
  test:
    command: pytest
    inputs: ["src/**/*.py", "tests/**/*.py"]
    depends_on: [lint, typecheck]
  
  build:
    command: python -m build
    inputs: ["src/**/*.py", "pyproject.toml"]
    outputs: ["dist/"]
    depends_on: [test]
```

### Multi-Stage Build

```yaml
version: 1

tasks:
  generate:
    command: protoc --python_out=. schema.proto
    inputs: ["schema.proto"]
    outputs: ["schema_pb2.py"]
  
  build-backend:
    command: go build -o backend cmd/server/main.go
    inputs: ["cmd/**/*.go", "*.proto"]
    outputs: ["backend"]
    depends_on: [generate]
  
  build-frontend:
    command: npm run build
    inputs: ["src/**/*.ts"]
    outputs: ["dist/"]
    depends_on: [generate]
  
  package:
    command: docker build -t myapp .
    inputs: ["backend", "dist/", "Dockerfile"]
    depends_on: [build-backend, build-frontend]
```

## 🎨 CLI Commands

### `cscd run`

Execute tasks with automatic dependency resolution and parallel execution:

```bash
# Run single task (parallel by default)
cscd run build

# Control parallelism
cscd run build --jobs 8      # use 8 workers
cscd run build --jobs auto   # auto-detect CPUs
cscd run build --jobs 1      # sequential

# Plain output for CI/CD
cscd run build --plain

# Run multiple tasks
cscd run lint test build

# Dry run (show execution plan)
cscd run --dry-run deploy

# Disable caching
cscd run --no-cache build

# Quiet mode
cscd run -q test
```

**Interactive Tree View:**

```
📦 Tasks
├── ✓ lint-css             ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
│   └── ✓ test                 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
│       └── ✓ build                ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
│           └── ✓ package              ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
├── ✓ lint-js              ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
└── ✓ lint-python          ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
    └── ✓ docs                 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

✓ Successfully executed 7 task(s)
```

**Error Context:**

When tasks fail, Cascade provides detailed context:

```
✗ Task failed: step3
  Dependency chain:
    ├─ step1
    ├─ step2
    └─ step3

⊘ Skipped 3 task(s) due to failure:
  • step4
  • step5
  • final
```

### `cscd graph`

Visualize task dependencies:

```bash
# ASCII tree output
cscd graph

# GraphViz DOT format
cscd graph --format dot > graph.dot
```

**Example Output:**

```
┌─ Roots (no dependencies)
│  ├─ setup-database
│  └─ install-deps
│
├─ Layer 1
│  ├─ lint-python
│  └─ lint-js
│
├─ Layer 2
│  ├─ test-unit
│  └─ test-integration
│
└─ Final layer
   └─ deploy
```

### `cscd validate`

Validate configuration:

```bash
cscd validate
```

Checks:
- ✅ Valid YAML syntax
- ✅ No cyclic dependencies
- ✅ All dependencies defined
- ✅ Required fields present

### `cscd clean`

Manage cache:

```bash
# Clean with confirmation
cscd clean

# Force clean
cscd clean --force
```

## 🏗️ Architecture

Cascade is built as a layered system:

**CLI → Config → Graph → Executor → Cache**

Each layer is independently testable with clear interfaces. The architecture supports local-first operation with future remote cache backends.

For detailed architecture documentation, see [spec/architecture.md](spec/architecture.md).

## 🧪 Testing

Cascade maintains high code quality with comprehensive testing:

```bash
# Run unit and integration tests
uv run pytest

# With coverage report
uv run pytest --cov=cascade --cov-report=html

# cascache integration tests (requires Docker)
./tests/integration-cascache/run-tests.sh
# Or with just:
just test-cascache
```

**Current Status:**
- 101 tests (51 unit + 47 integration + 3 component)
- 85% code coverage
- All quality checks passing
- Optional: cascache integration tests with Docker Compose

**Test Levels:**
- **Unit tests** (`tests/unit/`) - Fast, mocked dependencies
- **Integration tests** (`tests/integration/`) - Component interaction, local only
- **Component tests** (`tests/component/`) - CLI end-to-end tests
- **cascache integration** (`tests/integration-cascache/`) - Real cascache server (Docker-based)

For detailed testing strategy, see [spec/testing.md](spec/testing.md) and [tests/integration-cascache/README.md](tests/integration-cascache/README.md).

## 🛠️ Development

### Quick Setup

```bash
# Clone and install
git clone https://gitlab.com/yourusername/cascade.git
cd cascade
uv sync
```

### Common Commands

```bash
just lint        # Run linter (ruff)
just typecheck   # Type checking (pyright)
just test        # Run tests (pytest)
just test-cascache  # cascache integration tests (Docker)
just ci-gitlab   # Full CI pipeline
```

For detailed development setup and project structure, see [spec/architecture.md](spec/architecture.md).

## 📊 Status

**Phase 1: Core MVP** ✅ COMPLETE (2026-02-12)

- ✅ Task execution with dependencies
- ✅ Content-addressable caching
- ✅ YAML configuration
- ✅ Rich CLI interface
- ✅ Graph visualization
- ✅ 85% test coverage
- ✅ Complete documentation

**Phase 2: Parallelization** ✅ COMPLETE (2026-02-12)

- ✅ Async task execution
- ✅ Parallel execution with `--jobs` flag
- ✅ Auto CPU detection
- ✅ Interactive tree view with live progress
- ✅ Dependency-aware scheduling
- ✅ Better error context with dependency chains
- ✅ TTY detection for CI/CD compatibility

**Coming Soon:**
- 🔄 Phase 3: CAS Integration (remote caching with cascache)
- 🎨 Phase 4: Enhanced developer experience
- 🤖 Phase 5: CI/CD optimizations

**Future Features:**
- 🐳 Docker Integration - Run tasks in isolated containers
- 🌐 Remote Execution - Execute tasks on remote machines via cascache
- 🔌 Plugin System - Extensible architecture for custom integrations
- 📊 Web Dashboard - Real-time monitoring and analytics
- 🎨 VSCode Integration - Tasks generator or full extension
- 🤖 CI Pipeline Generation - Auto-generate GitHub Actions, GitLab CI, etc.

See [roadmap.md](spec/roadmap.md) for details.

## 🤝 Contributing

Contributions welcome! Please:

- Follow PEP 8 and project code style
- Add tests for new functionality
- Update documentation as needed
- Run quality checks before submitting

Development setup instructions in the [Development](#development) section above.

## 📝 License

MIT License - see [LICENSE](LICENSE) for details.

## 🔗 Links

**Documentation:**
- [Concept Document](docs/concept.md) - Core concepts and technology stack
- [CLI Reference](docs/cli.md) - Command documentation
- [Configuration Guide](docs/configuration.md) - YAML reference

**Specifications:**
- [Architecture](spec/architecture.md) - System design
- [Testing Strategy](spec/testing.md) - Test practices
- [Design Document](spec/design.md) - Philosophy
- [Roadmap](spec/roadmap.md) - Implementation plan

**Examples:**
- [examples/](examples/) - Sample projects

---

**Built with:** Python 3.13+ • uv • Typer • Rich • NetworkX • Pydantic
