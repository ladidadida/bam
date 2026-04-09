# Bam Configuration Reference

Complete guide to `bam.yaml` configuration syntax and options.

## File Structure

```yaml
version: 1           # Required: Configuration schema version

cache:               # Optional: Cache backend settings
  local:
    enabled: true    # Enable local filesystem cache
    path: .bam/cache # Cache directory
  remote:
    enabled: false   # Enable remote CAS cache
    url: grpc://localhost:50051
    token_file: null # Path to auth token file

tasks:               # Required: Task definitions
  task-name:         # Unique task identifier
    command: "..."   # Required: Shell command to execute
    inputs: []       # Optional: Input file patterns
    outputs: []      # Optional: Output file paths
    depends_on: []   # Optional: Task dependencies
    env: {}          # Optional: Environment variables
    stage: null      # Optional: Stage label (for --stage grouping / CI)
    timeout: 300     # Optional: Timeout in seconds (null = no limit)
    interactive: false  # Optional: Run as a foreground process (dev servers, REPLs)

ci:                  # Optional: CI pipeline generation settings
  provider: github-actions   # "github-actions" or "gitlab-ci"
  python_version: "3.14"
  exclude: []                # Tasks to omit from CI (local-only tasks)
  install_command: null      # Override default install step
```

## Required Fields

### `version`

**Type:** Integer  
**Required:** Yes  
**Values:** `1` (current schema version)

```yaml
version: 1
```

### `tasks`

**Type:** Dictionary  
**Required:** Yes (but can be empty)

Container for all task definitions. Keys are task names, values are task configurations.

```yaml
tasks:
  build:
    command: make build
  test:
    command: make test
```

## Task Configuration

### `command`

**Type:** String  
**Required:** Yes  
**Description:** Shell command to execute for this task.

```yaml
tasks:
  build:
    command: npm run build
  
  multi-line:
    command: |
      echo "Building..."
      npm install
      npm run build
  
  with-pipes:
    command: cat input.txt | grep "pattern" | sort > output.txt
```

**Notes:**
- Executed with `shell=True` in subprocess
- Supports pipes, redirects, and shell features
- Environment variables expanded: `$VAR` or `${VAR}`
- Command must exit 0 for success

### `inputs`

**Type:** List of strings  
**Required:** No  
**Default:** `[]`  
**Description:** Input files and glob patterns used for cache key computation.

```yaml
tasks:
  build:
    command: gcc main.c -o app
    inputs:
      - "main.c"
      - "lib/**/*.c"      # Recursive glob
      - "include/*.h"     # Simple glob
```

**Glob Patterns:**
- `*` - Match any characters except `/`
- `**` - Match any characters including `/` (recursive)
- `?` - Match single character
- `[abc]` - Match any character in set
- `[!abc]` - Match any character not in set

**Cache Behavior:**
- Files matching patterns are hashed for cache key
- Changes to any input file invalidate the cache
- Non-existent files are silently skipped
- Directories are recursively hashed

**Examples:**

```yaml
inputs:
  - "src/**/*.py"           # All Python files in src/
  - "tests/test_*.py"       # Test files
  - "pyproject.toml"        # Configuration
  - "requirements.txt"      # Dependencies
```

### `outputs`

**Type:** List of strings  
**Required:** No  
**Default:** `[]`  
**Description:** Files and directories produced by this task.

```yaml
tasks:
  build:
    command: npm run build
    outputs:
      - "dist/"              # Directory
      - "build/app.js"       # File
      - "build/styles.css"   # File
```

**Caching:**
- Only tasks with outputs are cached
- Outputs are tar.gz compressed and stored
- On cache hit, outputs are restored to their paths
- Missing outputs don't cause errors (logged as warnings)

**Notes:**
- Paths are relative to current working directory
- Parent directories created automatically on restore
- Overwrites existing files on cache restore

### `depends_on`

**Type:** List of strings  
**Required:** No  
**Default:** `[]`  
**Description:** Other tasks that must run before this task.

```yaml
tasks:
  lint:
    command: ruff check .
  
  test:
    command: pytest
    depends_on:
      - lint              # Run lint first
  
  build:
    command: npm run build
    depends_on:
      - lint              # Run lint first
      - test              # Then test
```

