# Cascade Configuration Reference

Complete guide to `cscd.yaml` configuration syntax and options.

## File Structure

```yaml
version: 1           # Required: Configuration schema version

cache:               # Optional: Cache backend settings
  type: local        # Cache type: "local" or "cas"
  url: null          # CAS server URL (for type: cas)
  local_fallback: true  # Fall back to local on CAS failure

tasks:               # Required: Task definitions
  task-name:         # Unique task identifier
    command: "..."   # Required: Shell command to execute
    inputs: []       # Optional: Input file patterns
    outputs: []      # Optional: Output file paths
    depends_on: []   # Optional: Task dependencies
    env: {}          # Optional: Environment variables
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

**Variable Expansion:**

```yaml
tasks:
  build:
    command: echo "$BUILD_ID"
    env:
      BUILD_ID: "${CI_PIPELINE_ID:-local}"   # Default value
      PROJECT: "${CI_PROJECT_NAME}"           # From CI
```

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

## Cache Configuration

### `cache.type`

**Type:** String  
**Required:** No  
**Default:** `"local"`  
**Values:** `"local"` or `"cas"`

```yaml
cache:
  type: local    # Use local filesystem cache
```

### `cache.url`

**Type:** String or null  
**Required:** Only for `type: cas`  
**Default:** `null`

```yaml
cache:
  type: cas
  url: grpc://localhost:50051    # CAS server address
```

### `cache.local_fallback`

**Type:** Boolean  
**Required:** No  
**Default:** `true`

```yaml
cache:
  type: cas
  url: grpc://cache-server:50051
  local_fallback: true    # Use local cache if CAS unavailable
```

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

---

**Version:** 0.1.0  
**Schema Version:** 1  
**Last Updated:** 2026-02-12
