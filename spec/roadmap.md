# Cascade - Implementation Roadmap

**Project:** Cascade - Content-Addressed Workflow Orchestration  
**Timeline:** 6-7 weeks to production-ready  
**Current Status:** Phase 1 In Progress (Day 1-2 complete)

---

## Timeline Overview

```
Week 1-2: Core MVP        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 1
Week 3:   CAS Integration ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 2  
Week 4:   Parallelization ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 3
Week 5:   Dev Experience  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 4
Week 6:   CI/CD Features  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 5
Week 7+:  Advanced        ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ Phase 6+
```

---

## Phase 1: Core MVP (Week 1-2) - Local Task Runner

**Goal:** Execute tasks with dependency tracking and local caching

**Status:** 🟡 IN PROGRESS

### Day 1-2: Project Setup

**Status:** ✅ COMPLETE (2026-02-12)

**Objectives:**
- Repository and project structure initialization
- Development environment configuration
- Basic CLI framework

**Tasks:**
- [x] Create GitLab repository `cascade`
- [x] Initialize with uv package manager (`uv init`)
- [x] Define project structure (src/, tests/, docs/, examples/)
- [x] Configure pyproject.toml
  - Python 3.13+ requirement
  - Core dependencies: click/typer, pyyaml, networkx, rich
  - Dev dependencies: pytest, pytest-asyncio, mypy, ruff
- [x] Set up testing infrastructure
  - pytest configuration
  - Test directory structure
  - Fixtures and utilities
- [x] Basic CLI framework
  - Entry point: `cascade` command
  - Skeleton commands: run, list, clean, graph
  - Help text and version
- [x] README with vision statement
- [x] Contributing guidelines
- [x] License file (MIT or Apache 2.0)
- [x] .gitignore for Python projects
- [x] Initial commit and push

**Deliverables:**
- Working `cascade --help` command
- README with quick start
- CI pipeline (GitLab CI)

**Tests:** Setup validation tests

---

### Day 3-4: Configuration Parsing

**Status:** ✅ COMPLETE (2026-02-12)

**Objectives:**
- Load and parse cascade.yaml files
- Validate configuration structure
- Define task model

**Tasks:**
- [x] YAML parser implementation
  - Load cascade.yaml files
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
- [x] Example cascade.yaml files
  - Hello world example
  - Python project example
  - Multi-task example with dependencies
- [x] Config file discovery logic
  - `--config` CLI flag
  - `CASCADE_CONFIG` environment variable
  - Search current and parent directories

**Deliverables:**
- Configuration parser module
- Task model with validation
- Example configurations
- `cascade validate` command

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
  - `cascade graph` command
  - ASCII art output for terminal
  - DOT format for graphviz
  - HTML visualization (optional)
- [x] Dry-run mode
  - Show execution plan without running
  - `cascade run --dry-run` flag

**Deliverables:**
- Graph builder module
- Task ordering algorithm
- Cycle detection with error reporting
- `cascade graph` visualization command

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
- `cascade run <task>` working end-to-end

**Tests:**
- Simple command execution
- Commands with arguments
- Environment variables
- Non-zero exit codes
- Output capture
- Execution in correct directory

---

### Day 10-12: Local Caching

**Objectives:**
- Implement content-addressable local cache
- Skip tasks with matching cache keys
- Store and restore task outputs

**Tasks:**
- [ ] Content hashing (SHA256)
  - Hash input files
  - Hash command string
  - Hash environment variables (relevant ones)
  - Deterministic hash computation
- [ ] Input fingerprinting
  - Glob pattern expansion (inputs)
  - File modification time tracking
  - Recursive directory hashing
  - Sort inputs for determinism
- [ ] Local cache directory structure
  - `.cascade/cache/` directory
  - Blob storage: `{hash}/output.tar.gz`
  - Metadata: `{hash}/metadata.json`
  - Lock files for concurrent access
- [ ] Cache lookup
  - Compute input hash
  - Check if cache entry exists
  - Validate cached outputs still valid
- [ ] Cache restore
  - Extract cached outputs
  - Restore to correct locations
  - Verify integrity
- [ ] Cache storage
  - Tar/compress task outputs
  - Store with metadata
  - Atomic writes (temp + rename)
- [ ] `cascade clean` command
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

