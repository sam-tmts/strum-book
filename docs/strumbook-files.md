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
| `song-library` (the default) | A to Z by title | A title page, an index, a strip of links along the bottom of each page, a chord reference page and Credits |
| `set-list` | In the order they're played | Coming soon |

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

## The format

A StrumBook file is [TOML](https://toml.io) and its name ends in `.strumbook.toml`, so
editors and GitHub know how to show it. Text goes in quotes; `"""` starts and ends text
that runs over several lines.

### `[book]`

| Key | Meaning |
|-----|---------|
| `title` | The book's title. Required. |
| `type` | `"song-library"`, the default and, for now, the only type. |
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

Any mix of these. A song is written as `source:file name`: the source's name, a colon,
then the song's file name without `.cho`, spaces and all.

| Key | Meaning |
|-----|---------|
| `include` | `"all"` for every song in every source, or a list of source names, such as `["group", "band"]`. |
| `pick` | A list of single songs, such as `["carols:Away In A Manger"]`. |
| `exclude` | Songs to leave out, even if `include` or `pick` brings them in. A song that no longer exists only gets a warning. |

A `song-library` sorts its songs A to Z by title, and so does its index. If two sources
have a song with the same file name, the book has both; the index shows each one's
artist.

### `[build]`

The same settings as the command-line options, without the `--` in front. On/off
options take `true` or `false`.

| Key | Meaning |
|-----|---------|
| `title-page` | Include the title page (default `true`). |
| `credits` | Include Credits and "About this book" (default `true`). |
| `mid-word-chords` | `"inline"` (default) or `"above"`: see the [README](../README.md). |
| `pdf-tags` | Tag the PDF for screen readers (default `true`). |

## Which setting wins

Settings come in three layers, each overriding the one before:

1. **The type's defaults**, from `--type` if you give it, otherwise the StrumBook
   file's `type`, otherwise `song-library`.
2. **The StrumBook file's `[build]` settings.** These still apply if you change the
   type on the command line, because they were written into that book on purpose.
3. **Options on the command line**, such as `--credits off`. `--title` and `--edition`
   override the StrumBook file's `title` and `edition` too.

## When something's wrong

StrumBook stops with an error naming the problem, and writes no PDF, if the file isn't
valid TOML or has no title, a song in `pick` doesn't exist (file names must match
exactly, capitals included), a source is unknown, has no songs or can't be downloaded,
or a setting has a value StrumBook doesn't accept. Keys it doesn't know only get a
warning, so a StrumBook file written for a newer StrumBook still builds. Unknown chords
and directives in a song are warnings, as when building from a folder.

## Downloaded collections

StrumBook keeps the collections it downloads in your computer's cache folder:
`~/Library/Caches/strumbook/` on a Mac, `$XDG_CACHE_HOME/strumbook/` (usually
`~/.cache/strumbook/`) on Linux and `%LOCALAPPDATA%\strumbook\cache\` on Windows.
Deleting it is always safe: the next build downloads them again. Without a network, a
build uses the copy from last time and warns that it may be out of date. Only `git`
sources need `git` installed.
