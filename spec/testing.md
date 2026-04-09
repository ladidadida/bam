# Bam Testing Specification

**Version:** 1.0  
**Last Updated:** 2026-02-12  
**Status:** Phase 2 Complete

## Testing Philosophy

Bam maintains high code quality through comprehensive testing at multiple levels. Our testing strategy balances thoroughness with maintainability, ensuring both correctness and developer productivity.

## Testing Targets

### Coverage Goals
- **Overall:** 85%+ code coverage (✅ achieved: 85%)
- **Critical paths:** 95%+ (config, graph, cache)
- **UI/CLI:** 70%+ (harder to test, less critical)

### Test Distribution
- **Unit tests:** 51 tests (47%)
- **Integration tests:** 47 tests (44%)
- **Component tests:** 3 tests (3%)
- **Integration-cascache tests:** 7 tests (6%, optional)
- **Total:** 108 tests

## Test Organization

```text
tests/
├── unit/                     # Fast, isolated tests
│   ├── test_cache.py            # Core cache behavior
│   ├── test_cli.py              # CLI unit behavior
│   ├── test_config_parser.py    # Config parsing/discovery
│   ├── test_executor.py         # Executor behavior
│   ├── test_graph_builder.py    # Graph construction/sort
│   └── cache/
│       └── test_cas_retry.py    # Remote cache retry logic
│
├── integration/              # Multi-component tests
│   ├── test_workflows.py        # End-to-end workflows
│   ├── test_parallel.py         # Parallel execution behavior
│   ├── test_rich_progress.py    # TTY/plain output behavior
│   ├── test_cache_manager.py    # Cache integration behavior
│   ├── test_error_context.py    # Error context and skipped tasks
│   └── test_errors.py           # Error scenarios
│
├── component/                # CLI end-to-end tests
│   └── test_cli_e2e.py          # Full CLI testing
│
├── integration-cascache/     # Optional real-server tests
│   ├── test_cascache_integration.py
│   ├── docker-compose.yml
│   └── run-tests.sh
│
└── conftest.py               # Shared fixtures

## Test Levels

### 1. Unit Tests

**Purpose:** Test individual functions and classes in isolation

**Characteristics:**
- Fast (<10ms per test)
- No file I/O (use in-memory)
- Mocked external dependencies
- Single responsibility focus

**Example:**
```python
def test_compute_cache_key():
    """Cache key should be deterministic and unique."""
    inputs = [Path("foo.txt"), Path("bar.txt")]
    command = "build"
    env = {"KEY": "value"}
    
    key1 = compute_cache_key(command, inputs, env)
    key2 = compute_cache_key(command, inputs, env)
    
    assert key1 == key2  # Deterministic
    assert len(key1) == 64  # SHA256 hex
```

**Coverage Areas:**
- Configuration parsing and validation
- Graph algorithms (cycles, topological sort)
- Cache key computation
- Path glob expansion
- Environment variable expansion

### 2. Integration Tests

**Purpose:** Test interactions between components

**Characteristics:**
- Moderate speed (<100ms per test)
- Real file I/O with temp directories
- Multiple components working together
- Focus on data flow

**Example:**
```python
def test_full_workflow_with_cache(tmp_path):
    """Complete workflow with caching should work end-to-end."""
    # Setup
    config = create_test_config(tmp_path)
    cache = LocalCache(tmp_path / ".cache")
    executor = TaskExecutor(cache)
    
    # First run
    result1 = executor.run_workflow(config, ["build"])
    assert result1.success
    assert result1.executed == ["build"]
    
    # Second run (from cache)
    result2 = executor.run_workflow(config, ["build"])
    assert result2.success
    assert result2.cached == ["build"]