**Rules:**
- Dependencies must be defined tasks (not forward references)
- Cyclic dependencies are detected and cause validation error
- Dependencies run in topological order
- Independent dependencies can run in parallel (future feature)

**Graph Example:**

```yaml
tasks:
  setup:
    command: install-deps
  
  lint-python:
    command: ruff check
    depends_on: [setup]
  
  lint-js:
    command: eslint .
    depends_on: [setup]
  
  test:
    command: pytest
    depends_on: [lint-python, lint-js]  # Both linters must pass
```

### `env`

**Type:** Dictionary (string to string)  
**Required:** No  
**Default:** `{}`  
**Description:** Environment variables for the task.

```yaml
tasks:
  build:
    command: npm run build
    env:
      NODE_ENV: production
      API_URL: https://api.example.com
      CACHE_SIZE: "1000"
```

**Behavior:**
- Merged with system environment (doesn't replace)
- Task env overrides system env vars
- Used in cache key computation
- Supports variable expansion: `${VAR}`

**Cache Impact:**
Only env vars defined in the task config affect the cache key:

```yaml
tasks:
  compile:
    command: gcc -O2 main.c  # Uses $PATH from system
    env:
      OPTIMIZATION: "2"      # This IS in cache key
    # System $PATH is NOT in cache key
```

---

### `stage`

**Type:** String  
**Required:** No  
**Default:** `null`  
**Description:** Assigns the task to a named stage. Stages group tasks for
`bam --stage <name>` execution and become stage labels in generated CI pipelines.

```yaml
tasks:
  lint:
    command: ruff check src/
    stage: lint

  test:
    command: pytest
    stage: test
    depends_on: [lint]

  build:
    command: python -m build
    stage: build
    depends_on: [test]
```

Run an entire stage:

```bash
bam --stage test   # runs lint and test (and their dependencies)
```

---

### `timeout`

**Type:** Integer  
**Required:** No  
**Default:** `null` (no timeout)  
**Description:** Maximum number of seconds a task may run before bam intervenes.

```yaml
tasks:
  long-test:
    command: pytest tests/ --timeout=60
    timeout: 120   # Fail after 2 minutes if still running

  deploy:
    command: ./deploy.sh
    timeout: 300   # Prompt after 5 minutes in interactive mode
```

**Behavior:**
- **Interactive mode (TTY):** When the timeout expires bam pauses the progress
  display and asks: *"⏱ 'task' has been running for Xs. Continue waiting?"*
  - Press **Enter** (default Yes) to reset the timer and wait another `timeout`
    seconds.
  - Answer **No** to kill the task immediately and mark it failed.
- **CI / non-TTY mode:** The task is killed and marked failed without prompting.

---

### `interactive`

**Type:** Boolean  
**Required:** No  
**Default:** `false`  
**Description:** Run the task as a long-running foreground process — e.g. a development
server, file watcher, or REPL — instead of a captured subprocess.

When `interactive: true` the task:
- **Inherits the terminal** — stdin, stdout, and stderr are passed through directly, so colour output, progress bars, and user prompts work exactly as they would when you run the command yourself.
- **Is never cached** — there are no outputs to store.
- **Has no timeout** — it runs until the process exits or you press Ctrl-C.
- **Receives Ctrl-C naturally** — the signal is delivered to the child process through the shared terminal process group, giving it a chance to shut down gracefully.

```yaml
tasks:
  install:
    command: npm ci
    inputs: ["package.json", "package-lock.json"]
    outputs: ["node_modules/"]

  serve:
    command: npm run dev
    interactive: true
    depends_on: [install]   # install runs first (cached), then the server starts
```

**Rules:**
- An interactive task must be a **leaf node**: no other task may `depends_on` it.
- Only the **last task** in the execution order may be interactive. Dependencies run
  normally (with caching and the parallel scheduler) before the foreground process starts.
- `interactive: true` is mutually exclusive with `outputs` — declaring outputs has no
  effect and is silently ignored.
- Ctrl-C (SIGINT) and SIGTERM exit codes are treated as clean, not as failures.

**Exit behaviour:**

| Exit code | Treated as |
|---|---|
| 0 | Success |
| SIGINT (-2) / SIGTERM (-15) | Clean stop (exit 0) |
| Any other non-zero | Failure — printed and bam exits with that code |

---

### `runner`

**Type:** Object  
**Required:** No  
**Default:** `null` (shell)
**Description:** Controls *how* the task command is executed.

When omitted, the command runs in a local shell — the same as `type: shell`.

#### Runner types

**`shell`** (default)

Runs the command in a local shell. Equivalent to no `runner:` key.

```yaml
tasks:
  lint:
    command: ruff check src/
```

---

**`docker`**

Runs the command inside a Docker container.  The current working directory is
bind-mounted so relative paths work as expected.

**Required field:** `image`

```yaml
tasks:
  lint-in-container:
    runner:
      type: docker
      image: python:3.14-slim
    command: pip install ruff && ruff check src/

  build-java:
    runner:
      type: docker
      image: maven:3.9-eclipse-temurin-21
    command: mvn package -DskipTests
    inputs:
      - "src/**/*.java"
      - "pom.xml"
    outputs:
      - "target/*.jar"
```

**Notes:**
- Requires `docker` on `PATH`; a clear error is raised if it is missing.
- The image is pulled automatically by Docker if not cached locally.
- The cache key includes the image name so different images never share a cache hit.

---

**`python-uv`**

Treats the `command` field as an **inline Python script** and executes it with
`uv run python`. Useful for short analysis or reporting tasks without a
dedicated script file.

```yaml
tasks:
  count-files:
    runner:
      type: python-uv
    command: |
      import pathlib
      files = list(pathlib.Path("src").rglob("*.py"))
      print(f"{len(files)} Python source files")

  check-version:
    runner:
      type: python-uv
    command: |
      import tomllib, pathlib
      data = tomllib.loads(pathlib.Path("pyproject.toml").read_text())
      print(data["project"]["name"], data["project"].get("version", "(dynamic)"))
```

**Notes:**
- Requires `uv` on `PATH`; a clear error is raised if it is missing.
- The script is written to a temporary `.py` file and cleaned up after execution.
- The cache key includes the full script body.

---

**Runner error handling**

If the required tool (`docker` or `uv`) is not on `PATH`, bam raises a
`RunnerNotFoundError` **before** spawning any subprocess, with a message like:

```
Runner 'docker' requires 'docker' but it was not found on PATH.
Install docker and make sure it is available before running this task.
```

### `cache.type`

> **Note:** The old `cache.type / cache.url / cache.local_fallback` flat schema is
> superseded. Use the nested `cache.local` / `cache.remote` structure below.

---

## Cache Configuration

### `cache.local.enabled`

**Type:** Boolean  
**Required:** No  
**Default:** `true`

```yaml
cache:
  local:
    enabled: true
```

### `cache.local.path`

**Type:** String  
**Required:** No  
**Default:** `".cache"`

```yaml
cache:
  local:
    path: .bam/cache
```

### `cache.remote.enabled`

**Type:** Boolean  
**Required:** No  
**Default:** `false`

```yaml
cache:
  remote:
    enabled: true
    url: grpc://cache-server:50051
```

### `cache.remote.url`

**Type:** String  
**Required:** No  
**Default:** `"grpc://localhost:50051"`  
**Description:** CAS server URL. Only used when `cache.remote.enabled: true`.

### `cache.remote.token_file`

**Type:** String or null  
**Required:** No  
**Default:** `null`  
**Description:** Path to a file containing a Bearer auth token for the CAS server.

```yaml
cache:
  remote:
    enabled: true
    url: grpc://cache-server:50051
    token_file: ~/.config/bam/token
```

### `cache.remote.upload` / `cache.remote.download`

**Type:** Boolean  
**Required:** No  
**Default:** `true` for both  
**Description:** Control whether bam pushes artifacts to and/or pulls from the remote cache independently.

```yaml
cache:
  remote:
    enabled: true
    upload: true     # push on cache miss
    download: true   # restore from remote on hit
```

### `cache.remote.timeout`

**Type:** Float  
**Required:** No  
**Default:** `30.0`  
**Description:** gRPC request timeout in seconds. On timeout bam falls back to the local cache.

### `cache.remote.max_retries` / `cache.remote.initial_backoff`

**Type:** Integer / Float  
**Required:** No  
**Default:** `3` / `0.1`  
**Description:** Retry policy for transient gRPC errors (UNAVAILABLE, DEADLINE_EXCEEDED,
RESOURCE_EXHAUSTED). Backoff doubles on each attempt up to 5 s.

```yaml
cache:
  remote:
    max_retries: 3
    initial_backoff: 0.1
```

---

## CI Configuration (`ci:`)

Controls the output of `bam --ci`. Each bam task becomes one CI job that calls
`bam <task>`, with job dependencies wired from `depends_on`.

```yaml
ci:
  provider: github-actions
  runner: ubuntu-latest
  python_version: "3.14"
  install_command: null    # default: "uv tool install bam-tool"
  exclude:
    - format               # local-only tasks to omit from CI
  triggers:
    push:
      branches: [main]
    pull_request:
  env:
    MY_CI_VAR: value
```

### `ci.provider`

**Type:** String  
**Required:** No  
**Default:** `"github-actions"`  
**Values:** `"github-actions"` | `"gitlab-ci"`

### `ci.runner`

**Type:** String  
**Required:** No  
**Default:** `"ubuntu-latest"`  
**Description:** CI runner image. For GitHub Actions this is the `runs-on` value.

### `ci.python_version`

**Type:** String or null  
**Required:** No  
**Default:** `null`  
**Description:** Python version to set up in CI (e.g. `"3.14"`). If null, no setup-python step is added.

### `ci.install_command`

**Type:** String or null  
**Required:** No  
**Default:** `null` (falls back to `uv tool install bam-tool`)  
**Description:** Override the step that installs bam in CI. Useful for installing from
source during development:

```yaml
ci:
  install_command: "uv tool install ."
```

### `ci.exclude`

**Type:** List of strings  
**Required:** No  
**Default:** `[]`  
**Description:** Task names to omit from the generated CI pipeline. Use this for
tasks that only make sense locally (e.g. `format`, aggregate aliases).

```yaml
ci:
  exclude:
    - format      # auto-formats code — not a CI check
    - ci-checks   # local dev convenience alias
```

### `ci.triggers`

**Type:** Dictionary  
**Required:** No  
**Default:** `{push: {branches: [main]}, pull_request: null}`  
**Description:** CI event triggers. Structure mirrors the provider's trigger syntax.

### `ci.env`

**Type:** Dictionary  
**Required:** No  
**Default:** `{}`  
**Description:** Environment variables injected into every CI job.

## Complete Examples

### Simple Project

```yaml
version: 1

tasks:
  build:
    command: go build -o app main.go
    inputs:
      - "*.go"
    outputs:
      - "app"
  
  test:
    command: go test ./...
    inputs:
      - "*.go"
      - "*_test.go"
```

### Python Project

```yaml
version: 1

tasks:
  lint:
    command: ruff check src/
    inputs:
      - "src/**/*.py"
      - "pyproject.toml"
  
  typecheck:
    command: pyright
    inputs:
      - "src/**/*.py"
      - "pyproject.toml"
  
  test:
    command: pytest tests/
    inputs:
      - "src/**/*.py"
      - "tests/**/*.py"
      - "pyproject.toml"
    depends_on:
      - lint
      - typecheck
  
  build:
    command: python -m build
    inputs:
      - "src/**/*.py"
      - "pyproject.toml"
      - "README.md"
    outputs:
      - "dist/"
    depends_on:
      - test
```

### Multi-Stage Build

```yaml
version: 1

tasks:
  install:
    command: npm ci
    inputs:
      - "package.json"
      - "package-lock.json"
    outputs:
      - "node_modules/"
  
  lint:
    command: npm run lint
    inputs:
      - "src/**/*.ts"
      - ".eslintrc.json"
    depends_on:
      - install
  
  build:
    command: npm run build
    inputs:
      - "src/**/*.ts"
      - "tsconfig.json"
    outputs:
      - "dist/"
    depends_on:
      - lint
  
  test:
    command: npm test
    inputs:
      - "src/**/*.ts"
      - "tests/**/*.ts"
      - "jest.config.js"
    depends_on:
      - build
  
  package:
    command: npm pack
    inputs:
      - "dist/"
      - "package.json"
    outputs:
      - "*.tgz"
    depends_on:
      - test
```

### Development Server (interactive)

```yaml
version: 1

tasks:
  install:
    command: npm ci
    inputs:
      - "package.json"
      - "package-lock.json"
    outputs:
      - "node_modules/"

  serve:
    command: npm run dev
    interactive: true       # Full terminal access, no timeout, never cached
    depends_on: [install]   # Restore node_modules from cache first
```

Running `bam serve` installs dependencies (restored from cache when unchanged) and
then hands the terminal over to the dev server. Press Ctrl-C to stop.

### With Environment Variables

```yaml
version: 1

tasks:
  setup:
    command: |
      echo "Setting up environment..."
      export DATABASE_URL="postgres://localhost/testdb"
    env:
      ENV: development
  
  migrate:
    command: alembic upgrade head
    env:
      DATABASE_URL: ${DATABASE_URL}
      ENV: ${ENV:-development}
    depends_on:
      - setup
  
  seed:
    command: python seed_db.py
    env:
      DATABASE_URL: ${DATABASE_URL}
    depends_on:
      - migrate
```

## Validation Rules

### Task Names
- Must be unique
- Can contain: letters, numbers, hyphens, underscores
- Cannot start with a hyphen
- Case-sensitive

### Dependencies
- Must reference existing tasks
- No cyclic dependencies
- Topologically sortable

### Commands
- Cannot be empty
- Must be valid shell syntax (not validated until execution)

### Paths
- Relative to config file location or working directory
- Use forward slashes `/` (even on Windows)
- Globs evaluated at runtime

## Best Practices

### 1. Explicit Inputs

```yaml
# ✅ Good: Explicit inputs
tasks:
  build:
    inputs:
      - "src/**/*.ts"
      - "tsconfig.json"
      - "package.json"
    command: tsc

# ❌ Bad: Missing inputs means no caching
tasks:
  build:
    command: tsc
```

### 2. Granular Tasks

```yaml
# ✅ Good: Separate, cacheable steps
tasks:
  lint:
    command: eslint src/
    inputs: ["src/**/*.js"]
  
  test:
    command: jest
    inputs: ["src/**/*.js", "tests/**/*.js"]
    depends_on: [lint]

# ❌ Bad: Monolithic, poor caching
tasks:
  check:
    command: eslint src/ && jest
    inputs: ["src/**/*.js", "tests/**/*.js"]
```

### 3. Output Declarations

```yaml
# ✅ Good: Declare outputs for caching
tasks:
  compile:
    command: gcc -o app main.c
    inputs: ["*.c", "*.h"]
    outputs: ["app"]          # Cached!

# ❌ Bad: Missing outputs means no caching
tasks:
  compile:
    command: gcc -o app main.c
    inputs: ["*.c", "*.h"]
```

### 4. Environment Variables

```yaml
# ✅ Good: Explicit env in config
tasks:
  build:
    command: npm run build
    env:
      NODE_ENV: production

# ❌ Bad: Implicit env (not in cache key)
tasks:
  build:
    command: NODE_ENV=production npm run build
```

## Common Patterns

### Parallel Tasks

```yaml
tasks:
  lint-python:
    command: ruff check src/
  
  lint-js:
    command: eslint web/
  
  check:
    depends_on:
      - lint-python
      - lint-js
```

### Conditional Execution

```yaml
tasks:
  build:
    command: |
      if [ "$ENV" = "production" ]; then
        npm run build:prod
      else
        npm run build:dev
      fi
    env:
      ENV: ${ENV}
```

### Dynamic Outputs

```yaml
tasks:
  archive:
    command: tar czf "release-$(date +%Y%m%d).tar.gz" dist/
    inputs: ["dist/**/*"]
    outputs: ["release-*.tar.gz"]  # Glob matches dynamic name
```

### Watch Mode Pattern

Declare precise `inputs:` globs so watch mode only triggers on relevant files:

```yaml
tasks:
  test:
    command: pytest tests/
    inputs:
      - "src/**/*.py"   # re-run when source changes
      - "tests/**/*.py" # re-run when tests change
      - "pyproject.toml"
```

Then start the feedback loop:

```bash
bam -w test          # watches src/, tests/, and pyproject.toml
bam -w test --no-cache --debounce 0.5
```

See [cli.md](cli.md) for the full watch mode reference.

---

**Version:** 0.5.4  
**Schema Version:** 1  
**Last Updated:** 2026-04-09
