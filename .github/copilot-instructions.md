# GitHub Copilot Instructions — Bam

> The primary agent context for this project lives in [`AGENTS.md`](../AGENTS.md) at the
> repository root. All AI agents (Copilot, Codex, Claude, Cursor, etc.) should treat that
> file as the single source of truth for architecture, conventions, and roadmap status.

## TL;DR for Copilot

**What is bam?** A content-addressed workflow orchestration tool (Python 3.13+, uv).
Bridges Make/Just and Bazel. YAML config → task graph → parallel async execution → CAS caching.

**Stack:** typer · pydantic · networkx · rich · asyncio · cascache_lib (gRPC)

**Key paths:**
- `src/bam_tool/cli.py` — CLI commands
- `src/bam_tool/config/` — YAML schema + parser
- `src/bam_tool/graph/builder.py` — dependency graph
- `src/bam_tool/executor/executor.py` — async subprocess execution
- `src/bam_tool/cache/__init__.py` — cache backend (via cascache_lib)
- `spec/roadmap.md` — phase-by-phase progress (authoritative)

**Style:** type hints everywhere · pathlib · dataclasses · async I/O · ruff + pyright

**Run tests:** `uv run pytest`  
**Current phase:** Phase 3 — Remote cache hardening (see `spec/roadmap.md`)
