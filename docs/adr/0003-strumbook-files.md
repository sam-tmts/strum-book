# ADR-0003: Books are described by StrumBook files

Status: Accepted. Date: 2026-11-27. Issues: #12, #13.

## Context

A book used to be "every song in one folder", with its settings typed as command-line
options every time. Real books draw on several collections, some of them private git
repositories, and are built again and again: a group's songbook, a band's book, a gig.
Whoever builds one shouldn't have to remember how. Book makers are often not
technical, so the description has to be easy to read and write by hand.

## Decision

A book is described by a **StrumBook file**, documented in
[`strumbook-files.md`](../strumbook-files.md):

- **Format.** TOML, named `<something>.strumbook.toml`, read with the standard
  library's `tomllib`.
- **Tables.** Four tables:
  - `[book]`: title, type, edition, subtitle, notes;
  - `[sources.<name>]`: the collections;
  - `[songs]`: which songs;
  - `[build]`: settings.
- **Types.** A `type` says how the book is put together: `song-library` (A to Z, the
  default) or `set-list` (running order, with sets and spares). A type sets defaults
  and decides which `[songs]` keys apply.
- **Settings.** `[build]` keys have the same names as the command-line options. Settings
  come in three layers, each overriding the one before:
  1. the type's defaults;
  2. the file's `[build]`;
  3. options on the command line.
- **Sources.** A source is a `path` or a `git` repository, and songs refer to it by its
  name: `name:file name`. Git sources go through the system's own `git`, only over https
  or ssh, into the user's cache.
- **Credits.** Credits names every source and shows only its `link`, never a git
  address.
- **Unknown keys** give a warning, not an error. The file records no StrumBook version.

## Consequences

- **A public interface.** The format is now an interface people depend on, alongside the
  command line: their files live in their own repositories. Renaming or removing a key,
  a type or a value is a breaking change under semver, like a command-line option. We
  stay at 0.x until both settle.
- **New options** go in `[build]` under their command-line name and take the usual
  three layers. They need no new format.
- **New kinds of book** become new types with their own defaults. They don't add a
  separate format.
- **Older StrumBook.** A file written for a newer StrumBook still builds on an older one,
  with warnings for keys it doesn't know.
- **Git stays optional.** Only `git` sources need it, and StrumBook never passes options
  from a file to `git` (see the [threat model](../threat-model.md)).
- **The folder shortcut** (`strumbook build SONGS_DIR`) stays, as a song library of every
  song in one folder.

## Alternatives considered

- **Command-line options only:** nothing to learn, but every build means remembering
  them, and choosing songs from several collections doesn't fit on a command line.
- **YAML:** familiar, but Python has no YAML reader built in, so it would add a
  dependency, and its indentation rules trip people up.
- **JSON:** built in, but it has no comments and is fiddly to write by hand.
- **A file extension of our own, such as `.strbk`:** unmistakable, but editors and
  GitHub wouldn't know it's TOML, and opening it on a tablet or laptop would ask which
  app to use. `.strumbook.toml` is both distinct and recognisable.
- **Book definitions only inside collection repositories:** a book can draw on several
  collections, so it can't belong to one. A StrumBook file can still live in a
  collection's `books/` folder.
- **Python packages for git** (such as GitPython or dulwich): a new dependency, and
  private repositories would need their own sign-in handling. The system's `git` uses
  the sign-in the book maker already has.
