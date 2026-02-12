# Cascade 🌊

**Flow naturally through your build pipeline**

Cascade is a content-addressed workflow orchestration tool that brings the power of content-addressable storage to everyday development workflows. It bridges the gap between simple task runners (like Make/Just) and complex build systems (like Bazel), providing intelligent caching without forcing teams to restructure their projects.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-60%20passing-brightgreen.svg)](#testing)
[![Coverage](https://img.shields.io/badge/coverage-85%25-brightgreen.svg)](#testing)

## ✨ Features

- **🎯 Smart Caching** - Content-addressed caching with SHA256 for instant rebuilds
- **📊 Dependency Graphs** - Automatic topological sorting and cycle detection
- **🔍 Rich CLI** - Colored output, progress tracking, and ASCII graph visualization
- **⚙️ Simple Config** - Clean YAML syntax with glob patterns and env vars
- **🛡️ Type Safe** - Full type hints with mypy validation
- **🧪 Well Tested** - 85% coverage with 60 tests (unit + integration)
- **📚 Documented** - Complete CLI and configuration references

## 🚀 Quick Start

### Installation

```bash
# Using uv (recommended)
uv pip install cascade

# Using pip
pip install cascade

# From source
git clone https://gitlab.com/yourusername/cascade.git
cd cascade
uv sync
```

### Your First Workflow

Create `cascade.yaml` in your project:

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
cascade run test

# List available tasks
cascade list

# Visualize dependency graph
cascade graph

# Validate configuration
cascade validate
```

## 📖 Documentation

**User Guides:**
- [CLI Reference](docs/cli.md) - Complete command documentation
- [Configuration Guide](docs/configuration.md) - Full cascade.yaml reference

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
    command: mypy src/
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

### `cascade run`

Execute tasks with automatic dependency resolution:

```bash
# Run single task
cascade run build

# Run multiple tasks
cascade run lint test build

# Dry run (show execution plan)
cascade run --dry-run deploy

# Disable caching
cascade run --no-cache build

# Quiet mode
cascade run -q test
```

### `cascade graph`

Visualize task dependencies:

```bash
# ASCII tree output
cascade graph

# GraphViz DOT format
cascade graph --format dot > graph.dot
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

### `cascade validate`

Validate configuration:

```bash
cascade validate
```

Checks:
- ✅ Valid YAML syntax
- ✅ No cyclic dependencies
- ✅ All dependencies defined
- ✅ Required fields present

### `cascade clean`

Manage cache:

```bash
# Clean with confirmation
cascade clean

# Force clean
cascade clean --force
```

## 🏗️ Architecture

Cascade is built as a layered system:

**CLI → Config → Graph → Executor → Cache**

Each layer is independently testable with clear interfaces. The architecture supports local-first operation with future remote cache backends.

For detailed architecture documentation, see [spec/architecture.md](spec/architecture.md).

## 🧪 Testing

Cascade maintains high code quality with comprehensive testing:

```bash
# Run all tests
uv run pytest

# With coverage report
uv run pytest --cov=cascade --cov-report=html
```

**Current Status:**
- 60 tests (35 unit + 22 integration + 3 e2e)
- 85% code coverage
- All quality checks passing

For detailed testing strategy and practices, see [spec/testing.md](spec/testing.md).

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
just typecheck   # Type checking (mypy)
just test        # Run tests (pytest)
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

**Coming Soon:**
- ⚡ Phase 2: Parallel execution
- 🔄 Phase 3: CAS Integration (remote caching)
- 🎨 Phase 4: Enhanced developer experience
- 🤖 Phase 5: CI/CD optimizations

**Future Features:**
- 🐳 Docker Integration - Run tasks in isolated containers
- 🌐 Remote Execution - Execute tasks on remote machines via pycas
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
