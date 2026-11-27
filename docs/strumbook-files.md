# StrumBook files

A StrumBook file is a short recipe for one book: which song collections to use, which
songs, and how to build it. It holds no songs itself, so it can live anywhere: in its
own repository, in a folder on your laptop, or inside a collection. Build it with:

```sh
strumbook build carols.strumbook.toml -o carols.pdf
```

The book comes out the same every time, with no options to remember. (`strumbook build
SONGS_DIR -o BOOK.pdf` still works as a shortcut for "every song in one folder".)

## Types of book

A StrumBook file's `type` says how the book is put together:

| Type | The songs | What else is in the book |
|------|-----------|--------------------------|
| `song-library` (the default) | A to Z by title | A title page, an index, a strip of links along the bottom of each page, two Reference pages (chord shapes, and the notes in each chord) and Credits |
| `set-list` | In the order they're played, perhaps in sets, with spares at the back | A title page, a running-order page and a break page before each set; the rest, chord diagrams included, only if you turn it on |

Some of the books people make with them:

- **A group's songbook:** a `song-library` of hundreds of songs, everything in one or
  more collections.
- **A band's book:** a `song-library` of tens to a couple of hundred songs picked from
  the group's collection and the band's own.
- **A gig:** 10 to 20 songs in running order, perhaps in separate sets: a `set-list`.

## Examples

A whole collection, fetched from GitHub:

```toml
[book]
title = "Christmas Carols"
type = "song-library"            # the default; shown here for clarity
edition = "2026-12-01"           # shown on the title page
subtitle = "Christmas 2026"
notes = """
Bring mince pies. Carols marked with a capo are played as written.
"""

[sources.carols]
git = "https://github.com/pathawks/Christmas-Songs"
pin = "263d5ce"                  # optional; leave it out to always take the latest
link = "https://github.com/pathawks/Christmas-Songs"   # shown in Credits

[songs]
include = "all"                  # every song in every source

[build]
title-page = true
credits = true
```

A few songs from a folder on this computer:

```toml
[book]
title = "Carol singing at the station"

[sources.carols]
path = "../Christmas-Songs"

[songs]
pick = [
  "carols:Away In A Manger",
  "carols:O Little Town Of Bethlehem",
]
```

A gig in two sets, with spares at the back:

```toml
[book]
title = "Carols on the green"
type = "set-list"
edition = "2026-12-20"

[sources.carols]
path = "../Christmas-Songs"

[[songs.set]]
name = "Set 1"
running-time = "25 min"
notes = """
Start 6:30. Away In A Manger twice if the children join in.
"""
songs = [
  "carols:Away In A Manger",
]

[[songs.set]]
name = "Set 2"
running-time = "20 min"
notes = """
Collection buckets out before this set.
"""
songs = [
  "carols:O Come O Come Emmanuel",
]

[songs]
spares = [                       # at the back, under "Spares and encores"
  "carols:O Little Town Of Bethlehem",
]
```

## The format

