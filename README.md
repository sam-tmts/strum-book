# StrumBook

Tools for building songbooks for ukulele groups and bands from collections of ChordPro
songs: tablet-friendly PDFs with a tappable index, searchable text and chord diagrams
for each instrument. The [problem statement](docs/problem-statement.md) explains why.

**Status: early development.** It builds a song library or a gig set list from a
StrumBook file, or a song library from one folder of songs, with chord diagrams for
standard (GCEA) or baritone (DGBE) ukulele.

## Try it

You need [uv](https://docs.astral.sh/uv/), and git to clone this repository. From its
root:

```sh
uv sync --locked
uv run --locked strumbook build tests/fixtures/carols -o output/carols.pdf
```

`strumbook build BOOK.strumbook.toml -o BOOK.pdf` builds the book a
[StrumBook file](docs/strumbook-files.md) describes: its title, which song collections
to draw on (folders, or git repositories it downloads), which songs, and its settings.
`strumbook build SONGS_DIR -o BOOK.pdf` is a shortcut for every `.cho` file in one
folder.

Either way, StrumBook writes a PDF for a tablet: a title page, an index, the songs
sorted by title (or `{sorttitle}`) with chord diagrams down the side, two Reference
pages (every root's chord shapes in nine types, then the notes in each chord) and
Credits. Choruses are marked, and a small line under each title gives the
song's subtitle and its words, music and translation credits. Every page after the
title page has a strip of links along the bottom to the index, each letter and the
reference page. A StrumBook file of type `set-list` makes a gig book instead: a
running order, then each set's songs, with optional break pages and spares at the back.

Options, which override a StrumBook file's own settings:

- `--title TEXT`: the book's title (default: the StrumBook file's title, or the
  folder's name).
- `--edition TEXT`: the edition line on the title page (default: today's date).
- `--type song-library|set-list`: the type of book (default song-library, A to Z). A
  set list needs a StrumBook file, and leaves out the chord diagrams, index, link
  strip, Reference pages and Credits unless you turn them on.
- `--title-page on|off`: include the title page (default on).
- `--chords on|off`: the chord diagrams down the side of each song (default on; off
  for a set list). With `off`, the lyrics use the whole page width and the chord
  names in them stay.
- `--index on|off`, `--navigation on|off` (the link strip) and `--reference on|off`:
  include each (default on).
- `--reference-notes on|off`: include the "Notes in each chord" page in Reference
  (default on). With `off`, Reference keeps just the chord shapes.
- `--reference-charts GCEA,DGBE`: a chord shapes page in Reference for each tuning
  listed, in order, so one book can serve standard and baritone players (default: the
  book's own tuning). Song diagrams still follow `--tuning`.
- `--set-breaks on|off`: a page before each set in a set list (default on when there's
  more than one set, or spares).
- `--credits on|off`: include Credits (default on): each song's credits, linked both
  ways with its credit line, then an "About this book" page saying how it was made.
- `--mid-word-chords inline|above`: a chord inside a word, such as `a[D]wakes`, is
  drawn inline by default, which splits the word for search. `above` floats it over
  the word instead, so search finds the whole word.
- `--tuning GCEA|DGBE`: the chord shapes in the diagrams and, unless
  `--reference-charts` says otherwise, on the Reference page, for a standard ukulele (`GCEA`, or `ukulele`; the default) or a baritone (`DGBE`, or
  `baritone`), in any case. The chord names stay the same. The title page says which
  tuning, when the book has diagrams or Reference pages.
- `--slash-chords simplify|as-written`: `simplify` drops a slash chord's bass note
  when it's already in the chord, so `Am/C` prints as `Am`, but `C/B` stays. The
  default is `simplify` for GCEA, which has no real bass string, and `as-written` for
  DGBE. The song files are never changed.
- `--pdf-tags on|off`: tags help screen readers but make the PDF about twice the
  size (about 30 MB for 500 songs); `off` gives a smaller file.

To avoid page turns, a song drops its diagram column if the diagrams would push it onto
a second page, or if it has more than 8 diagrams and needs more than one page anyway.
The chord names in the lyrics always stay. StrumBook warns about ChordPro directives
it doesn't know and, when the book has diagrams, about chords it has no diagram for. Chords are played as written:
`{capo}` is ignored.

To see a full book, `make christmas` builds all 28 carols from
[Christmas Songs](https://github.com/pathawks/Christmas-Songs) into
`output/christmas-carols.pdf`, from the StrumBook file
`books/christmas.strumbook.toml`.

[Git](https://git-scm.com) is optional: StrumBook needs it, and the network, only to
download a StrumBook file's `git` sources. It installs on macOS, Linux and Windows
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
| [Libertinus Serif](https://github.com/alerque/libertinus) | Bundled with Typst, it sets the sharp and flat signs (♯ ♭) on the Reference pages, which Atkinson Hyperlegible doesn't have. |
| [ChordPro](https://www.chordpro.org) | The song format: lyrics with chords inline, which StrumBook reads. |
| [Git](https://git-scm.com) | Downloads the song collections a StrumBook file names, if they're in git, with the book maker's own sign-in. |
| [Christmas Songs](https://github.com/pathawks/Christmas-Songs) | Public-domain carols in ChordPro, used as test songs. |
| [uv](https://docs.astral.sh/uv/) | Sets up the Python environment and pins every dependency. |
| [pytest](https://pytest.org) | Runs the tests. |
| [pypdf](https://github.com/py-pdf/pypdf) | Lets the tests read the books they build: text, links and bookmarks. |
| [Ruff](https://docs.astral.sh/ruff/) | Checks and formats the code. |

The exact versions are pinned in [`uv.lock`](uv.lock).
