# Bam - Implementation Roadmap

**Project:** Bam - Content-Addressed Workflow Orchestration  
**Timeline:** 6-7 weeks (experimental roadmap)  
**Current Status:** Phase 2 COMPLETE ✅ (2026-02-12)

---

## Timeline Overview

```
Week 1-2: Core MVP        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 1
Week 3:   Parallelization ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 2
Week 4:   CAS Integration ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 3  
Week 5:   Dev Experience  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 4
Week 6:   CI/CD Features  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 5
Week 7+:  Advanced        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 6+
```

---

## Phase 1: Core MVP (Week 1-2) - Local Task Runner

**Goal:** Execute tasks with dependency tracking and local caching

**Status:** ✅ COMPLETE (2026-02-12)

### Day 1-2: Project Setup

**Status:** ✅ COMPLETE (2026-02-12)

**Objectives:**
- Repository and project structure initialization
- Development environment configuration
- Basic CLI framework

**Tasks:**
- [x] Create GitLab repository `bam`
- [x] Initialize with uv package manager (`uv init`)
- [x] Define project structure (src/, tests/, docs/, examples/)
- [x] Configure pyproject.toml
  - Python 3.14+ requirement
  - Core dependencies: click/typer, pyyaml, networkx, rich
  - Dev dependencies: pytest, pytest-asyncio, pyright, ruff
- [x] Set up testing infrastructure
  - pytest configuration
  - Test directory structure
  - Fixtures and utilities
- [x] Basic CLI framework
  - Entry point: `bam` command
  - Skeleton commands: run, list, clean, graph
  - Help text and version
- [x] README with vision statement
- [x] Contributing guidelines
- [x] License file (MIT or Apache 2.0)
- [x] .gitignore for Python projects
- [x] Initial commit and push

**Deliverables:**
- Working `bam --help` command
- README with quick start
- CI pipeline (GitLab CI)

**Tests:** Setup validation tests

---

### Day 3-4: Configuration Parsing

**Status:** ✅ COMPLETE (2026-02-12)

**Objectives:**
- Load and parse bam.yaml files
- Validate configuration structure
- Define task model

**Tasks:**
- [x] YAML parser implementation
  - Load bam.yaml files
  - Environment variable expansion
  - Config file discovery (walk up directory tree)
- [x] Task model (dataclasses)
  ```python
  @dataclass
  class Task:
      name: str
      command: str
      inputs: list[Path]
      outputs: list[Path]
      depends_on: list[str]
      env: dict[str, str]
  ```
- [x] Configuration validation
  - Schema definition (pydantic)
  - Required field validation
  - Type checking
  - Helpful error messages
- [x] Example bam.yaml files
  - Hello world example
  - Python project example
  - Multi-task example with dependencies
- [x] Config file discovery logic
  - `--config` CLI flag
  - `BAM_CONFIG` environment variable
  - Search current and parent directories

**Deliverables:**
- Configuration parser module
- Task model with validation
- Example configurations
- `bam validate` command

**Tests:** 
- Valid/invalid YAML parsing
- Schema validation
- Environment variable expansion
- File discovery logic

---

### Day 5-6: Task Graph

**Status:** ✅ COMPLETE (2026-02-12)

**Objectives:**
- Build dependency graph from tasks
- Detect cycles and invalid dependencies
- Determine execution order

**Tasks:**
- [x] Dependency graph builder (networkx)
  - Create directed graph from tasks
  - Add nodes (tasks) and edges (dependencies)
  - Validate task references
- [x] Topological sort for execution order
  - Order tasks respecting dependencies
  - Handle multiple valid orderings
- [x] Cycle detection
  - Detect circular dependencies
  - Report cycle path to user
  - Clear error messages
- [x] Graph visualization
  - `bam graph` command
  - ASCII art output for terminal
  - DOT format for graphviz
  - HTML visualization (optional)
- [x] Dry-run mode
  - Show execution plan without running
  - `bam run --dry-run` flag

**Deliverables:**
- Graph builder module
- Task ordering algorithm
- Cycle detection with error reporting
- `bam graph` visualization command

**Tests:**
- Simple dependency chains
- Complex dependency graphs
- Cycle detection (various patterns)
- Multiple independent tasks
- Missing dependency errors

---

### Day 7-9: Task Execution

**Status:** ✅ COMPLETE (2026-02-12)

**Objectives:****
- Execute shell commands via subprocess
- Handle environment variables and working directories
- Capture output and exit codes

**Tasks:**
- [x] Command executor (subprocess)
  - Execute shell commands
  - Stream stdout/stderr in real-time
  - Capture exit codes
  - Timeout handling