A StrumBook file is [TOML](https://toml.io) and its name ends in `.strumbook.toml`, so
editors and GitHub know how to show it. Text goes in quotes; `"""` starts and ends text
that runs over several lines.

### `[book]`

| Key | Meaning |
|-----|---------|
| `title` | The book's title. Required. |
| `type` | `"song-library"` (the default) or `"set-list"`: see [Set lists](#set-lists). |
| `edition` | The edition line on the title page, such as a date. Default: the day you build it. |
| `subtitle` | A line under the title on the title page. |
| `notes` | Plain text for the title page, printed as typed, line breaks and all. Separate paragraphs with a blank line. |

### `[sources.<name>]`

One table for each collection the book draws on. The name, in lower case letters,
digits and hyphens, is how songs refer to it, and how Credits names it:
`[sources.carols]` is `carols`.

| Key | Meaning |
|-----|---------|
| `path` | A folder on this computer, absolute or relative to the StrumBook file. |
| `git` | A git repository's address, `https://…` or ssh (`git@github.com:…`). StrumBook downloads it with your computer's `git`, so private repositories work if you can already clone them. Keep passwords and tokens out of the address: git's own sign-in looks after them. |
| `pin` | `git` only: a commit or tag to use. Without one, every build fetches the latest songs. Pin a book that must never change. (A branch name stays wherever it was when first downloaded.) |
| `folder` | Where the songs are inside the collection. Default: `songs/` if there is one, otherwise the top level. |
| `link` | A public web address for the collection, shown in Credits. |

Each source has either `path` or `git`; two sources may share a `git` address (with
different `folder`s, say) only if they also share its `pin`.

Credits lists every source by its name, with its `link`, or "No public link" if it has
none. A `git` address is never printed, so a private repository's address doesn't end
up in a book you share; give a public collection a `link`.

### `[songs]`

A song is written as `source:file name`: the source's name, a colon, then the song's
file name without `.cho`, spaces and all. A `song-library` takes any mix of these:

| Key | Meaning |
|-----|---------|
| `include` | `"all"` for every song in every source, or a list of source names, such as `["group", "band"]`. |
| `pick` | A list of single songs, such as `["carols:Away In A Manger"]`. |
| `exclude` | Songs to leave out, even if `include` or `pick` brings them in. A song that no longer exists only gets a warning. |

A `song-library` sorts its songs A to Z by title, and so does its index. If two sources
have a song with the same file name, the book has both; the index shows each one's
artist. A `set-list` chooses its songs differently: see [Set lists](#set-lists).

### `[build]`

The same settings as the command-line options, without the `--` in front. On/off
options take `true` or `false`. A set list leaves out the extras unless you turn them
on.

| Key | Meaning | `song-library` | `set-list` |
|-----|---------|----------------|------------|
| `title-page` | The title page | on | on |
| `chords` | The chord diagrams down the side of each song | on | off |
| `index` | The A-to-Z index | on | off |
| `navigation` | The strip of links along the bottom of each page | on | off |
| `reference` | The Reference pages: chord shapes, and the notes in each chord | on | off |
| `credits` | Credits and "About this book" | on | off |
| `set-breaks` | A page before each set | — | on when there's more than one set, or spares |
| `mid-word-chords` | `"inline"` or `"above"`: see the [README](../README.md) | `"inline"` | `"inline"` |
| `tuning` | `"GCEA"` (or `"ukulele"`) or `"DGBE"` (or `"baritone"`), in any case: see the [README](../README.md) | `"GCEA"` | `"GCEA"` |
| `slash-chords` | `"simplify"` or `"as-written"`: see the [README](../README.md) | `"simplify"` for GCEA, `"as-written"` for DGBE | the same |
| `pdf-tags` | Tag the PDF for screen readers | on | on |

## Set lists

A `set-list` book is for a gig: the songs in running order, with as little clutter as
possible. It takes its songs from `[[songs.set]]` tables, one per set, in order:

| Key | Meaning |
|-----|---------|
| `name` | The set's name, such as `"Set 1"`. Required. |
| `songs` | Its songs, in running order. Required. |
| `running-time` | Free text, such as `"25 min"`. |
| `notes` | Plain text for the set's break page: songs to drop if running late, reminders, and so on. |

`spares`, under `[songs]`, lists songs you might add or play as encores; they come
after the last set, under "Spares and encores". A song can be in only one set or in
the spares. A gig with no sets can use `pick` instead, as one unnamed set in the order
listed. `include` and `exclude` are errors in a set list.

The book has a title page, a running-order page listing each set and its songs (tap a
song to go to it), then each set's songs. When `set-breaks` is on, each set and the
spares start with a break page showing the name, running time and notes (an unnamed
`pick` set has none). Each song's title and page number link back to the running
order. With `navigation` on, the strip along the bottom links the running order, each
set, the spares and (if it's on) Reference. A set list with only a `pick` list and no
spares has no strip.

## Which setting wins

Settings come in three layers, each overriding the one before:

1. **The type's defaults**, from `--type` if you give it, otherwise the StrumBook
   file's `type`, otherwise `song-library`.
2. **The StrumBook file's `[build]` settings.** These still apply if you change the
   type on the command line, because they were written into that book on purpose. (A
   book with sets only builds as a set list, and one with `include` only as a song
   library.)
3. **Options on the command line**, such as `--credits off`. `--title` and `--edition`
   override the StrumBook file's `title` and `edition` too.

## When something's wrong

StrumBook stops with an error naming the problem, and writes no PDF, if the file isn't
valid TOML or has no title, a song in `pick`, a set or the spares doesn't exist (file
names must match exactly, capitals included), a song is in a set list twice, a set has
no name or no songs, a source is unknown, has no songs or can't be downloaded, a
setting has a value StrumBook doesn't accept, or a `[songs]` key belongs to the other
type (`include` or `exclude` in a set list; sets or `spares` in a song library; sets
and `pick` together). `--type set-list` needs a StrumBook file. Keys it doesn't know
only get a warning, so a StrumBook file written for a newer StrumBook still builds.
Unknown directives in a song are warnings, as when building from a folder; so are
chords StrumBook has no diagram for, when `chords` is on.

If the file isn't valid TOML, the error says which line. For the usual slips, it shows
how to write the line: a ChordPro line such as `{title: Carols}`, `title: Carols` or
`title = Carols` all become `title = "Carols"`, and `credits = off` becomes
`credits = false`.

## Downloaded collections

StrumBook keeps the collections it downloads in your computer's cache folder:
`~/Library/Caches/strumbook/` on a Mac, `$XDG_CACHE_HOME/strumbook/` (usually
`~/.cache/strumbook/`) on Linux and `%LOCALAPPDATA%\strumbook\cache\` on Windows.
Deleting it is always safe: the next build downloads them again. Without a network, a
build uses the copy from last time and warns that it may be out of date. Only `git`
sources need `git` installed.
