# Contributing to bam

Thanks for contributing to bam.

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
```

## Development Workflow

- Keep changes focused and small.
- Follow existing code style and naming conventions.
- Add or update tests for behavior changes.

## Useful Commands

```bash
uv sync
bam lint
bam typecheck
bam test-unit
```

## Pull Requests

- Describe what changed and why.
- Reference any related issue or roadmap item.
- Ensure CI passes before requesting review.

## Commit Messages

Use concise, imperative messages (e.g. `add task graph cycle detection`).

## Remotes

This project is mirrored on two remotes:

| Remote | URL | Role |
|--------|-----|------|
| `origin` | `gitlab.com/cascascade/bam` | Primary — CI, PyPI releases |
| `github` | `github.com/ladidadida/bam` | Mirror — schema publishing, future primary |

After pushing to `origin`, please also push to `github`:

```bash
git push origin main && git push github main
```

Tags must be pushed to both remotes:

```bash
git push origin vX.Y.Z && git push github vX.Y.Z
```

See `AGENTS.md` → *Dual-Remote Setup* for full details.
