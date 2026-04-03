# Bam CLI Reference

Complete command-line interface documentation for bam.

## Installation

```bash
# Using uv (recommended)
uv pip install bam-tool

# Using pip
pip install bam-tool
```

## Overview

bam uses a **flat command interface**. Tasks defined in `bam.yaml` are run
directly as `bam <task>`. Management operations are flags on the same command.

```
bam [OPTIONS] [TASK]
```

Quick reference:

| What you want | Command |
|---|---|
| Run a task | `bam <task>` |
| List tasks | `bam --list` |
| Validate config | `bam --validate` |
| Show dependency graph | `bam --graph` |
| Export DOT graph | `bam --graph-dot` |
| Generate CI pipeline | `bam --ci` |
| Clean cache | `bam --clean` |
| Show version | `bam --version` |

---

## Running Tasks

```bash
bam <task> [OPTIONS]
```

Tasks are resolved from the `tasks:` section of `bam.yaml`. All dependencies
are executed automatically in topological order.

**Options:**

| Flag | Default | Description |
|---|---|---|
| `--jobs N` / `--jobs auto` | `auto` | Number of parallel workers |
| `--dry-run` | `false` | Print execution plan without running |
| `--no-cache` | `false` | Disable cache reads and writes |
| `--quiet`, `-q` | `false` | Suppress command output |
| `--plain` | `false` | Use plain output (no rich UI) |
| `--config PATH` | auto-discover | Path to `bam.yaml` |

**Examples:**

```bash
# Run a single task
bam build

# Run with explicit parallelism
bam build --jobs 4
bam build --jobs auto   # detect CPU count
bam build --jobs 1      # sequential

# Dry run — show what would run
bam build --dry-run

# Disable caching for this run
bam build --no-cache

# Quiet (only show pass/fail, not command output)
bam build -q

# Force plain output (useful in scripts)
bam build --plain

# Use a different config file
bam build --config path/to/bam.yaml
```

**Behavior:**
- Automatically runs all dependencies in topological order
- Independent tasks run in parallel (controlled by `--jobs`)
- Uses cached outputs when available (unless `--no-cache`)
- Fails fast: the first failed task stops dependent tasks
- Returns exit code 0 on success, 1 on failure

**Interactive Tree View** (TTY only, auto-detected):

```
📦 Tasks
├── ✓ lint               ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
├── ✓ typecheck          ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
│   └── ✓ test           ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%
│       └── ✓ build      ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 100%

✓ Successfully executed 4 task(s)
```

**Error Context:**

```
✗ Task failed: test
  Dependency chain:
    ├─ lint
    ├─ typecheck
    └─ test

⊘ Skipped 1 task(s) due to failure:
  • build
```

---

## Management Flags

### `--list`

Display all configured tasks and their dependencies.

```bash
bam --list
bam --list --config examples/hello-world/bam.yaml
```

**Output:**
```
Available tasks:
  • build
    depends on: lint, test
  • lint
  • test
```

---

### `--validate`

Validate configuration file syntax and dependency graph.

```bash
bam --validate
bam --validate --config path/to/bam.yaml
```

**Checks performed:**
✅ Valid YAML syntax
✅ Required fields present
✅ No cyclic dependencies
✅ All `depends_on` tasks are defined
✅ Runner configuration is valid

**Output:**
```
Configuration is valid: /path/to/bam.yaml
Discovered 8 task(s).
```

---

### `--graph` / `--graph-dot`

Visualize the task dependency graph.

```bash
# ASCII tree (default)
bam --graph

# DOT format for Graphviz
bam --graph-dot > graph.dot
dot -Tpng graph.dot -o graph.png

# With specific config
bam --graph --config path/to/bam.yaml
```

**ASCII Output:**
```
┌─ Roots (no dependencies)
│  ├─ setup-database
│  └─ install-deps
│
├─ Layer 1
│  ├─ lint-python
│  └─ lint-js
│
└─ Layer 2
   └─ test
```

**DOT Output:**
```dot
digraph TaskGraph {
  rankdir=LR;
  "setup" -> "build";
  "build" -> "test";
  "test" -> "deploy";
}
```

---

### `--clean` / `--clean-force`

Remove cached artifacts from the local cache directory.

```bash
# Prompt for confirmation before cleaning
bam --clean

# Skip confirmation
bam --clean-force

# Custom cache directory
bam --clean-force --cache-dir /path/to/cache
```

| Flag | Description |
|---|---|
| `--clean` | Clean with interactive confirmation prompt |
| `--clean-force` | Clean without confirmation |
| `--cache-dir PATH` | Cache directory (default: `.bam/cache`) |

---

### `--ci` / `--ci-dry-run`

Generate a CI pipeline file from the task graph.

```bash
# Write pipeline file (path determined by provider)
bam --ci

# Preview without writing
bam --ci-dry-run

# Write to a custom path
bam --ci --ci-output .github/workflows/ci.yml
```

Provider is configured in the `ci:` section of `bam.yaml`:

```yaml
ci:
  provider: github-actions   # or gitlab-ci
  runner: ubuntu-latest
  python_version: "3.14"
```

Each bam task becomes one CI job that calls `$BAM_TOOL <task>`, with
job dependencies wired from `depends_on`.

---

### `--version`

```bash
bam --version
```

---

## Global Options

| Option | Description |
|---|---|
| `--config PATH` | Path to `bam.yaml` (default: auto-discover upwards from cwd) |
| `--help` | Show help and exit |
| `--version` | Show version and exit |

---

## Shell Tab Completion

bam supports shell tab completion for task names. Install it once per shell:

```bash
# bash
bam --install-completion bash

# zsh
bam --install-completion zsh

# fish
bam --install-completion fish
```

After installation, `bam <TAB>` completes task names from `bam.yaml`.

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | Success |
| `1` | Task failed or configuration error |
| `2` | Invalid CLI usage (bad flag, missing argument) |

---

## Common Patterns

### CI/CD — plain output, no cache

```bash
bam --plain --no-cache ci-checks
```

### Dry run before deploy

```bash
bam deploy --dry-run
```

### Regenerate CI after updating bam.yaml

```bash
bam --ci && git add .gitlab/generated.gitlab-ci.yml && git commit -m "update CI"
```

### Validate before running

```bash
bam --validate && bam build
```

---

## Getting Help

- **Quick help:** `bam --help`
- **Documentation:** https://gitlab.com/cascascade/bam
- **Issues:** https://gitlab.com/cascascade/bam/-/issues
- **Examples:** See `examples/` directory

---

**Version:** 0.5.1  
**License:** MIT