- [x] Environment variable handling
  - Merge task env with system env
  - Variable expansion in commands
  - Secret sanitization (don't log)
- [x] Working directory management
  - Execute in correct directory
  - Handle relative paths
  - Restore working directory after execution
- [x] Output capture and formatting
  - Real-time output streaming
  - Colored output (rich)
  - Task name prefixing for clarity
  - Quiet mode option
- [x] Exit code handling
  - Fail fast on non-zero exit
  - Continue on failure (optional)
  - Detailed error reporting
- [x] Task state tracking
  - States: pending, running, completed, failed, skipped
  - Status reporting
  - Summary at end of execution

**Deliverables:**
- Task executor module
- Output formatting with rich
- Error handling and reporting
- `bam run <task>` working end-to-end

**Tests:**
- Simple command execution
- Commands with arguments
- Environment variables
- Non-zero exit codes
- Output capture
- Execution in correct directory

---

### Day 10-12: Local Caching

**Status:** ✅ COMPLETE (2026-02-12)

**Objectives:****
- Implement content-addressable local cache
- Skip tasks with matching cache keys
- Store and restore task outputs

**Tasks:**
- [x] Content hashing (SHA256)
  - Hash input files
  - Hash command string
  - Hash environment variables (relevant ones)
  - Deterministic hash computation
- [x] Input fingerprinting
  - Glob pattern expansion (inputs)
  - File modification time tracking
  - Recursive directory hashing
  - Sort inputs for determinism
- [x] Local cache directory structure
  - `.bam/cache/` directory
  - Blob storage: `{hash}/output.tar.gz`
  - Metadata: `{hash}/metadata.json`
  - Lock files for concurrent access
- [x] Cache lookup
  - Compute input hash
  - Check if cache entry exists
  - Validate cached outputs still valid
- [x] Cache restore
  - Extract cached outputs
  - Restore to correct locations
  - Verify integrity
- [x] Cache storage
  - Tar/compress task outputs
  - Store with metadata
  - Atomic writes (temp + rename)
- [x] `bam clean` command
  - Delete cache directory
  - Selective cleaning (by task, by age)
  - Show cache size before cleaning

**Deliverables:**
- Local cache implementation
- Cache key computation
- Cache backend abstraction (for future CAS)
- Significant speedup on repeated runs

**Tests:**
- Hash computation (deterministic)
- Cache hit scenario
- Cache miss scenario
- Invalid cache (outputs changed)
- Cache storage and restoration
- Concurrent access safety

---

### Day 13-14: Testing & Documentation

**Status:** ✅ COMPLETE (2026-02-12)

**Objectives:****
- Comprehensive test coverage
- User documentation
- Example projects

**Tasks:**
- [x] Unit tests for all modules
  - Configuration parsing
  - Graph building
  - Task execution
  - Cache operations
  - 85% code coverage (exceeded 80% target)
- [x] Integration tests
  - Full workflow execution (multi-stage pipeline)
  - Multi-task dependencies
  - Cache hit/miss scenarios
  - Error handling and edge cases
  - 22 integration tests added
- [x] Example projects
  - `examples/hello-world/` - Single task
  - `examples/python-project/` - Lint + test
  - `examples/multi-language/` - Proto gen + parallel builds
  - `examples/complex-graph/` - 12-task multi-stage pipeline
  - All examples validated
- [x] CLI documentation
  - Complete command reference (docs/cli.md)
  - Usage examples for all commands
  - Tips & tricks section
  - Environment variables
- [x] Configuration reference
  - Complete bam.yaml guide (docs/configuration.md)
  - All fields documented
  - Best practices section
  - Common patterns
- [x] README improvements
  - Quick start guide present
  - Installation instructions
  - Feature highlights
  - Project philosophy

**Deliverables:**
- ✅ 85% test coverage (57 tests: 35 unit + 22 integration)
- ✅ 4 working example projects (all validated)
- ✅ Complete CLI documentation (docs/cli.md)
- ✅ Configuration reference (docs/configuration.md)
- ✅ Polished README with examples

**Tests:** 
- All unit and integration tests passing
- Example projects run successfully

---

## Phase 1 Success Criteria ✅

**Must Have:**
- [ ] Can execute tasks with dependencies in correct order
- [ ] Local cache hit rate >80% on repeated runs
- [ ] Time to first run: <5 minutes (with examples)
- [ ] Config file: <50 lines for simple project
- [ ] All tests passing (80%+ coverage)
- [ ] Zero-config works for simple projects

**Performance Targets:**
- Config parsing: <100ms
- Graph building: <50ms for 100 tasks
- Cache lookup: <10ms per task
- Task execution overhead: <50ms per task

**Should Have:**
- [ ] Helpful error messages with suggestions
- [ ] Colored terminal output
- [ ] Example projects working
- [ ] Basic documentation complete

---

## Phase 2: Parallelization (Week 3) - Fast Execution

**Goal:** Execute independent tasks concurrently

**Status:** ⏳ PLANNED

### Day 1-2: Parallel Executor

**Tasks:**
- [ ] Concurrent task execution (asyncio)
  - Convert executor to async
  - Worker pool management
  - Semaphore for max workers
- [ ] Max workers configuration
  - `--jobs` CLI flag
  - `BAM_MAX_PARALLEL` env var
  - Auto-detect CPU count
- [ ] Task scheduling algorithm
  - Execute ready tasks immediately
  - Balance load across workers
  - Prioritize critical path

**Deliverables:**
- Async task executor
- Parallel execution working

---

### Day 3-4: Dependencies & Coordination

**Tasks:**
- [ ] Wait for task dependencies
  - Async waiting with `asyncio.Event`
  - Task completion signals
  - Dependency tracking
- [ ] Propagate failures
  - Cancel dependent tasks on failure
  - Option to continue independent tasks
  - Configurable failure modes
- [ ] Resource locking (optional)
  - Shared resource declarations
  - Mutex for exclusive access
  - Deadlock detection

**Deliverables:**
- Safe parallel execution
- Failure handling

---

### Day 5-6: Progress Reporting

**Tasks:**
- [ ] Real-time task status
  - Live status updates
  - Task progress bars
  - ETA calculation
- [ ] Rich terminal output
  - Parallel progress bars (rich.progress)
  - Colored status indicators
  - Spinner for running tasks
- [ ] Parallel output handling
  - **Buffer task output** (don't interleave with bam messages)
  - Show complete task output on completion
  - Real-time streaming mode (`--stream` flag)
  - **Principle: Task output is primary, bam messages minimal**
- [ ] Output verbosity levels
  - `--quiet`: Only task output
  - Default: Minimal bam messages + task output
  - `--verbose`: Include timing and diagnostics
  - `--format json`: Machine-readable for CI
- [ ] Summary statistics
  - Total time, time saved
  - Cache hit rate
  - Parallelism achieved

**Design Principle:**
Task output should dominate the terminal. Users run `bam run test` to see test results, not bam orchestration details. Keep bam messages minimal, clearly prefixed, and never interleaved with task output.

**Deliverables:**
- Beautiful progress reporting
- Clean task output handling
- Multiple verbosity modes

---

### Day 7: Testing & Optimization

**Tasks:**
- [ ] Stress tests (many parallel tasks)
  - 100+ task workflows
  - Resource exhaustion tests
  - Race condition detection
- [ ] Benchmark speedup measurements
  - Compare sequential vs parallel
  - Measure overhead
  - Identify bottlenecks
- [ ] Memory profiling
  - Check for leaks
  - Optimize memory usage
  - Document memory requirements
- [ ] Documentation updates
  - Parallel execution guide
  - Performance tuning tips

**Deliverables:**
- Performance benchmarks
- Memory usage documented

---

## Phase 2 Success Criteria ✅

**Must Have:**
- [ ] 2-4x speedup for independent tasks
- [ ] No race conditions in parallel execution
- [ ] Clean parallel output
- [ ] Deterministic results

**Performance Targets:**
- Parallelism efficiency: >80%
- Memory: <100MB baseline + <10MB per parallel task
- No deadlocks or race conditions

---

## Phase 3: CAS Integration (Week 4) - Distributed Caching

**Goal:** Share cache across team and CI

**Status:** 🔄 IN PROGRESS (2026-02-12)

### Day 1: Async Cache Refactoring ✅

**Status:** ✅ COMPLETE (2026-02-12)

**Tasks:**
- [x] CacheBackend interface converted to async
  ```python
  class CacheBackend(ABC):
      async def exists(self, key: str) -> bool
      async def get(self, key: str, output_paths: list[Path]) -> bool
      async def put(self, key: str, output_paths: list[Path]) -> bool
      async def clear(self) -> None
  ```
- [x] LocalCache implementation refactored to async
  - Uses asyncio.to_thread() for blocking I/O
  - Preserved tar.gz compression logic
  - Non-blocking for event loop compatibility
- [x] Executor updated to await cache operations
  - `await cache.exists()`
  - `await cache.get()`
  - `await cache.put()`
- [x] Tests updated to async
  - All cache tests now use `async def`
  - 85 tests passing
- [x] CLI cache.clear() uses asyncio.run()
- [x] Type errors fixed (pyright clean)

**Deliverables:**
- ✅ Async cache interface ready for gRPC
- ✅ All tests passing (85/85)
- ✅ Type safety validated

---

### Day 2-3: CAS Client ✅

**Status:** ✅ COMPLETE (2026-02-12)

**Tasks:**
- [x] Copy proto files from cascache
  - build/bazel/remote/execution protos (cas_simple, action_cache, capabilities)
  - Generate Python gRPC bindings
- [x] gRPC client for cascache server
  - Connection management with grpc.aio
  - Async channel initialization
- [x] Authentication
  - Token-based auth (Bearer token in metadata)
  - Optional token parameter
- [x] Error handling
  - gRPC error catching
  - Logging for failures
- [x] CASCache implementation (basic)
  - exists() - check blob with FindMissingBlobs
  - get() - download with BatchReadBlobs
  - put() - upload with BatchUpdateBlobs
  - Tarball compression for artifacts
  - Async operations using asyncio

**Deliverables:**
- ✅ Proto files copied and Python bindings generated
- ✅ CASCache class with gRPC client
- ✅ Authentication via Bearer token
- ✅ All 85 tests passing
- ✅ Type safety validated (pyright clean)

---

### Day 4-5: CacheManager Implementation ✅

**Status:** ✅ COMPLETE (2026-02-12)

**Tasks:**
- [x] CacheManager implementation
  - Orchestrates local + remote caching
  - Check local first (fast), then remote
  - Populate local on remote hit
  - Automatic upload to remote on put
  - Graceful fallback on network errors
- [x] Cache factory function
  - create_cache() builds cache from config
  - Token file reading support
  - Automatic fallback to local on errors
- [x] Updated configuration schema
  - LocalCacheConfig (enabled, path)
  - RemoteCacheConfig (enabled, type, url, token_file, upload, download, timeout)
  - Hierarchical cache configuration
- [x] Statistics tracking
  - Local/remote hit counters
  - Miss tracking
  - Upload/download failure tracking
  - Hit rate calculation
- [x] Integration tests
  - CacheManager with local-only
  - Fallback to local on remote failure
  - Stats tracking verification
  - 90 tests passing (85 original + 5 new)

**Deliverables:**
- ✅ CacheManager class with hierarchical caching
- ✅ Cache factory for config-driven cache creation
- ✅ Updated configuration schema
- ✅ Statistics tracking and reporting
- ✅ All 90 tests passing
- ✅ Type safety validated (pyright clean)

---

### Day 5-6: CASCache Enhancements ✅

**Status:** ✅ COMPLETE (2026-02-12)

**Tasks:**
- [x] Retry logic with exponential backoff
  - Automatic retry on transient errors (UNAVAILABLE, DEADLINE_EXCEEDED, RESOURCE_EXHAUSTED)
  - Configurable max_retries (default: 3)
  - Exponential backoff starting at 100ms (doubles up to 5s)
  - No retry on non-retryable errors (UNAUTHENTICATED, PERMISSION_DENIED, INVALID_ARGUMENT)
- [x] Connection pooling
  - gRPC keepalive configuration (30s keepalive time, 10s timeout)
  - Connection reuse across requests
  - Automatic reconnection on network failures
- [x] Better error messages
  - User-friendly error translations for gRPC status codes
  - Connection failure tracking
  - Timeout and authentication error guidance
- [x] Configuration updates
  - max_retries: Maximum retry attempts
  - initial_backoff: Initial backoff delay in seconds
  - Added to RemoteCacheConfig schema
- [x] Comprehensive testing
  - 11 new tests for retry logic
  - Test exponential backoff behavior
  - Test non-retryable errors
  - Test connection failure tracking
  - 101 tests passing (90 original + 11 new)

**Deliverables:**
- ✅ Retry logic with exponential backoff
- ✅ Connection pooling for efficient gRPC connections
- ✅ User-friendly error messages
- ✅ Configuration schema updates
- ✅ All 101 tests passing
- ✅ Type safety validated (pyright clean)
- ✅ Documentation updated with retry behavior

**Implementation Notes:**
- Streaming for large artifacts marked as future enhancement (>1MB currently logged)
- Connection failures tracked for monitoring/alerting
- Graceful fallback to local cache maintained

---

### Day 7: Remote Cache Operations (Original Plan)

**Tasks:**
- [ ] Enhance CASCache
  - Retry logic with exponential backoff
  - Connection pooling
  - Better error messages
  - Streaming for large artifacts
- [ ] Cache configuration
  - `cache.local.enabled`: true/false
  - `cache.remote.url`: CAS server URL
  - `cache.remote.upload`: true/false
  - `cache.local_fallback`: true/false
- [ ] Cache selection logic
  - Choose backend based on config
  - Fallback chain: CAS → Local → No cache

**Deliverables:**
- CacheBackend abstraction
- LocalCache and CASCache implementations
- Configuration for cache selection

---

### Day 5-6: Remote Cache Operations

**Tasks:**
- [ ] Upload artifacts to CAS
  - Compute digest (SHA256)
  - Tar/compress outputs
  - Stream upload to CAS
  - Store mapping: cache_key → digest
- [ ] Download artifacts from CAS
  - Lookup cache_key → digest
  - Stream download from CAS
  - Extract to output locations
  - Verify integrity
- [ ] Fallback to local on CAS failure
  - Detect CAS unavailability
  - Automatic fallback to LocalCache
  - Log warnings, don't fail workflow
- [ ] Cache statistics tracking
  - Hit/miss rates (local vs remote)
  - Upload/download counts
  - Bytes transferred
  - Time savings
- [ ] `bam cache stats` command
  - Show cache statistics
  - Breakdown by task
  - Local vs remote hits

**Deliverables:**
- Full CAS integration
- Fallback logic working
- Cache statistics tracking

---

### Day 7: Testing ✅

**Status:** ✅ COMPLETE (2026-02-12)

**Tasks:**
- [x] Unit tests with mock CAS server
  - Mock gRPC responses for retry testing
  - Test error scenarios (UNAVAILABLE, UNAUTHENTICATED, etc.)
  - Test fallback logic
  - 11 retry-specific tests in test_cas_retry.py
- [x] Container-based integration tests with real cascache
  - Docker Compose setup with cascache server + bam client
  - Uses `uv run --from git+...` to run cascache without installation
  - 8 comprehensive integration tests
  - Tests upload/download, cache sharing, multi-file artifacts, large files
  - Optional dependency group: `uv sync --group cascache`
- [x] Network failure scenarios
  - Connection retry with exponential backoff
  - Graceful fallback to local cache
  - Connection failure tracking
- [x] Documentation updates
  - CAS configuration in examples/remote-cache/
  - Retry logic documentation in spec/design.md
  - Integration test guide in tests/integration-cascache/README.md

**Deliverables:**
- ✅ All 101 tests passing (unit + integration + component)
- ✅ cascache integration tests (Docker-based, optional)
- ✅ CI workflow for cascache integration tests  
- ✅ Complete documentation for team deployment

**Implementation Notes:**
- cascache integration tests are optional (require Docker)
- Use `./tests/integration-cascache/run-tests.sh` or `just test-cascache` to run
- Tests simulate multi-machine cache sharing
- No need to install cascache locally (runs in container)

---

## Phase 3 Success Criteria

**Must Have:**
- [ ] CAS integration working (upload/download)
- [ ] Cache shared across machines
- [ ] Fallback to local on CAS failure
- [ ] Team cache hit rate: >70%

**Performance Targets:**
- CAS upload: <100ms overhead for small artifacts
- CAS download: <50ms overhead for cache hit
- Network timeout: <5s before fallback

---

## Phase 3 Future Enhancements

### Streaming for Large Artifacts
- [ ] **Streaming upload/download**: For artifacts >1MB, use streaming to reduce memory usage
  ```python
  # Currently logs when artifact >1MB, but uses batch API
  # Future: Use streaming API for large files
  ```
- [ ] **Chunked transfer**: Split large artifacts into chunks
- [ ] **Progress callbacks**: Report upload/download progress

### Cache Upload Configuration
- [ ] **Per-task upload control**: Allow tasks to opt-out of remote upload
  ```yaml
  tasks:
    local-only-task:
      command: ...
      cache:
        remote_upload: false  # don't push to remote
  ```
- [ ] **Global upload policy**: Make default upload behavior configurable
  ```yaml
  cache:
    remote:
      upload_policy: always | on-success | manual
  ```
- [ ] CLI flag: `bam run --no-remote-upload` to disable temporarily

### ActionCache Support
- [ ] Implement ActionCache client (cache entire command results)
- [ ] Action result serialization
- [ ] Command fingerprinting for cache keys
- [ ] Update cascache to match on action cache

### Performance Optimizations
- [ ] Parallel upload/download of artifacts
- [ ] Compression for large artifacts
- [ ] Deduplication across tasks
- [ ] Background upload (don't block task completion)

### Version Compatibility
- [ ] Implement REAPI version negotiation
- [ ] Support multiple REAPI versions
- [ ] Graceful degradation for version mismatches

### Multi-Remote Support
- [ ] Support multiple remote caches (team + CI)
- [ ] Cache priority/fallback chain
- [ ] Smart routing (which artifacts go where)

### Monitoring & Observability
- [ ] Cache hit/miss statistics
- [ ] Remote cache latency tracking
- [ ] Upload/download bandwidth metrics
- [ ] Dashboard integration

---

## Phase 4: Developer Experience (Week 5) - Better Workflow

**Goal:** Make daily development smooth and fast

**Status:** 🔄 IN PROGRESS

### Day 1-3: Watch Mode ✅

**Status:** ✅ COMPLETE (2026-04-08)

**Tasks:**
- [x] File watching (`watchdog>=3.0`)
  - Watch input file patterns per task
  - Detect file modifications and creations
  - Filter to only files declared as inputs
- [x] Auto-run tasks on changes
  - Debouncing (default 0.3 s — coalesces rapid editor saves)  
  - Restart observer with fresh watch set after each run
  - Config reloaded on every iteration (picks up bam.yaml edits)
- [x] Cancel-safe Ctrl-C handling
  - `KeyboardInterrupt` caught at top level; exits cleanly
- [x] `bam -w <task>` / `bam --watch <task>` flag
  - Prints watched directories at startup
  - `--debounce` option to tune the quiet period
  - `--jobs`, `--no-cache`, `--quiet`, `--plain` all pass through
  - Initial run before entering the watch loop

**Deliverables:**
- ✅ `src/bam_tool/watcher.py` — `compute_watch_dirs`, `wait_for_change`
- ✅ `--watch`/`-w` and `--debounce` flags on main command
- ✅ `watchdog>=3.0.0` added to dependencies
- ✅ 9 unit tests in `tests/unit/test_watcher.py` (all passing)
- ✅ 158 total tests passing

---

### Day 4-5: Rich CLI

**Tasks:**
- [ ] Colored output
  - Task names in cyan
  - Success in green
  - Errors in red
  - Warnings in yellow
- [ ] Progress indicators
  - Spinners for running tasks
  - Progress bars for long operations
  - Time remaining estimates
- [ ] Better error messages
  - Friendly explanations
  - Suggestions for fixes
  - Links to documentation
- [ ] Task timing breakdown
  - Time per task
  - Cache hit time savings
  - Total time and speedup
- [ ] ASCII art graph visualization
  - Terminal-friendly graph display
  - Show critical path
  - Highlight running tasks

**Deliverables:**
- Beautiful terminal UI
- Helpful error messages

---

### Day 6: Shell Integration

**Tasks:**
- [ ] Shell completions
  - Bash completion script
  - Zsh completion script
  - Fish completion script
- [ ] Command aliases
  - Short aliases for common commands
  - Custom alias configuration
- [ ] Output formatting options
  - `--format json` for scripting
  - `--format table` for CI
  - `--quiet` for minimal output

**Deliverables:**
- Shell completions
- CI-friendly output formats

---

### Day 7: Developer Tooling

**Tasks:**
- [ ] `bam init` wizard
  - Interactive project setup
  - Choose project type (Python, Go, etc.)
  - Generate starter bam.yaml
  - Install shell completions
- [ ] Configuration validation
  - `bam validate --strict`
  - Warn about best practice violations
  - Suggest optimizations
- [ ] Task templates
  - Reusable task definitions
  - Template variables
  - Built-in templates (test, build, deploy)
- [ ] Example project scaffolding
  - `bam init --example python`
  - Pre-configured example projects

**Deliverables:**
- Onboarding workflow
- Project templates

---

## Phase 4 Success Criteria ✅

**Must Have:**
- [ ] Watch mode working and responsive
- [ ] Beautiful terminal output
- [ ] Shell completions installed
- [ ] `bam init` wizard functional

**Developer Experience:**
- Time from install to first success: <5 minutes
- Onboarding satisfaction: High
- Daily usage friction: Minimal

---

## Phase 5: CI/CD Features (Week 6) - Production Ready

**Goal:** Ready for production CI pipelines

**Status:** ⏳ PLANNED

### Day 1-2: Environment Handling

**Tasks:**
- [ ] Environment variable expansion
  - `$VAR` and `${VAR}` syntax
  - Default values: `${VAR:-default}`
  - Required vars: `${VAR:?error message}`
- [ ] Secret handling
  - Detect secrets (patterns)
  - Never log secret values
  - Mask in output
- [ ] Multiple environment configs
  - `bam.yaml` + `bam.dev.yaml`
  - Environment-specific overrides
  - `--env` flag for selection
- [ ] `.env` file support
  - Load variables from .env
  - Merge with system env
  - Precedence rules
- [ ] Per-task `env_file:` field
  - Load a task-specific env file (e.g. `env_file: .env.test`)
  - Expand variables into task environment
  - Support multiple env files per task
- [ ] `secrets:` list on `TaskConfig`
  - Declare which env var names contain secrets
  - Automatically redact declared values from all log output
  - Never write secret values to cache metadata

**Deliverables:**
- Flexible environment handling
- Secret protection

---

### Day 3-4: Advanced Task Features

**Tasks:**
- [ ] Conditional task execution
  - `condition: branch == 'main'`
  - Skip tasks based on env vars
  - Expression evaluation
- [ ] Task retry logic
  - `retry: 3` for flaky commands
  - Exponential backoff
  - Retry on specific exit codes
- [ ] Task timeouts
  - `timeout: 300` (seconds)
  - Kill task on timeout
  - Clear timeout errors
- [ ] Continue-on-failure option
  - `continue_on_failure: true`
  - Run dependent tasks despite failure
  - Report all failures at end
- [ ] Task tagging and filtering
  - Tags: `[build, test, deploy]`
  - `bam run --tag test`
  - `bam run --exclude deploy`
- [ ] Glob output post-run validation
  - Warn (or fail in `--strict` mode) when declared `outputs:` globs match nothing after a task completes
  - Catches misconfigured output paths early before they silently produce cache misses

**Deliverables:**
- Advanced task control
- CI-specific features

---

### Day 5: CI Integration

**Tasks:**
- [ ] GitHub Actions example
  - Workflow file with bam
  - Cache restoration
  - Artifact uploads
- [ ] GitLab CI example
  - .gitlab-ci.yml with bam
  - Docker image with bam
  - Cache configuration
- [ ] Jenkins integration guide
  - Jenkinsfile example
  - Plugin requirements
  - Best practices
- [ ] CI-specific output formatting
  - Machine-readable output
  - Exit codes for CI systems
  - Failure summaries
- [ ] Performance reporting
  - Time savings report
  - Cache hit rates
  - Upload as CI artifacts
- [ ] Task matrix support
  - `matrix:` key on `TaskConfig` for multi-dimensional builds
  - Expand one task definition into N parallel, cache-keyed variants (e.g. multiple Python versions)
  - Each matrix cell gets a unique cache key combining the base hash and matrix parameters
  - Example:
    ```yaml
    tasks:
      test:
        command: pytest
        matrix:
          python: ["3.11", "3.12", "3.13"]
    ```

**Deliverables:**
- CI integration guides
- Working examples for major platforms

---

### Day 6-7: Reliability Features

**Tasks:**
- [ ] Comprehensive error recovery
  - Graceful degradation
  - Automatic retries for transient errors
  - Clear error categorization
- [ ] Cache corruption detection
  - Integrity checks (checksums)
  - Auto-repair or invalidate
  - Warning logs
- [ ] Network resilience
  - Retry with backoff
  - Timeout handling
  - Offline mode (local cache only)
- [ ] Telemetry (optional)
  - Metrics export (Prometheus format)
  - Usage statistics
  - Error reporting (opt-in)
- [ ] Health checks
  - `bam health` command
  - Check config validity
  - Check cache connectivity
  - Check CAS server reachability
- [ ] Age-based cache eviction
  - `bam clean --older-than 7d` to prune stale local cache entries
  - LRU eviction with optional `--max-size` cap (e.g. `--max-size 2G`)
  - Prevents unbounded `.bam/cache/` growth in long-lived dev environments
  - Preview mode: `bam clean --older-than 7d --dry-run` shows what would be deleted

**Deliverables:**
- Production-grade reliability
- Health monitoring

---

## Phase 5 Success Criteria ✅

**Must Have:**
- [ ] Works in GitHub Actions, GitLab CI, Jenkins
- [ ] Handles secrets safely
- [ ] Retry and timeout features working
- [ ] Health checks functional

**Reliability:**
- CI failure rate: <1% due to bam
- Network resilience: Survives transient failures
- Error reporting: Clear, actionable

---

## Phase 6+: Advanced Features (Week 7+) - Optional Enhancements

**Goal:** Enterprise and advanced use cases

**Status:** ⏳ FUTURE

### Remote Execution

**Architecture:**
- Configure remote machines with pre-installed tools
- Exchange artifacts via cascache (content-addressable storage)
- Remote machine runs task runner instance
- Simple SSH-based communication

**Tasks:**
- [ ] Remote machine configuration (hostname, credentials, cascache URL)
- [ ] Remote task executor implementation
- [ ] Artifact upload/download via cascache
- [ ] Remote execution status tracking
- [ ] Error handling and fallback to local
- [ ] SSH connection management
- [ ] Remote environment validation
- [ ] Network failure recovery

**Configuration Example:**
```yaml
remote:
  workers:
    - name: build-server
      host: build1.company.com
      cas_url: grpc://cas.company.com:50051
      capabilities: [docker, large-memory]

tasks:
  heavy-build:
    command: make build
    inputs: ["src/**"]
    outputs: ["dist/"]
    remote: build-server  # Run on remote machine
```

### Language API

- [ ] Python API for programmatic task definition
- [ ] Task composition and reuse
- [ ] Dynamic task generation
- [ ] Integration with Python build tools

### VSCode Integration

**Goal:** Seamless IDE integration for better developer experience

**Options:**
1. **VSCode Tasks Generator** (simpler)
   - Convert `bam.yaml` to `.vscode/tasks.json`
   - `bam vscode-tasks` command
   - Keep bam.yaml as source of truth
   - VSCode tasks call bam commands

2. **VSCode Extension** (richer)
   - Task explorer in sidebar
   - Run tasks from command palette
   - Task graph visualization
   - Real-time execution status
   - Integrated terminal output

**Tasks:**
- [ ] VSCode tasks.json generator
  - Parse bam.yaml
  - Generate VSCode task definitions
  - Map dependencies correctly
  - Problem matchers for error highlighting
- [ ] VSCode extension (optional)
  - Task tree view provider
  - Commands integration
  - Language server for bam.yaml
  - Syntax highlighting and validation
  - Graph visualization panel
- [ ] Keyboard shortcuts and snippets
- [ ] Documentation for VSCode users

**Generated tasks.json Example:**
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "bam: build",
      "type": "shell",
      "command": "bam run build",
      "group": "build",
      "problemMatcher": ["$eslint-stylish"],
      "dependsOn": ["bam: lint", "bam: test"]
    }
  ]
}
```

**Benefits:**
- Run tasks via Ctrl+Shift+B (build tasks)
- Task list in command palette
- Integration with debugging
- Familiar VSCode workflow

### CI Pipeline Generation

**Goal:** Automatically generate CI pipeline configurations from bam.yaml

**Architecture:**
- Read bam.yaml task definitions
- Generate platform-specific CI config
- Optimize for caching and artifacts
- Support multiple CI platforms

**Supported Platforms:**
- GitHub Actions (.github/workflows/)
- GitLab CI (.gitlab-ci.yml)
- Jenkins (Jenkinsfile)
- CircleCI (.circleci/config.yml)
- Azure Pipelines (azure-pipelines.yml)

**Tasks:**
- [ ] CI config generator framework
  - Abstract CI config model
  - Platform-specific renderers
  - Template system
- [ ] GitHub Actions generator
  - Workflow file generation
  - Matrix builds support
  - Caching strategy
  - Artifact uploads
- [ ] GitLab CI generator
  - Pipeline stages
  - Docker image selection
  - Cache configuration
  - Parallel job execution
- [ ] Jenkins generator
  - Declarative pipeline syntax
  - Stage definitions
  - Post actions
- [ ] Smart optimization
  - Detect independent tasks → parallel jobs
  - Setup task reuse (install once)
  - Caching strategy recommendations
  - Minimal container images

**Commands:**
```bash
# Generate CI config for specific platform
bam ci-gen github    # → .github/workflows/bam.yml
bam ci-gen gitlab    # → .gitlab-ci.yml
bam ci-gen jenkins   # → Jenkinsfile

