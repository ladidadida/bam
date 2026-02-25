# Bam CLI Reference

Complete command-line interface documentation for Bam.

## Installation

```bash
# Using uv (recommended)
uv pip install bam

# Using pip
pip install bam
```

## Global Options

All commands support these global options:

- `--help` - Show help message and exit
- `--version` - Show version and exit

## Commands

### `bam run`

Execute one or more tasks with their dependencies.

**Usage:**
```bash
bam run [OPTIONS] TASK [TASK...]
```

**Arguments:**
- `TASK` - One or more task names to execute (required)

**Options:**
- `--config PATH` - Path to bam.yaml configuration file
  - Default: Searches for `bam.yaml` or `.bam.yaml` in current directory and parents
- `--dry-run` - Show what would be executed without running anything
- `--quiet, -q` - Suppress command output (only show results)
- `--no-cache` - Disable cache reads and writes for this run

**Examples:**

```bash
# Run single task
bam run build

# Run multiple tasks
bam run lint test build

# Dry run to see execution plan
bam run --dry-run deploy

# Run with specific config
bam run --config path/to/config.yaml test

# Run without caching
bam run --no-cache build

# Quiet mode (minimal output)
bam run -q test
```

**Behavior:**
- Automatically runs all dependencies in topological order
- Uses cached outputs when available (unless `--no-cache`)
- Fails fast on first task error
- Returns exit code 0 on success, 1 on failure

---

### `bam list`

Display all configured tasks and their dependencies.

**Usage:**
```bash
bam list [OPTIONS]
```

**Options:**
- `--config PATH` - Path to bam.yaml configuration file

**Examples:**

```bash
# List all tasks
bam list

# List with specific config
bam list --config examples/hello-world/bam.yaml
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

### `bam graph`

Visualize the task dependency graph.

**Usage:**
```bash
bam graph [OPTIONS]
```

**Options:**
- `--config PATH` - Path to bam.yaml configuration file
- `--format FORMAT` - Output format: `ascii` or `dot`
  - Default: `ascii`
  - `ascii` - Tree-style Unicode box drawing
  - `dot` - GraphViz DOT format for rendering

**Examples:**

```bash
# Show ASCII graph
bam graph

# Generate DOT format for GraphViz
bam graph --format dot > graph.dot
dot -Tpng graph.dot -o graph.png

# With specific config
bam graph --config path/to/config.yaml
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

### `bam validate`

Validate configuration file syntax and dependency graph.

**Usage:**
```bash
bam validate [OPTIONS]
```

**Options:**
- `--config PATH` - Path to bam.yaml configuration file

**Examples:**

```bash
# Validate default config
bam validate

# Validate specific config
bam validate --config path/to/config.yaml
```

**Checks:**
✅ Valid YAML syntax  
✅ Required fields present  
✅ No cyclic dependencies  
✅ All dependencies defined  
✅ No duplicate task names

**Output:**
```
Configuration is valid: /path/to/bam.yaml
Discovered 12 task(s).
```

**Error Example:**
```
Error: Cyclic dependency detected in task graph:
  a -> b -> c -> a
```

---

### `bam clean`

Clean local cache artifacts.

**Usage:**
```bash
bam clean [OPTIONS]
```

**Options:**
- `--cache-dir PATH` - Cache directory to clean
  - Default: `.bam/cache`
- `--force, -f` - Skip confirmation prompt

**Examples:**

```bash
# Clean default cache (with confirmation)
bam clean

# Force clean without confirmation
bam clean --force

# Clean custom cache directory
bam clean --cache-dir /path/to/cache
```

**Interactive Mode:**
```
Cache directory: .bam/cache
Cache size: 142.35 MB
Delete all cached artifacts? [y/N]: 
```

**Force Mode:**
```
✓ Cache cleared
```

---

## Environment Variables

Configure bam behavior via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `BAM_CONFIG` | Path to configuration file | `./bam.yaml` |
| `BAM_CACHE_DIR` | Local cache directory | `./.bam/cache` |
| `BAM_CACHE_TYPE` | Cache backend type | `local` |
| `BAM_LOG_LEVEL` | Logging verbosity | `INFO` |

**Examples:**

```bash
# Use custom config location
export BAM_CONFIG=~/.config/bam.yaml
bam run build

# Use different cache directory
export BAM_CACHE_DIR=/tmp/bam-cache
bam run test

# Debug mode
export BAM_LOG_LEVEL=DEBUG
bam run --dry-run deploy
```

---

## Configuration File Discovery

Bam searches for configuration files in this order:

1. `--config` CLI argument
2. `BAM_CONFIG` environment variable
3. `./bam.yaml` in current directory
4. `./.bam.yaml` (hidden file) in current directory
5. Walk up directory tree looking for either file

**Example:**

```
/home/user/project/src/
  └─ No config here, searches parent...
/home/user/project/
  └─ bam.yaml ✓ Found!
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
bam run --dry-run build | grep "Would execute"
```

### 2. Cache Debugging

```bash
# Run without cache to force rebuild
bam run --no-cache build

# Check cache status
bam clean  # Shows size before confirming
```

### 3. Configuration Validation

```bash
# Always validate after config changes
bam validate && echo "Config OK" || echo "Config ERROR"
```

### 4. Complex Workflows

```bash
# Run multiple independent targets
bam run test-frontend test-backend

# Combine with shell scripts
bam run build && docker build -t myapp .
```

### 5. Visual Debugging

```bash
# Generate dependency graph
bam graph --format dot | dot -Tsvg > graph.svg
```

### 6. Integration with CI/CD

```bash
# GitLab CI example
script:
  - bam validate
  - bam run test
  - bam run build
  - bam run deploy

# GitHub Actions example
- name: Run tests
  run: bam run test
```

---

## Getting Help

For more information:

- **Quick help:** `bam --help`
- **Command help:** `bam run --help`
- **Documentation:** https://gitlab.com/cascascade/bam
- **Issues:** https://gitlab.com/cascascade/bam/-/issues
- **Examples:** See `examples/` directory

---

**Version:** 0.1.0  
**License:** MIT
