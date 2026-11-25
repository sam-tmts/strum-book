# Developer guide

## Layout

| Path | What |
|------|------|
| `src/strumbook/cli.py` | Command-line entry point (`strumbook`, or `python -m strumbook`) |
| `tests/` | pytest tests; `conftest.py` blocks network access during tests |
| `docs/problem-statement.md` | The problem, the direction and what we've learnt |
| `docs/adr/` | Lasting decisions |

There's no rendering or import code yet. Add modules when an issue needs them, not
before.

## Tools

Python 3.12, [uv](https://docs.astral.sh/uv/) for environments and the lockfile,
pytest, and Ruff for lint and formatting ([ADR-0001](adr/0001-python-toolchain.md)).
Run commands from the repository root:

```sh
uv sync --locked      # set up .venv from uv.lock
make check            # pytest, ruff check, ruff format --check: the same as CI
make format           # format the code
make build            # build the package into dist/
```

`--locked` makes a command fail rather than quietly change `uv.lock`. To change
dependencies, edit `pyproject.toml`, run `uv lock`, and commit both files.

## Tests

Name tests for the behaviour they check (`test_unknown_arguments_fail`). Use temporary
directories and public-domain or synthetic songs. Tests can't reach the network; a
test that needs a song collection uses a small fixture in `tests/`.

## Working with song collections

Collections live in their own repositories. For work that needs one, add its folder to
the Claude Code session (**+ > Add folder** in the desktop app), and write generated
books outside this repository. Treat collections as read-only unless the task says
otherwise.

## Decisions

Write an ADR for a decision later work must respect: what was decided, why, and the
alternatives considered. Keep it short and review it in the same PR.