# Interactive wizard
bam ci-gen --interactive

# With customization
bam ci-gen github --cache-strategy aggressive --parallel
```

**Generated GitHub Actions Example:**
```yaml
name: Bam CI
on: [push, pull_request]

jobs:
  setup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup environment
        run: bam run setup
      - uses: actions/cache@v3
        with:
          path: .bam/cache
          key: bam-${{ hashFiles('**/bam.yaml') }}
  
  parallel-checks:
    needs: setup
    runs-on: ubuntu-latest
    strategy:
      matrix:
        task: [lint, typecheck, test]
    steps:
      - name: Run ${{ matrix.task }}
        run: bam run ${{ matrix.task }}
  
  build:
    needs: parallel-checks
    runs-on: ubuntu-latest
    steps:
      - name: Build
        run: bam run build
      - uses: actions/upload-artifact@v3
        with:
          name: dist
          path: dist/
```

**Benefits:**
- Quick CI setup from existing bam.yaml
- Best practices baked in (caching, artifacts)
- Automatic parallelization detection
- Platform-specific optimizations
- Reduces CI configuration complexity

**Advanced Features:**
- [ ] Multi-platform CI (run same tasks on Linux/Mac/Windows)
- [ ] Environment-specific configs (staging, production)
- [ ] Secret detection and handling
- [ ] Cost optimization (shorter job times)
- [ ] CI config validation before generation

### Docker Integration

**Goal:** Run tasks in isolated Docker containers

**Architecture:**
- Specify Docker image per task
- Mount input directories as volumes
- Capture outputs from container
- Cache docker image pulls
- Support custom registry authentication

**Tasks:**
- [ ] Docker image configuration in task definition
- [ ] Volume mounting for inputs/outputs
- [ ] Docker image pull and caching
- [ ] Container lifecycle management (create, start, stop, cleanup)
- [ ] Environment variable passing to container
- [ ] Registry authentication (Docker Hub, private registries)
- [ ] Resource limits (CPU, memory)
- [ ] Network configuration

**Configuration Example:**
```yaml
tasks:
  test:
    command: pytest tests/
    inputs: ["src/**", "tests/**"]
    docker:
      image: python:3.14-slim
      volumes:
        - src:/workspace/src
        - tests:/workspace/tests
      env:
        PYTHONPATH: /workspace
