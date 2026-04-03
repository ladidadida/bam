# bam

**Fast builds, no fluff.**

bam is a content-addressed workflow orchestration tool that brings the power of content-addressable storage to everyday development workflows. It bridges the gap between simple task runners (like Make/Just) and complex build systems (like Bazel), providing intelligent caching without forcing teams to restructure their projects.

bam utilizes its partner projects [cascache_lib](https://gitlab.com/cascascade/cascache_lib) and [cascache_server](https://gitlab.com/cascascade/cascache_server) that implement local and remote CAS caching.

**Warning**: Large parts of this tool were generated with the help of AI. Special thanks to Claude Sonnet for the excellent support!

## ✨ Features

- **⚡ Parallel Execution** - Auto-detect CPU cores and run independent tasks concurrently
- **🌳 Interactive Tree View** - Dagger-style dependency visualization with live progress
- **📊 Dependency Graphs** - Automatic topological sorting and cycle detection
- **🔍 Rich CLI** - Beautiful tree views, error context, and progress tracking
- **⚙️ Simple Config** - Clean YAML syntax with glob patterns and env vars
- **🎯 Smart Caching** - Content-addressed caching with SHA256 for instant rebuilds
- **🌐 Distributed Cache** - Share cache across team with automatic retry and fallback
- **� Runner Support** - Run tasks in Docker containers or as inline Python scripts
- **🤖 CI Generation** - Auto-generate GitHub Actions and GitLab CI pipelines
- **🛡️ Type Safe** - Full type hints with pyright validation
- **🧪 Well Tested** - 137 passing tests
- **📚 Documented** - Complete CLI and configuration references

## 🚀 Quick Start

### Installation

```bash
# Using uv (recommended)
uv pip install bam-tool

# Using pip
pip install bam-tool

# From source
git clone https://gitlab.com/cascascade/bam.git
cd bam
uv sync
```

### Your First Workflow

Create `bam.yaml` in your project:

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
# Execute a task (and all its dependencies)
bam test

# Parallel execution (auto-detect CPUs)
bam test                 # parallel by default
bam test --jobs 4        # use 4 workers
bam test --jobs 1        # sequential

# Plain output for CI/CD
bam test --plain

# List available tasks
bam --list

# Visualize dependency graph
bam --graph

# Validate configuration
bam --validate
```

### Distributed Caching

Share cache across your team with a remote CAS server:

```yaml
cache:
  local:
    enabled: true
    path: .bam/cache
  remote:
    enabled: true
    type: cas
    url: grpc://cas.example.com:50051
    token_file: ~/.bam/cas-token
    timeout: 30.0
    max_retries: 3  # Automatic retry on transient errors
```

**Features:**
- 🔄 Automatic retry with exponential backoff
- 🔌 Connection pooling for low latency
- ⚡ Local-first strategy (check local → remote → miss)
- 🛡️ Graceful fallback to local on network errors
- 📊 Statistics tracking (future: `bam cache stats`)

See [examples/remote-cache/](https://gitlab.com/cascascade/bam/-/tree/main/examples/remote-cache/) for complete setup guide.

## 📖 Documentation

**User Guides:**
- [Concept Document](https://gitlab.com/cascascade/bam/-/blob/main/docs/concept.md) - What is bam? Core concepts and technology stack
- [CLI Reference](https://gitlab.com/cascascade/bam/-/blob/main/docs/cli.md) - Complete command documentation
- [Configuration Guide](https://gitlab.com/cascascade/bam/-/blob/main/docs/configuration.md) - Full bam.yaml reference

**Technical Specifications:**
- [Architecture](https://gitlab.com/cascascade/bam/-/blob/main/spec/architecture.md) - System design and components
- [Testing Strategy](https://gitlab.com/cascascade/bam/-/blob/main/spec/testing.md) - Test organization and practices
- [Design Document](https://gitlab.com/cascascade/bam/-/blob/main/spec/design.md) - Philosophy and principles
- [Roadmap](https://gitlab.com/cascascade/bam/-/blob/main/spec/roadmap.md) - Implementation timeline and status

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

## 🎨 CLI Reference

bam uses a **flat command interface** — tasks are run directly as `bam <task>`,
and management operations are flags.

### Running Tasks

```bash
# Run a task (and all its dependencies)
bam build

# Control parallelism
bam build --jobs 8      # use 8 workers
bam build --jobs auto   # auto-detect CPUs (default)
bam build --jobs 1      # sequential

# Dry run (show execution plan without running)
bam build --dry-run

# Disable caching
bam build --no-cache

# Quiet mode
bam build -q

# Plain output for CI/CD
bam build --plain
```

**Interactive Tree View:**

```
📦 Tasks
├── ✓ lint               ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
├── ✓ typecheck          ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
│   └── ✓ test           ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
│       └── ✓ build      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

✓ Successfully executed 4 task(s)
```

**Error Context:**

When tasks fail, bam shows the full dependency chain and which tasks were skipped:

```
✗ Task failed: test
  Dependency chain:
    ├─ lint
    ├─ typecheck
    └─ test

⊘ Skipped 1 task(s) due to failure:
  • build
```

### Management Flags

```bash
bam --list              # List all configured tasks
bam --validate          # Validate config (YAML, deps, cycles)
bam --graph             # Show ASCII dependency graph
bam --graph-dot         # Output DOT format (pipe to Graphviz)
bam --clean             # Clean cache (prompts for confirmation)
bam --clean-force       # Clean cache without confirmation
bam --dry-run           # Show execution plan (no task specified)
bam --version           # Show version
```

### CI Pipeline Generation

```bash
bam --ci                # Generate CI pipeline (writes file)
bam --ci-dry-run        # Preview CI YAML without writing
bam --ci-output FILE    # Write to custom path
```

### Global Options

```bash
--config PATH           # Path to bam.yaml (default: auto-discover)
--jobs N / auto         # Parallel workers (default: auto)
--no-cache              # Disable caching for this run
--dry-run               # Show plan without running
--quiet, -q             # Suppress output
--plain                 # Force plain output (no rich UI)
```

## 🏗️ Architecture

bam is built as a layered system:

**CLI → Config → Graph → Executor → Cache**

Each layer is independently testable with clear interfaces. The architecture supports local-first operation with future remote cache backends.

For detailed architecture documentation, see [spec/architecture.md](https://gitlab.com/cascascade/bam/-/blob/main/spec/architecture.md).

## 🧪 Testing

bam maintains high code quality with comprehensive testing:

```bash
# Run unit and integration tests
uv run pytest

# With coverage report
uv run pytest --cov=bam_tool --cov-report=html

# cascache integration tests (requires Docker)
./tests/integration-cascache/run-tests.sh
```

**Current Status:**
- 137 passing tests
- Unit, integration, and component test levels
- Optional: cascache integration tests with Docker Compose

**Test Levels:**
- **Unit tests** (`tests/unit/`) - Fast, mocked dependencies
- **Integration tests** (`tests/integration/`) - Component interaction, local only
- **Component tests** (`tests/component/`) - CLI end-to-end tests
- **cascache integration** (`tests/integration-cascache/`) - Real cascache server (Docker-based)

For detailed testing strategy, see [spec/testing.md](https://gitlab.com/cascascade/bam/-/blob/main/spec/testing.md) and [tests/integration-cascache/README.md](https://gitlab.com/cascascade/bam/-/blob/main/tests/integration-cascache/README.md).

## 🛠️ Development

### Quick Setup

```bash
# Clone and install
git clone https://gitlab.com/cascascade/bam.git
cd bam
uv sync
```

### Common Commands

```bash
uv run ruff check src tests     # Lint
uv run pyright                  # Type checking
uv run pytest                   # Tests
bam lint                        # Run lint via bam
bam test                        # Run all tests via bam
bam build                       # Full build via bam
```

## 📊 Status

**Phase 1: Core MVP** ✅ COMPLETE (2026-02-12)

- ✅ Task execution with dependencies
- ✅ Content-addressable caching
- ✅ YAML configuration
- ✅ Rich CLI interface
- ✅ Graph visualization
- ✅ 85% test coverage
- ✅ Complete documentation

**Phase 2: Parallelization** ✅ Complete

- ✅ Async task execution
- ✅ Parallel execution with `--jobs` flag
- ✅ Auto CPU detection
- ✅ Interactive tree view with live progress
- ✅ Dependency-aware scheduling
- ✅ Better error context with dependency chains
- ✅ TTY detection for CI/CD compatibility

**Phase 3: Extended Runners & CI** ✅ Complete

- ✅ Flat CLI interface (`bam <task>` instead of `bam run <task>`)
- ✅ Shell tab completion for task names
- ✅ CI pipeline generation (`--ci`) for GitHub Actions and GitLab CI
- ✅ Docker runner (`runner.type: docker`)
- ✅ Python-uv runner (`runner.type: python-uv`) for inline scripts
- ✅ Runner-aware cache keys

**Coming Soon:**
- 🔄 Phase 4: Remote cache hardening (advanced CAS sync, observability, reliability)
- 🎨 Phase 5: Enhanced developer experience

See [roadmap.md](https://gitlab.com/cascascade/bam/-/blob/main/spec/roadmap.md) for details.

## 🤝 Contributing

Contributions welcome! Please:

- Follow PEP 8 and project code style
- Add tests for new functionality
- Update documentation as needed
- Run quality checks before submitting

Development setup instructions in the [Development](#development) section above.

## 📝 License

MIT License - see [LICENSE](https://gitlab.com/cascascade/bam/-/blob/main/LICENSE) for details.

## 🔗 Links

**Documentation:**
- [Concept Document](https://gitlab.com/cascascade/bam/-/blob/main/docs/concept.md) - Core concepts and technology stack
- [CLI Reference](https://gitlab.com/cascascade/bam/-/blob/main/docs/cli.md) - Command documentation
- [Configuration Guide](https://gitlab.com/cascascade/bam/-/blob/main/docs/configuration.md) - YAML reference

**Specifications:**
- [Architecture](https://gitlab.com/cascascade/bam/-/blob/main/spec/architecture.md) - System design
- [Testing Strategy](https://gitlab.com/cascascade/bam/-/blob/main/spec/testing.md) - Test practices
- [Design Document](https://gitlab.com/cascascade/bam/-/blob/main/spec/design.md) - Philosophy
- [Roadmap](https://gitlab.com/cascascade/bam/-/blob/main/spec/roadmap.md) - Implementation plan

**Examples:**
- [examples/](https://gitlab.com/cascascade/bam/-/tree/main/examples/) - Sample projects

---

**Built with:** Python 3.14+ • uv • Typer • Rich • NetworkX • Pydantic • cascache_lib