**Objectives:**
- Comprehensive test coverage
- User documentation
- Example projects

**Tasks:**
- [ ] Unit tests for all modules
  - Configuration parsing
  - Graph building
  - Task execution
  - Cache operations
  - 80%+ code coverage
- [ ] Integration tests
  - Full workflow execution
  - Multi-task dependencies
  - Cache hit/miss scenarios
- [ ] Example projects
  - `examples/hello-world/` - Single task
  - `examples/python-project/` - Proto gen + test + build
  - `examples/multi-language/` - Go + Python + TypeScript
- [ ] CLI documentation
  - Command reference (man page style)
  - Configuration reference
  - Examples for each command
- [ ] Configuration reference
  - All cascade.yaml options
  - Examples for common patterns
  - Best practices
- [ ] README improvements
  - Quick start guide
  - Installation instructions
  - Feature highlights
  - Comparison to alternatives

**Deliverables:**
- 80%+ test coverage
- 3+ working example projects
- Complete CLI documentation
- Polished README

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

## Phase 2: CAS Integration (Week 3) - Distributed Caching

**Goal:** Share cached artifacts via Python CAS server

**Status:** ⏳ PLANNED

### Day 1-2: CAS Client

**Tasks:**
- [ ] gRPC client for pycas server
  - Reuse proto definitions from pycas
  - Connection management
  - Channel pooling for performance
- [ ] Authentication
  - Token-based auth (read from file)
  - Token refresh logic
  - Secure token storage
- [ ] Error handling and retries
  - Exponential backoff
  - Transient error detection
  - Connection recovery
- [ ] Testing with mock pycas server

**Deliverables:**
- CAS gRPC client module
- Authentication handling
- Retry logic

---

### Day 3-4: Cache Backend Abstraction

**Tasks:**
- [ ] CacheBackend interface
  ```python
  class CacheBackend(ABC):
      async def get(self, key: str) -> bytes | None
      async def put(self, key: str, data: bytes) -> None
      async def exists(self, key: str) -> bool
  ```
- [ ] LocalCache implementation
  - Refactor Phase 1 cache to use interface
  - Async file I/O (aiofiles)
- [ ] CASCache implementation
  - Upload/download via gRPC
  - Streaming for large artifacts
  - Compression handling
- [ ] Cache configuration
  - `cache.type`: local, cas, layered
  - `cache.url`: CAS server URL
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
- [ ] `cascade cache stats` command
  - Show cache statistics
  - Breakdown by task
  - Local vs remote hits

**Deliverables:**
- Full CAS integration
- Fallback logic working
- Cache statistics tracking

---

### Day 7: Testing

**Tasks:**
- [ ] Unit tests with mock CAS server
  - Mock gRPC responses
  - Test error scenarios
  - Test fallback logic
- [ ] Integration tests with real pycas
  - Start pycas server in test
  - Upload/download blobs
  - Multi-machine simulation
- [ ] Network failure scenarios
  - CAS server down
  - Network timeout
  - Partial upload/download
- [ ] Documentation updates
  - CAS configuration guide
  - Deployment with pycas
  - Troubleshooting guide

**Deliverables:**
- All CAS tests passing
- Integration with pycas validated
- Documentation for team deployment

---

## Phase 2 Success Criteria ✅

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

## Phase 3: Parallelization (Week 4) - Fast Execution

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
  - `CASCADE_MAX_PARALLEL` env var
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
  - Buffer task output
  - Show output on task completion
  - Real-time mode for debugging
- [ ] Summary statistics
  - Total time, time saved
  - Cache hit rate
  - Parallelism achieved

**Deliverables:**
- Beautiful progress reporting
- Parallel output handling

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

## Phase 3 Success Criteria ✅

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

## Phase 4: Developer Experience (Week 5) - Better Workflow

**Goal:** Make daily development smooth and fast

**Status:** ⏳ PLANNED

### Day 1-3: Watch Mode

**Tasks:**
- [ ] File watching (watchdog)
  - Watch input file patterns
  - Detect file changes
  - Filter ignored files
- [ ] Auto-run tasks on changes
  - Debouncing (avoid rapid re-runs)
  - Smart task selection (minimal rebuild)
  - Interrupt and restart on new change