```

### Plugins & Extensions

- [ ] Plugin system architecture
- [ ] Built-in plugins:
  - Kubernetes (deploy to clusters)
  - Slack (notifications)
  - Custom cache backends
  - Build monitoring
- [ ] Community plugin registry
- [ ] Plugin development guide

### Advanced Caching

- [ ] Incremental caching (partial updates)
- [ ] Cache compression strategies
- [ ] Cross-platform cache sharing
- [ ] Cache analytics and insights
- [ ] Cache warming strategies

### Web UI

- [ ] Dashboard for workflow visualization
- [ ] Real-time task monitoring
- [ ] Cache statistics and management
- [ ] Historical execution data
- [ ] Team analytics

---

## Success Metrics

### Phase 1 Metrics
- Time to execute hello-world: <1s
- Local cache hit rate: >80%
- Test coverage: >80%
- Example projects: 3+

### Phase 2 Metrics
- Parallel speedup: 2-4x for independent tasks
- Parallelism efficiency: >80%
- No race conditions

### Phase 3 Metrics
- CAS integration success rate: >99%
- Team cache hit rate: >70%
- Network overhead: <100ms per artifact

### Phase 4 Metrics
- Watch mode latency: <500ms to restart
- Developer satisfaction: High
- Onboarding time: <5 minutes

### Phase 5 Metrics
- CI adoption: 3+ teams
- CI integration success: >99%
- Production incidents: 0

### Overall Success
- [ ] Replaces shell scripts in 3+ real projects
- [ ] Positive developer feedback from 5+ developers
- [ ] <200ms overhead for cached tasks
- [ ] Documentation: developers productive in <30 minutes
- [ ] Active community contributions (if open source)

---

## Risk Mitigation

### Technical Risks

**Risk:** Cache key collisions
- **Mitigation:** Use SHA256 (collision probability negligible)
- **Fallback:** Add size to cache key: `{hash}/{size}`

**Risk:** Non-deterministic builds
- **Mitigation:** Document best practices for deterministic commands
- **Fallback:** Allow cache bypass with `--force`

**Risk:** Large artifact storage
- **Mitigation:** Implement cache eviction policies (TTL, LRU, size quotas)
- **Fallback:** Compress artifacts, use CAS server with S3 backend

**Risk:** Network reliability for CAS
- **Mitigation:** Automatic fallback to local cache
- **Fallback:** Offline mode

### Adoption Risks

**Risk:** Learning curve too steep
- **Mitigation:** `bam init` wizard, excellent documentation
- **Fallback:** Start with hello-world, progressive complexity

**Risk:** Configuration too complex
- **Mitigation:** Zero-config defaults, simple YAML structure
- **Fallback:** Copy examples, templates

**Risk:** Performance overhead
- **Mitigation:** Aggressive optimization, benchmarking
- **Fallback:** Profile and fix bottlenecks

---

## Dependencies & Coordination

### Dependency on cascache
- **Required:** cascache server for Phase 2
- **Status:** cascache Week 5 complete, production-ready
- **Coordination:** 
  - Reuse proto definitions from cascache
  - Test against real cascache server
  - Document cascache deployment for teams

### External Dependencies
- Python 3.14+ (released October 2024)
- gRPC and protobuf
- networkx for graph algorithms
- Rich for terminal UI
- Watchdog for file watching

### Documentation Dependencies
- Design document (workflow-tool-design.md) ✅
- Copilot instructions ✅
- README and user guides (Phase 1)
- API reference (Phase 6+)

---

## Open Questions

### Critical (Need Answers Before Phase 2)

**1. Cache Key Stability**
```
Q: How to handle non-deterministic inputs?
Options:
A) Content-only hashing (ignore metadata)
B) Explicit exclude patterns
C) Normalization layer

