# StrumBook

Tools for building songbooks for ukulele groups and bands from collections of ChordPro
songs: tablet-friendly PDFs with a tappable index, searchable text and chord diagrams
for each instrument. The [problem statement](docs/problem-statement.md) explains why.

**Status: early development.** It builds a book from one folder of songs, in one
layout, with GCEA chord diagrams.

## Try it

You need [uv](https://docs.astral.sh/uv/) and git. From the repository root:

```sh
uv sync --locked
uv run --locked strumbook build tests/fixtures/carols -o output/carols.pdf
```

`strumbook build SONGS_DIR -o BOOK.pdf` reads every `.cho` file in the folder and
writes a PDF for a tablet: an index, the songs sorted by title with chord diagrams down
the side, and a chord reference page. Every page has a strip of links along the bottom
to the index, each letter and the reference page. Options:

- `--title TEXT`: the book's title (default: the folder's name).
- `--mid-word-chords inline|above`: a chord inside a word, such as `a[D]wakes`, is
  drawn inline by default, which splits the word for search. `above` floats it over
  the word instead, so search finds the whole word.
- `--pdf-tags on|off`: tags help screen readers but make the PDF about twice the
  size (about 30 MB for 500 songs); `off` gives a smaller file.

StrumBook warns about chords it has no diagram for and ChordPro directives it skips.
It needs no network access. It installs on macOS, Linux and Windows on x64, but not on
Windows on ARM yet: its Typst renderer has no package for it.

## How work happens

Each change starts as a GitHub issue (Build, Bug or Spike) and arrives as a pull
request. [CLAUDE.md](CLAUDE.md) is the working agreement; the
[architecture](docs/architecture.md), [developer guide](docs/developer-guide.md) and
[threat model](docs/threat-model.md) cover the rest.

Song collections live in their own repositories, which can be private. This repository
holds only the tool and public-domain test songs.

## Licence

[MIT](LICENSE). The licence covers the software, not any songs it is used with.