```

**Coverage Areas:**
- Task execution with dependencies
- Cache hit/miss scenarios
- Multi-stage pipelines
- Error propagation
- Configuration loading

### 3. Component Tests

**Purpose:** Test CLI commands as users would use them

**Characteristics:**
- Slower (<1s per test)
- Full CLI invocation
- Real subprocess execution
- Test user experience

**Example:**
```python
def test_bam_run_command(tmp_path):
    """CLI should execute tasks and show output."""
    create_test_project(tmp_path)
    
    result = subprocess.run(
        ["bam", "run", "build"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    
    assert result.returncode == 0
    assert "✅ build" in result.stdout
```

**Coverage Areas:**
- CLI argument parsing
- Output formatting
- Error messages
- Exit codes
- User interactions

## Test Categories

### Configuration Tests

**Files:** `tests/unit/config/`

**Test Cases:**
- Valid YAML parsing
- Invalid YAML syntax
- Missing required fields
- Extra unknown fields
- Environment variable expansion: `${VAR}`, `$VAR`, `${VAR:-default}`
- Glob pattern expansion: `**/*.py`, `src/**`, `*.txt`
- Default values
- Configuration file discovery

**Key Tests:**
```python
def test_parse_valid_config()
def test_invalid_yaml_syntax()
def test_missing_required_field()
def test_env_var_expansion()
def test_glob_pattern_resolution()
def test_config_file_discovery()
```

### Graph Tests

**Files:** `tests/unit/graph/`

**Test Cases:**
- Simple dependency chains
- Complex dependency graphs
- Cyclic dependencies (2-task, 3-task, self-reference)
- Missing dependencies
- Topological sort correctness
- Deterministic ordering
- Parallel-safe graphs
- Subgraph extraction

**Key Tests:**
```python
def test_simple_dependency_chain()
def test_detect_cycle_two_tasks()
def test_detect_cycle_three_tasks()
def test_missing_dependency()
def test_topological_sort_order()
def test_deterministic_ordering()
def test_subgraph_extraction()
```

### Cache Tests

**Files:** `tests/unit/cache/`

**Test Cases:**
- SHA256 hash computation
- Deterministic cache keys
- Different commands → different keys
- Different inputs → different keys
- Different env vars → different keys
- Same order independence (sorted)
- Cache storage (put/get/exists)
- Cache cleanup
- Archive compression

**Key Tests:**
```python
def test_compute_hash_deterministic()
def test_different_command_different_key()
def test_different_inputs_different_key()
def test_cache_put_and_get()
def test_cache_compression()
def test_cache_cleanup()
```

### Executor Tests

**Files:** `tests/unit/executor/`, `tests/integration/`

**Test Cases:**
- Simple task execution
- Task with dependencies
- Multi-stage pipeline
- Parallel task ordering
- Task failure handling
- Exit code propagation
- Output capture
- Environment variables
- Working directory

**Key Tests:**
```python
def test_execute_simple_task()
def test_execute_with_dependencies()
def test_multi_stage_pipeline()
def test_task_failure_stops_execution()
def test_capture_stdout_stderr()
def test_environment_variables()
```

### Error Handling Tests

**Files:** `tests/integration/test_errors.py`

**Test Cases:**
- Invalid YAML syntax
- Missing task definition
- Cyclic dependencies
- Command execution failure
- Missing input files
- Cache errors (permissions, disk full)
- Helpful error messages

**Key Tests:**
```python
def test_invalid_yaml_error_message()
def test_cyclic_dependency_error()
def test_missing_task_error()
def test_command_failure_message()
```

### CLI Tests

**Files:** `tests/component/test_cli_e2e.py`

**Test Cases:**
- `bam run <task>`
- `bam list`
- `bam graph`
- `bam validate`
- `bam clean`
- Help output
- Version display
- Error exit codes

**Key Tests:**
```python
def test_cli_run_task()
def test_cli_list_tasks()
def test_cli_graph_output()
def test_cli_validate_config()
def test_cli_clean_cache()
```

## Testing Utilities

### Test Fixtures

**Location:** `tests/conftest.py`

```python
@pytest.fixture
def tmp_workspace(tmp_path):
    """Create temporary workspace with test project."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace

@pytest.fixture
def sample_config():
    """Provide sample configuration for testing."""
    return {
        "version": 1,
        "tasks": {
            "build": {
                "command": "echo building",
                "inputs": ["src/**/*.py"],
                "outputs": ["dist/"],
            }
        }
    }

@pytest.fixture
def local_cache(tmp_path):
    """Create local cache backend."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    return LocalCache(cache_dir)
```

### Test Helpers

**Location:** `tests/helpers.py`

```python
def create_test_file(path: Path, content: str = "test"):
    """Create file with content."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)

def create_test_config(workspace: Path, config: dict):
    """Write bam.yaml to workspace."""
    config_path = workspace / "bam.yaml"
    config_path.write_text(yaml.dump(config))
    return config_path

def assert_cache_hit(result, task_name: str):
    """Assert task was served from cache."""
    assert task_name in result.cached
    assert task_name not in result.executed
```

## Test Execution

### Running Tests

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=bam --cov-report=html

# Specific category
uv run pytest tests/unit/
uv run pytest tests/integration/
uv run pytest tests/component/

# Specific file
uv run pytest tests/unit/cache/test_hash.py

# Specific test
uv run pytest tests/unit/cache/test_hash.py::test_compute_hash_deterministic

# Verbose output
uv run pytest -v

# Show print statements
uv run pytest -s

# Stop on first failure
uv run pytest -x

# Run in parallel
uv run pytest -n auto
```

