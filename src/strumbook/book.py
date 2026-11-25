"""The book model: songs in order with their chord diagrams, and the reference chords.

It knows nothing about pages; the renderer measures songs and asks `show_diagrams`.
"""

import unicodedata
from dataclasses import dataclass
from pathlib import Path

from strumbook.chordpro import Song, SongError, read_song
from strumbook.chords import shape

REFERENCE_ROOTS = ("C", "D", "E", "F", "G", "A", "Bb", "B")
MAX_DIAGRAMS = 8  # above this, a song that runs onto a second page loses its diagrams


class BuildError(Exception):
    """A problem the person building the book can fix; shown without a traceback."""


@dataclass(frozen=True)
class Diagram:
    """One fingering, labelled with every chord name in the song that uses it."""

    names: tuple[str, ...]
    frets: tuple[int, ...]

    @property
    def label(self) -> str:
        return " · ".join(self.names)


@dataclass(frozen=True)
class BookSong:
    song: Song
    id: str
    letter: str  # index group: A–Z, or "#" for titles that don't start with one
    diagrams: tuple[Diagram, ...]


@dataclass(frozen=True)
class Book:
    title: str
    songs: tuple[BookSong, ...]
    reference: tuple[tuple[str, tuple[Diagram, ...]], ...]  # root, its diagrams
    warnings: tuple[str, ...]


def group_diagrams(chord_names: list[str]) -> list[Diagram]:
    """One diagram per fingering, in order of first use; unknown chords left out."""
    by_frets: dict[tuple[int, ...], list[str]] = {}
    for name in chord_names:
        frets = shape(name)
        if frets is not None and name not in by_frets.setdefault(frets, []):
            by_frets[frets].append(name)
    return [Diagram(tuple(names), frets) for frets, names in by_frets.items()]


def show_diagrams(diagrams: int, pages_with: int, pages_without: int) -> bool:
    """Whether a song keeps its diagram column, given its page spans with and
    without it. The chord names in the lyrics always stay."""
    too_many = diagrams > MAX_DIAGRAMS and pages_with > 1
    fits_without = pages_with > 1 and pages_without == 1
    return not (too_many or fits_without)


def index_letter(title: str) -> str:
    first = unicodedata.normalize("NFKD", title.strip()[:1])[:1].upper()
    return first if "A" <= first <= "Z" else "#"


def read_book(folder: Path, title: str | None = None) -> Book:
    """Read every .cho file in `folder`. The title defaults to the folder's name."""
    if not folder.is_dir():
        raise BuildError(f"no such folder: {folder}")
    paths = sorted(folder.glob("*.cho"))
    if not paths:
        raise BuildError(f"no .cho files in {folder}")

    songs: list[tuple[Song, Path]] = []
    warnings: list[str] = []
    skipped: dict[str, list[str]] = {}
    for path in paths:
        try:
            song = read_song(path)
        except SongError as e:
            raise BuildError(str(e)) from None
        songs.append((song, path))
        for name in song.skipped:
            skipped.setdefault(name, []).append(song.title)
        warnings += [
            f"{song.title}: no diagram for {name}"
            for name in song.chords
            if shape(name) is None
        ]
    for name, titles in sorted(skipped.items()):
        where = titles[0] if len(titles) == 1 else f"{len(titles)} songs"
        warnings.append(f"skipped unknown directive {{{name}}} in {where}")

    songs.sort(key=lambda s: (index_letter(s[0].title), s[0].title.casefold(), s[1]))
    return Book(
        title=folder.resolve().name if title is None else title,
        songs=tuple(
            BookSong(
                song,
                f"s{i}",
                index_letter(song.title),
                tuple(group_diagrams(song.chords)),
            )
            for i, (song, _) in enumerate(songs)
        ),
        reference=tuple(
            (root, tuple(group_diagrams([root, root + "m", root + "7"])))
            for root in REFERENCE_ROOTS
        ),
        warnings=tuple(warnings),
    )
