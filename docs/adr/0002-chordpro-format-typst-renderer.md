# ADR-0002: ChordPro as the song format; StrumBook renders pages, with Typst first

Status: Accepted. Date: 2026-11-25. Supersedes the problem statement's "use ChordPro
as the renderer".

## Context

The agreed page designs (a link strip on every page, chord diagrams down the side,
links back to index entries, a two-column index, dropping diagrams to avoid page turns)
are mostly open questions for ChordPro's own PDF layout. StrumBook should also be easy
to install for groups with limited technical skills, on Windows and macOS.

## Decision

- ChordPro stays the song format. StrumBook reads it and lays out the pages itself.
- Reading songs and drawing pages are separated by a book model, so the page renderer
  can be replaced.
- Typst is the default page renderer. Its Python package (`typst`) bundles the
  compiler, so installing StrumBook needs nothing else.

## Consequences

StrumBook owns more layout code, but every design idea can be built directly. ChordPro
the program is no longer a dependency. Chord diagram data comes from StrumBook's own
small chord table (`src/strumbook/chords.json`), and StrumBook's Typst code draws the
diagrams (spike #3: ChordPro's table lacks sharps and slash chords, and the Typst
packages' shapes are poor for ukulele). Chord names are drawn as outlines so they stay
out of the PDF's searchable text.

## Alternatives considered

- **ChordPro's own PDF output:** proven, but most of the designs would need its config
  stretched or the PDF patched afterwards.
- **HTML printed by a browser:** reuses the HTML mock-ups, but needs a bundled browser
  or the user's Chrome.
- **WeasyPrint:** no browser, but hard to install on Windows.
- **LaTeX:** a heavy install.
