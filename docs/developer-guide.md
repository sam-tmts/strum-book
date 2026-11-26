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
access; a test that needs songs uses the carols in `tests/fixtures/carols/` or writes
synthetic ones. Tests read built PDFs with pypdf (text, links, bookmarks), through
`tests/pdf_helpers.py`.

## Sample books

CI builds a sample book from the fixture carols on every run that passes its checks,
and uploads it as a PDF, kept for 30 days. Its title and file name give the PR number
and head commit, so samples can be told apart on a tablet; on a PR, it's built from
the PR merged into its base. To find it, open **Details** for `checks` on the PR, then
the run's **Summary**: the sample is linked there and listed under Artifacts.
Downloading needs a GitHub sign-in.

CI builds only `tests/fixtures/`. Anyone signed in to GitHub can download the sample,
so never point it at private songs. To build one locally, into `output/` (which git
ignores):

```sh
uv run --locked strumbook build tests/fixtures/carols -o output/carols.pdf
```

`make christmas` builds the full book from all 28 carols in
[pathawks/Christmas-Songs](https://github.com/pathawks/Christmas-Songs), pinned to a
commit in the `Makefile`. It clones them into `collections/christmas-songs/` (git
ignores `collections/`, so nothing is committed), writes
`output/christmas-carols.pdf` and prints the number of warnings, which should be 0.
It needs network access to github.com, so CI doesn't run it. After the pin changes,
delete `collections/christmas-songs/` so the next run clones afresh. In a Claude Code sandbox
the clone fails, because the sandbox won't let git write a `.git/config` inside the
project: run it in your own terminal.

The layout lives in `src/strumbook/layout/book.typ`; the chord shapes in
`src/strumbook/chords.json` (frets per string, G C E A).

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
