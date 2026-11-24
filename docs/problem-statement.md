# Problem statement and direction

What strumbook is for, the direction agreed so far, and what we've learnt. Later CRs
turn parts of it into acceptance criteria.

## The problem

Ukulele groups meet to play and sing along together, often in a pub, and many members
are beginners. They usually play from one big songbook: a single PDF of several hundred
pages, read on tablets held in portrait.

- **Finding a song is slow.** Someone calls out a song and everyone scrolls or searches
  until someone calls out a page number. Search in the PDF is unreliable and the
  contents page can't be tapped. Older or less tech-savvy members find this hardest.
- **Baritone players get the wrong chord diagrams.** A baritone ukulele uses different
  fingerings from soprano, concert and tenor for the same chord names.
- **Text is small and fixed.** Bigger text would help people with poorer eyesight, but
  songs already struggle to fit on one page.
- **Turning pages breaks the timing.** It means taking a hand off the instrument
  mid-song. Foot pedals cost money and add fuss, so few people use them.
- **Songs arrive in every format.** Members contribute PDFs and documents made in many
  programs, copied from other songbooks, old chord archives and websites, or written
  themselves. Each looks different, and none can be re-rendered.

PDF is still the common currency: one file that the group's organiser publishes and
everyone can open. So strumbook must produce good PDFs; other views are optional
extras.

## Direction

1. **Songs live as [ChordPro](https://www.chordpro.org/) files** in each group's own Git
   repository, with notes and attribution in each file on a best-effort basis.
2. **An importer drafts ChordPro** from existing PDFs or from pasted chords-over-lyrics
   text, and a person checks each song. Imports arrive as pull requests, so the check
   is the review.
3. **Books are built from one or more collections**, either every song or a set list in
   running order.
4. **First goal: two books from the same songs**, one for standard ukulele and one for
   baritone, differing only in their chord diagrams.
5. **Every book has** clean searchable text, a tappable contents page with an A-to-Z
   jump strip, song titles that link back to the contents, and an appendix of notes per
   song (source, original performers, rights).
6. **Each song records its rights** (unknown, public domain, original, copyrighted) on a
   best-effort basis, so a book meant for public posting can flag copyrighted songs.

**Parked for later:** a flexible app or web view, transposing at the reader's request,
half-page turns, text size the reader can change, and a group website for voting on
songs. (Rewriting capo songs on import, and trying a larger fixed text size in the
tablet style, are not parked.)

## Ground rules

- strumbook is open source and public.
- Each group usually keeps its own song collection in a private repository. Nothing
  from a private collection (song lists, survey data, notes about a group) goes into this
  repository.
- Tests and examples in this repository use only public-domain songs, kept as small
  fixtures here.

## Song collections

Every collection repository uses the same small layout, so strumbook can treat them
alike:

```text
README.md
songs/     one .cho file per song, flat (naming below)
docs/      notes about the collection
import/    material for converting existing songs; deleted once that's done
books/     book and set-list definitions (added when needed)
config/    the collection's house style for ChordPro, if it differs (added when needed)
```

Song files are named `title--artist.cho`: lower case, spaces as hyphens, punctuation
removed, and two hyphens between title and artist (for example
`the-holly-and-the-ivy--traditional.cho`). References to a song leave off `.cho`.

Each song has at least a title and artist, a sort title when the title starts with
"The", and the file it was imported from, if any. How a song records its rights is
still to be decided.

```text
{title: The Holly and the Ivy}
{sorttitle: Holly and the Ivy, The}
{artist: Traditional}
{meta: source Holly and the Ivy, The - Traditional.pdf}
```

## Books from several collections

Members of a big group often also play in a smaller band, with its own repertoire that
is too tricky for the group's beginners, and perhaps some songs of its own. A band
might keep two collections, covers and originals, and build its book from those plus
the group's collection.

- **A book definition names its collections and its songs.** It lives in the `books/`
  folder of whichever repository owns the book.
- **Songs are referred to by collection and file name**, such as
  `group:the-holly-and-the-ivy--traditional`, so the same file name in two collections
  never clashes.
- **The same song in two collections**, such as a band's arrangement of a group song, is
  two separate files. The book picks one; the band's version can record where it came
  from with `{meta: ...}`.
- **Access stays per repository.** Whoever builds a book needs read access to every
  collection it uses, and builds from local clones.
- **Rights matter more.** A band's originals are its own and could appear in a book
  posted publicly.

The first goal needs only one collection, but its design shouldn't rule this out.

## What we learnt from ChordPro

Tried with ChordPro 6.101 in November 2026.

- **Use it as the renderer.** It's open source, actively maintained and runs on Windows,
  macOS and Linux. It already builds a songbook PDF from a folder of `.cho` files, with
  a cover, tappable contents pages (by title, and by title with artist) and bookmarks.
  That leaves mainly a tablet style, a baritone instrument definition, the importer, a
  thin wrapper that builds the books, and whatever ChordPro can't do from the Direction
  list above (still to check).
- **Its defaults suit print, not tablets.** Every song starts on a right-hand page, so
  blank filler pages appear (18 of 61 pages in our test). Turn that off with
  `pdf.songbook.align-songs=false`.
- **Inline chords**, which groups expect, need the `inline` preset. Chord font and
  colour are configurable (for example bold red).
- **The look is plain, but all of it is configuration**: fonts, sizes and diagram
  placement. The tablet style is where experiments with text size happen.
- **There's a ukulele preset but no baritone one.** We'll write a small instrument
  definition. Baritone is tuned like the top four strings of a guitar, which may make it
  easy; still to check.
- **Songs written for guitar with a capo**: `--decapo` rewrites them in the key they
  sound in. It printed A♯ and D♯ where B♭ and E♭ were expected;
  `settings.transpose-sf-key=true` may fix that (still to confirm).
- **Possible importer help**: `--a2crd` converts chords-over-lyrics text to ChordPro.
- **Quirk**: give `--config` once for each preset; the comma-separated form didn't work.
- **Installing on macOS**: the app isn't signed. Record how to install it safely
  (official download, checksum if published) when ChordPro becomes a dependency.
- **A larger test set**: [pathawks/Christmas-Songs](https://github.com/pathawks/Christmas-Songs),
  28 carols in ChordPro, released under CC0. Use it for end-to-end checks, pinned to a
  commit. CC0 covers the files, not the songs, and a few carols may still be under
  copyright, so don't copy songs from it into this repository without checking. It shows
  real-world quirks: written for guitar, a capo in 9 songs, and some non-standard tags.

The command from the test. The last setting is the untested fix for sharps and flats
mentioned above:

```sh
chordpro --config=ukulele --config=inline --decapo --toc --title="Christmas Carols" \
  --define pdf.songbook.align-songs=false \
  --define settings.transpose-sf-key=true \
  -o carols-ukulele.pdf *.cho
```