- [ ] Filtered patterns
  - `--pattern` flag for watch
  - Ignore patterns (.git, __pycache__)
- [ ] `cascade watch` command
  - `cascade watch test` - watch and re-run
  - `cascade watch --pattern 'src/**/*.py' -- lint test`

**Deliverables:**
- Watch mode implementation
- Fast feedback loop for development

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
- [ ] `cascade init` wizard
  - Interactive project setup
  - Choose project type (Python, Go, etc.)
  - Generate starter cascade.yaml
  - Install shell completions
- [ ] Configuration validation
  - `cascade validate --strict`
  - Warn about best practice violations
  - Suggest optimizations
- [ ] Task templates
  - Reusable task definitions
  - Template variables
  - Built-in templates (test, build, deploy)
- [ ] Example project scaffolding
  - `cascade init --example python`
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
- [ ] `cascade init` wizard functional

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
  - `cascade.yaml` + `cascade.dev.yaml`
  - Environment-specific overrides
  - `--env` flag for selection
- [ ] `.env` file support
  - Load variables from .env
  - Merge with system env
  - Precedence rules

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
  - `cascade run --tag test`
  - `cascade run --exclude deploy`

**Deliverables:**
- Advanced task control
- CI-specific features

---

### Day 5: CI Integration

**Tasks:**
- [ ] GitHub Actions example
  - Workflow file with cascade
  - Cache restoration
  - Artifact uploads
- [ ] GitLab CI example
  - .gitlab-ci.yml with cascade
  - Docker image with cascade
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
  - `cascade health` command
  - Check config validity
  - Check cache connectivity
  - Check CAS server reachability

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
- CI failure rate: <1% due to cascade
- Network resilience: Survives transient failures
- Error reporting: Clear, actionable

---

## Phase 6+: Advanced Features (Week 7+) - Optional Enhancements

**Goal:** Enterprise and advanced use cases

**Status:** ⏳ FUTURE

### Remote Execution

- [ ] Execute tasks on remote workers
- [ ] Distributed task queue
- [ ] Resource allocation (CPU, memory)
- [ ] Worker management and health

### Language API

- [ ] Python API for programmatic task definition
- [ ] Task composition and reuse
- [ ] Dynamic task generation
- [ ] Integration with Python build tools

### Plugins & Extensions

- [ ] Plugin system architecture
- [ ] Built-in plugins:
  - Docker (run tasks in containers)
  - Kubernetes (deploy to clusters)
  - Slack (notifications)
  - Custom cache backends
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
- CAS integration success rate: >99%
- Team cache hit rate: >70%
- Network overhead: <100ms per artifact

### Phase 3 Metrics
- Parallel speedup: 2-4x for independent tasks
- Parallelism efficiency: >80%
- No race conditions

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
- **Mitigation:** `cascade init` wizard, excellent documentation
- **Fallback:** Start with hello-world, progressive complexity

**Risk:** Configuration too complex
- **Mitigation:** Zero-config defaults, simple YAML structure
- **Fallback:** Copy examples, templates

**Risk:** Performance overhead
- **Mitigation:** Aggressive optimization, benchmarking
- **Fallback:** Profile and fix bottlenecks

---

## Dependencies & Coordination

### Dependency on pycas
- **Required:** pycas server for Phase 2
- **Status:** pycas Week 5 complete, production-ready
- **Coordination:** 
  - Reuse proto definitions from pycas
  - Test against real pycas server
  - Document pycas deployment for teams

### External Dependencies
- Python 3.13+ (released October 2024)
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

## Next Actions

**Immediate (This Week):**
1. [x] Finalize design document
2. [x] Create copilot instructions
3. [x] Create this roadmap
4. [x] Move docs to cascade repository
5. [x] Initialize project with uv
6. [x] Complete Phase 1 Day 1-2 (Project Setup)
7. [x] Complete Phase 1 Day 3-4 (Configuration Parsing)
8. [x] Complete Phase 1 Day 5-6 (Task Graph)
9. [x] Complete Phase 1 Day 7-9 (Task Execution)
10. [ ] Start Phase 1 Day 10-12 (Local Caching)

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
**Status:** Phase 1 In Progress (Day 1-9 complete) 🚧  
**Next Milestone:** Phase 1 Day 10-12 (Local Caching)
