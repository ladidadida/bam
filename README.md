# Cascade

Flow naturally through your build pipeline 🌊

Cascade is a content-addressed workflow orchestration tool that brings content-addressable storage (CAS) ideas to everyday development tasks. It sits between simple task runners and heavy build systems by keeping workflows declarative while adding smart caching.

## Status

- Phase: Core MVP (Phase 1)
- Runtime target: Python 3.13+
- Package manager: uv

## Why Cascade

- Flow, don’t fight: wrap existing commands instead of replacing toolchains
- Cache everything: deterministic content hashes for fast rebuilds
- Fail gracefully: local-first behavior with optional remote CAS
- Progressive complexity: simple tasks stay simple

## Quick Start

```bash
uv sync
uv run cascade --help
```

## Current CLI Skeleton

```bash
cascade run <task>
cascade list
cascade clean [--cache-dir .cascade/cache]
cascade graph
```

## Development

```bash
just install
just lint
just typecheck
just test
```

## Project Layout

```text
src/cascade/        # Application package
tests/              # Unit and component tests
docs/               # Project documentation
spec/               # Design + roadmap source of truth
examples/           # Example project configs
```

## Roadmap

Implementation planning is tracked in `spec/roadmap.md` and the design baseline lives in `spec/design.md`.

## Contributing

See `CONTRIBUTING.md` for setup, coding, and PR expectations.

## License

MIT (see `LICENSE`).
