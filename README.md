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
writes a PDF for a tablet: a title page, an index, the songs sorted by title (or
`{sorttitle}`) with chord diagrams down the side, a chord reference page and Credits.
Choruses are marked, and a small line under each title gives the song's subtitle and
its words, music and translation credits. Every page after the title page has a strip
of links along the bottom to the index, each letter and the reference page. Options:

- `--title TEXT`: the book's title (default: the folder's name).
- `--edition TEXT`: the edition line on the title page (default: today's date).
- `--source URL`: where the songs come from, printed and linked in Credits. Leave it
  out for a private collection.
- `--title-page on|off`: include the title page (default on).
- `--credits on|off`: include Credits (default on): each song's credits, linked both
  ways with its credit line, then an "About this book" page saying how it was made.
- `--mid-word-chords inline|above`: a chord inside a word, such as `a[D]wakes`, is
  drawn inline by default, which splits the word for search. `above` floats it over
  the word instead, so search finds the whole word.
- `--pdf-tags on|off`: tags help screen readers but make the PDF about twice the
  size (about 30 MB for 500 songs); `off` gives a smaller file.

To avoid page turns, a song drops its diagram column if the diagrams would push it onto
a second page, or if it has more than 8 diagrams and needs more than one page anyway.
The chord names in the lyrics always stay. StrumBook warns about chords it has no
diagram for and ChordPro directives it doesn't know. Chords are played as written:
`{capo}` is ignored.

To see a full book, `make christmas` builds all 28 carols from
[Christmas Songs](https://github.com/pathawks/Christmas-Songs) into
`output/christmas-carols.pdf`. It needs network access to clone them.

StrumBook itself needs no network access. It installs on macOS, Linux and Windows
(x64), but not yet on Windows on ARM: its Typst renderer has no package for it.

## How work happens

Each change starts as a GitHub issue (Build, Bug or Spike) and arrives as a pull
request. [CLAUDE.md](CLAUDE.md) is the working agreement; the
[architecture](docs/architecture.md), [developer guide](docs/developer-guide.md) and
[threat model](docs/threat-model.md) cover the rest.

Song collections live in their own repositories, which can be private. This repository
holds only the tool and public-domain test songs.

## Licence

[MIT](LICENSE). The licence covers the software, not any songs it is used with. The
bundled Atkinson Hyperlegible font has its own licence, the
[SIL Open Font License](src/strumbook/layout/fonts/OFL.txt).

## Thanks

StrumBook builds on the great work of these projects:

| Project | What it does for StrumBook |
|---------|----------------------------|
| [Typst](https://typst.app) | Lays out every page of the book and writes the PDF: searchable text, links and bookmarks. |
| [typst-py](https://github.com/messense/typst-py) | Bundles the Typst compiler as a Python package, so installing StrumBook needs nothing else. |
| [Atkinson Hyperlegible](https://www.brailleinstitute.org/freefont/) | The Braille Institute's typeface, designed to be easy to tell letters apart. It keeps lyrics clear on a tablet at arm's length. |
| [ChordPro](https://www.chordpro.org) | The song format: lyrics with chords inline, which StrumBook reads. |
| [Christmas Songs](https://github.com/pathawks/Christmas-Songs) | Public-domain carols in ChordPro, used as test songs. |
| [uv](https://docs.astral.sh/uv/) | Sets up the Python environment and pins every dependency. |
| [pytest](https://pytest.org) | Runs the tests. |
| [pypdf](https://github.com/py-pdf/pypdf) | Lets the tests read the books they build: text, links and bookmarks. |
| [Ruff](https://docs.astral.sh/ruff/) | Checks and formats the code. |

The exact versions are pinned in [`uv.lock`](uv.lock).
