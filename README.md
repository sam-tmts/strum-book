# StrumBook

Tools for building songbooks for ukulele groups and bands from collections of ChordPro
songs: tablet-friendly PDFs with a tappable index, searchable text and chord diagrams
for each instrument. The [problem statement](docs/problem-statement.md) explains why.

**Status: early development.** Only `strumbook --help` and `--version` work so far.

## Try it

You need [uv](https://docs.astral.sh/uv/) and git. From the repository root:

```sh
uv sync --locked
uv run --locked strumbook --help
```

## How work happens

Each change starts as a GitHub issue (Build, Bug or Spike) and arrives as a pull
request. [CLAUDE.md](CLAUDE.md) is the working agreement; the
[architecture](docs/architecture.md), [developer guide](docs/developer-guide.md) and
[threat model](docs/threat-model.md) cover the rest.

Song collections live in their own repositories, which can be private. This repository
holds only the tool and public-domain test songs.

## Licence

[MIT](LICENSE). The licence covers the software, not any songs it is used with.
