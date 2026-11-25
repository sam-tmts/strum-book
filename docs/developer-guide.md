# Developer guide

The tools, commands and conventions for working on StrumBook. For how the code is
structured, see [architecture](architecture.md).

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
directories and public-domain or synthetic songs. `tests/conftest.py` blocks network
access; a test that needs songs uses a small fixture in `tests/`.

## Working with song collections

Collections live in their own repositories. For work that needs one, add its folder to
the Claude Code session (**+ > Add folder** in the desktop app), and write generated
books outside this repository. Treat collections as read-only unless the task says
otherwise.

## Templates

| For | Where |
|-----|-------|
| Build, Bug and Spike issues | `.github/ISSUE_TEMPLATE/` (GitHub only reads them there) |
| Pull requests | `.github/PULL_REQUEST_TEMPLATE.md` |
| ADRs | [`templates/adr.md`](templates/adr.md), copied to `adr/NNNN-short-title.md` |
| Release notes | [`templates/release-notes.md`](templates/release-notes.md) |

## Releases

Versions follow [semver](https://semver.org) and live only in `pyproject.toml`. To
release: choose the version from the semver impact of the PRs merged since the last
release; set it in `pyproject.toml` through a PR; once merged, tag `vX.Y.Z` on `main`
and publish a GitHub release with notes from the template. The GitHub releases are the
changelog.