Decision needed: Week 1
```

**2. Failure Handling**
```
Q: What happens when task fails?
Options:
A) Default: stop dependents, continue independent
B) Configurable per-task
C) Global failure mode setting

Decision needed: Week 2
```

**3. Output Validation**
```
Q: How to ensure outputs are correct?
Options:
A) Basic: exit code + output exists
B) Advanced: add validation commands
C) Full: schema validation

Decision needed: Week 3
```

### Important (Can Defer)

- Workflow composition and reuse
- Secret management integration
- Multi-repository project support
- Plugin architecture details

---

---

## Deferred: Remote Cache Hardening

> These items are deliberately kept separate and deprioritised because testing
> a running `cascache_server` locally is inconvenient. Revisit when the local
> dev setup pain is resolved (e.g. a one-command Docker bootstrap).

### Streaming for Large Artifacts

- [ ] **Streaming upload/download**: For artifacts >1MB switch from `BatchUpdateBlobs` /
  `BatchReadBlobs` to the streaming API to avoid memory spikes and gRPC message-size limits
- [ ] **Chunked transfer**: Split large artifacts into configurable chunk sizes
- [ ] **Progress callbacks**: Report upload/download progress to the Rich UI

### Background Remote Upload

- [ ] Fire-and-forget remote upload after a task completes instead of awaiting it inline
  - Use a bounded `asyncio` task queue so in-flight uploads don't overwhelm the connection
  - `bam run` exits only after all background uploads finish (or a `--no-wait-upload` flag)
  - Reduces per-task wall-clock latency, especially on slow network links

### Per-Task Upload Control

- [ ] Allow individual tasks to opt out of remote upload:
  ```yaml
  tasks:
    deploy:
      command: kubectl apply ...
      cache:
        remote_upload: false   # side-effectful, never push to remote
  ```
- [ ] Global upload policy in `cache.remote`:
  ```yaml
  cache:
    remote:
      upload_policy: always | on-success | manual
  ```
- [ ] CLI override: `bam run --no-remote-upload`

### ActionCache Support

- [ ] Implement the REAPI ActionCache client (cache entire command results, not just blobs)
- [ ] Action result serialisation and fingerprinting
- [ ] Version negotiation with `cascache_server`

### Multi-Remote Support

- [ ] Support multiple remote caches in a fallback chain (e.g. team cache → CI cache → local)
- [ ] Smart routing: choose which artifacts go to which remote
- [ ] Per-task remote affinity

### Monitoring & Observability

- [ ] Prometheus-compatible metrics endpoint for cache hit/miss rates, latency, bandwidth
- [ ] `bam cache stats` command with breakdown by task and local vs. remote
- [ ] Connection failure rate tracking and alerting threshold

---

## Next Actions

**Immediate (This Week):**
1. [x] Finalize design document
2. [x] Create copilot instructions
3. [x] Create this roadmap
4. [x] Move docs to bam repository
5. [x] Initialize project with uv
6. [x] Complete Phase 1 Day 1-2 (Project Setup)
7. [x] Complete Phase 1 Day 3-4 (Configuration Parsing)
8. [x] Complete Phase 1 Day 5-6 (Task Graph)
9. [x] Complete Phase 1 Day 7-9 (Task Execution)
10. [x] Complete Phase 1 Day 10-12 (Local Caching)
11. [x] Complete Phase 1 Day 13-14 (Testing & Documentation)
12. [ ] Phase 1 Review and Release

**Phase 1 Week 1:**
- Days 1-2: Project setup
- Days 3-4: Configuration parsing
- Days 5-6: Task graph
- Days 7-9: Task execution (partial)

**Phase 1 Week 2:**
- Days 9-12: Finish execution + Local caching
- Days 13-14: Testing & documentation

**After Phase 1:**
- Review and iterate
- Get feedback from early users
- Adjust roadmap based on learnings
- Proceed to Phase 2

---

**Last Updated:** 2026-02-12  
**Status:** Phase 1 COMPLETE ✅  
**Next Milestone:** Phase 1 Review and Release Planning