### Coverage Reports

```bash
# Terminal report
uv run pytest --cov=bam

# HTML report
uv run pytest --cov=bam --cov-report=html
open htmlcov/index.html

# XML report (for CI)
uv run pytest --cov=bam --cov-report=xml
```

### Quality Checks

```bash
# Full CI pipeline
bam ci-checks

# Individual checks
bam lint         # Ruff
bam typecheck    # Pyright
bam test-unit    # Pytest (unit)
bam test-integration  # Pytest (integration)
```

## Test Data Management

### Fixtures Directory

**Location:** `tests/fixtures/`

```text
fixtures/
├── sample_configs/
│   ├── minimal.yaml           # Minimal valid config
│   ├── python_project.yaml    # Python workflow
│   ├── multi_language.yaml    # Polyglot project
│   ├── complex_graph.yaml     # Multi-stage pipeline
│   └── invalid/               # Invalid configs
│       ├── missing_command.yaml
│       ├── cyclic_deps.yaml
│       └── bad_syntax.yaml
│
└── mock_projects/
    ├── hello_world/           # Simple project
    ├── with_deps/             # Multi-file project
    └── failing/               # Project with failing tasks
```

### Dynamic Test Generation

For testing multiple scenarios, use `pytest.mark.parametrize`:

```python
@pytest.mark.parametrize("command,expected_key_prefix", [
    ("build", "a1b2c3"),
    ("test", "d4e5f6"),
    ("deploy", "g7h8i9"),
])
def test_cache_keys_differ_by_command(command, expected_key_prefix):
    """Different commands should produce different cache keys."""
    key = compute_cache_key(command, [], {})
    assert key.startswith(expected_key_prefix)
```

## Continuous Integration

### GitLab CI Configuration

**Location:** `.gitlab-ci.yml`

```yaml
test:
  stage: test
  script:
    - uv sync
    - uv run pytest --cov=bam --cov-report=xml
    - uv run mypy src/
    - uv run ruff check src/
  coverage: '/TOTAL.*\s+(\d+%)$/'
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

### GitHub Actions

**Location:** `.github/workflows/test.yml`

```yaml
name: Test
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v1
      - run: uv sync
      - run: uv run pytest --cov=bam
      - run: uv run mypy src/
      - run: uv run ruff check src/
```

## Current Test Status

### Phase 1 Results (2026-02-12)

- ✅ 60 tests passing
- ✅ 85% code coverage
- ✅ All quality checks green
- ✅ CI pipeline passing

### Coverage Breakdown

| Module | Coverage | Tests |
|--------|----------|-------|
| config/ | 90% | 12 |
| tasks/ | 85% | 8 |
| graph/ | 92% | 10 |
| executor/ | 80% | 9 |
| cache/ | 88% | 11 |
| cli.py | 75% | 10 |
| **Total** | **85%** | **60** |

### Test Performance

- Total runtime: ~2.8s
- Unit tests: ~0.5s
- Integration tests: ~1.8s
- Component tests: ~0.5s

## Testing Best Practices

### 1. Test Naming
```python
# Good: descriptive, action-oriented
def test_cache_key_changes_when_input_modified()

# Bad: vague, unclear
def test_cache()
```

### 2. AAA Pattern
```python
def test_example():
    # Arrange
    config = create_test_config()
    
    # Act
    result = parse_config(config)
    
    # Assert
    assert result.is_valid()
```

### 3. Single Assertion Focus
```python
# Good: focused test
def test_config_has_required_version():
    config = parse_config(valid_yaml)
    assert config.version == 1

# Avoid: testing multiple things
def test_config_everything():
    config = parse_config(valid_yaml)
    assert config.version == 1
    assert len(config.tasks) > 0
    assert config.cache is not None
```

### 4. Deterministic Tests
- No random data
- No time dependencies
- Fixed file ordering
- Reproducible results

### 5. Isolation
- Use `tmp_path` fixture
- Clean up after tests
- No global state
- Independent execution

## Future Testing Plans

### Phase 2: Parallel Execution
- Race condition testing
- Deadlock detection
- Resource contention
- Performance benchmarks

### Phase 3: CAS Integration
- gRPC client mocking
- Network error scenarios
- Authentication testing
- Fallback behavior

### Phase 4+
- Property-based testing (Hypothesis)
- Mutation testing
- Performance regression tests
- Load testing

## References

- [Architecture](architecture.md) - System design
- [Design Document](design.md) - Philosophy
- [Roadmap](roadmap.md) - Implementation plan
- [pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
