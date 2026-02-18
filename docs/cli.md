# Cascade CLI Reference

Complete command-line interface documentation for Cascade.

## Installation

```bash
# Using uv (recommended)
uv pip install cscd

# Using pip
pip install cscd
```

## Global Options

All commands support these global options:

- `--help` - Show help message and exit
- `--version` - Show version and exit

## Commands

### `cscd run`

Execute one or more tasks with their dependencies.

**Usage:**
```bash
cscd run [OPTIONS] TASK [TASK...]
```

**Arguments:**
- `TASK` - One or more task names to execute (required)

**Options:**
- `--config PATH` - Path to cscd.yaml configuration file
  - Default: Searches for `cscd.yaml` or `.cscd.yaml` in current directory and parents
- `--dry-run` - Show what would be executed without running anything
- `--quiet, -q` - Suppress command output (only show results)
- `--no-cache` - Disable cache reads and writes for this run

**Examples:**

```bash
# Run single task
cscd run build

# Run multiple tasks
cscd run lint test build

# Dry run to see execution plan
cscd run --dry-run deploy

# Run with specific config
cscd run --config path/to/config.yaml test

# Run without caching
cscd run --no-cache build

# Quiet mode (minimal output)
cscd run -q test
```

**Behavior:**
- Automatically runs all dependencies in topological order
- Uses cached outputs when available (unless `--no-cache`)
- Fails fast on first task error
- Returns exit code 0 on success, 1 on failure

---

### `cscd list`

Display all configured tasks and their dependencies.

**Usage:**
```bash
cscd list [OPTIONS]
```

**Options:**
- `--config PATH` - Path to cscd.yaml configuration file

**Examples:**

```bash
# List all tasks
cscd list

# List with specific config
cscd list --config examples/hello-world/cscd.yaml
```

**Output Format:**
```
Available tasks:
  • build
    depends on: lint, test
  • lint
  • test
```

---

### `cscd graph`

Visualize the task dependency graph.

**Usage:**
```bash
cscd graph [OPTIONS]
```

**Options:**
- `--config PATH` - Path to cscd.yaml configuration file
- `--format FORMAT` - Output format: `ascii` or `dot`
  - Default: `ascii`
  - `ascii` - Tree-style Unicode box drawing
  - `dot` - GraphViz DOT format for rendering

**Examples:**

```bash
# Show ASCII graph
cscd graph

# Generate DOT format for GraphViz
cscd graph --format dot > graph.dot
dot -Tpng graph.dot -o graph.png

# With specific config
cscd graph --config path/to/config.yaml
```

**ASCII Output Example:**
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

**DOT Output Example:**
```dot
digraph TaskGraph {
  rankdir=LR;
  "setup" -> "build";
  "build" -> "test";
  "test" -> "deploy";
}
```

---

### `cscd validate`

Validate configuration file syntax and dependency graph.

**Usage:**
```bash
cscd validate [OPTIONS]
```

**Options:**
- `--config PATH` - Path to cscd.yaml configuration file

**Examples:**

```bash
# Validate default config
cscd validate

# Validate specific config
cscd validate --config path/to/config.yaml
```

**Checks:**
✅ Valid YAML syntax  
✅ Required fields present  
✅ No cyclic dependencies  
✅ All dependencies defined  
✅ No duplicate task names

**Output:**
```
Configuration is valid: /path/to/cscd.yaml
Discovered 12 task(s).
```

**Error Example:**
```
Error: Cyclic dependency detected in task graph:
  a -> b -> c -> a
```

---

### `cscd clean`

Clean local cache artifacts.

**Usage:**
```bash
cscd clean [OPTIONS]
```

**Options:**
- `--cache-dir PATH` - Cache directory to clean
  - Default: `.cscd/cache`
- `--force, -f` - Skip confirmation prompt

**Examples:**

```bash
# Clean default cache (with confirmation)
cscd clean

# Force clean without confirmation
cscd clean --force

# Clean custom cache directory
cscd clean --cache-dir /path/to/cache
```

**Interactive Mode:**
```
Cache directory: .cscd/cache
Cache size: 142.35 MB
Delete all cached artifacts? [y/N]: 
```

**Force Mode:**
```
✓ Cache cleared
```

---

## Environment Variables

Configure Cascade behavior via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `CSCD_CONFIG` | Path to configuration file | `./cscd.yaml` |
| `CSCD_CACHE_DIR` | Local cache directory | `./.cscd/cache` |
| `CSCD_CACHE_TYPE` | Cache backend type | `local` |
| `CSCD_LOG_LEVEL` | Logging verbosity | `INFO` |

**Examples:**

```bash
# Use custom config location
export CSCD_CONFIG=~/.config/cscd.yaml
cscd run build

# Use different cache directory
export CSCD_CACHE_DIR=/tmp/cascade-cache
cscd run test

# Debug mode
export CSCD_LOG_LEVEL=DEBUG
cscd run --dry-run deploy
```

---

## Configuration File Discovery

Cascade searches for configuration files in this order:

1. `--config` CLI argument
2. `CSCD_CONFIG` environment variable
3. `./cscd.yaml` in current directory
4. `./.cscd.yaml` (hidden file) in current directory
5. Walk up directory tree looking for either file

**Example:**

```
/home/user/project/src/
  └─ No config here, searches parent...
/home/user/project/
  └─ cscd.yaml ✓ Found!
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Task failure, configuration error, or validation error |
| 130 | Interrupted (Ctrl+C) |

---

## Tips & Tricks

### 1. Quick Task Status

```bash
# See what will run
cscd run --dry-run build | grep "Would execute"
```

### 2. Cache Debugging

```bash
# Run without cache to force rebuild
cscd run --no-cache build

# Check cache status
cscd clean  # Shows size before confirming
```

### 3. Configuration Validation

```bash
# Always validate after config changes
cscd validate && echo "Config OK" || echo "Config ERROR"
```

### 4. Complex Workflows

```bash
# Run multiple independent targets
cscd run test-frontend test-backend

# Combine with shell scripts
cscd run build && docker build -t myapp .
```

### 5. Visual Debugging

```bash
# Generate dependency graph
cscd graph --format dot | dot -Tsvg > graph.svg
```

### 6. Integration with CI/CD

```bash
# GitLab CI example
script:
  - cscd validate
  - cscd run test
  - cscd run build
  - cscd run deploy

# GitHub Actions example
- name: Run tests
  run: cscd run test
```

---

## Getting Help

For more information:

- **Quick help:** `cascade --help`
- **Command help:** `cscd run --help`
- **Documentation:** https://gitlab.com/cascascade/cscd
- **Issues:** https://gitlab.com/cascascade/cscd/-/issues
- **Examples:** See `examples/` directory

---

**Version:** 0.1.0  
**License:** MIT
