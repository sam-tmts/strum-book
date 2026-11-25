# ADR-0001: Python toolchain

Status: accepted, 2026-11-25.

## Decision

Python 3.12 with a `src/strumbook/` package and the standard library's `argparse`.
uv manages the environment and a committed lockfile; pytest for tests; Ruff for lint
and formatting; `make check` runs all three, locally and in CI. The build backend
(`uv_build`) is pinned in `pyproject.toml`. This matches smugback, so both projects
share one toolchain.

## Why

It's small, fast, and already working on Sam's machine. One lockfile and one check
command keep local runs and CI identical.

## Alternatives

pip with venv (no lockfile without more tools); Poetry (heavier, no gain here).
