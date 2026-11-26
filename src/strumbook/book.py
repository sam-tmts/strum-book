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
    letter: str  # index group: A–Z, or "#" for sort titles that don't start with one
    diagrams: tuple[Diagram, ...]


@dataclass(frozen=True)
class Book:
    title: str
    songs: tuple[BookSong, ...]  # in book order
    reference: tuple[tuple[str, tuple[Diagram, ...]], ...]  # root, its diagrams
    warnings: tuple[str, ...]
    a_to_z: bool = True  # False when the songs are in a listed running order
    subtitle: str = ""
    notes: str = ""  # plain text; paragraphs separated by blank lines
    sources: tuple[str, ...] = ()  # web addresses for Credits


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


def diagram_columns(diagrams: int) -> int:
    """One column of diagrams for up to MAX_DIAGRAMS, two above that."""
    return 0 if diagrams == 0 else 1 if diagrams <= MAX_DIAGRAMS else 2


def index_letter(title: str) -> str:
    first = unicodedata.normalize("NFKD", title.strip()[:1])[:1].upper()
    return first if "A" <= first <= "Z" else "#"


def song_files(folder: Path) -> list[Path]:
    """The .cho files in `folder`, by name. Hidden files are skipped, such as the
    "._Song.cho" files macOS leaves on USB sticks."""
    return sorted(p for p in folder.glob("*.cho") if not p.name.startswith("."))


def read_book(folder: Path, title: str | None = None) -> Book:
    """Read every .cho file in `folder`. The title defaults to the folder's name."""
    if not folder.is_dir():
        raise BuildError(f"no such folder: {folder}")
    paths = song_files(folder)
    if not paths:
        raise BuildError(f"no .cho files in {folder}")
    return make_book(folder.resolve().name if title is None else title, paths)


def make_book(
    title: str,
    paths: list[Path],
    *,
    a_to_z: bool = True,
    subtitle: str = "",
    notes: str = "",
    sources: tuple[str, ...] = (),
    warnings: tuple[str, ...] = (),
) -> Book:
    """A book of the songs in `paths`, sorted by title, or in the order given."""
    songs: list[tuple[Song, Path]] = []
    found: list[str] = list(warnings)
    skipped: dict[str, list[str]] = {}
    for path in paths:
        try:
            song = read_song(path)
        except SongError as e:
            raise BuildError(str(e)) from None
        songs.append((song, path))
        for name in song.skipped:
            skipped.setdefault(name, []).append(song.title)
        found += [
            f"{song.title}: no diagram for {name}"
            for name in song.chords
            if shape(name) is None
        ]
    for name, titles in sorted(skipped.items()):
        where = titles[0] if len(titles) == 1 else f"{len(titles)} songs"
        found.append(f"skipped unknown directive {{{name}}} in {where}")

    if a_to_z:
        songs.sort(key=lambda s: (*sort_key(s[0]), s[1]))
    return Book(
        title=title,
        songs=tuple(
            BookSong(
                song,
                f"s{i}",
                index_letter(song.sort_title),
                tuple(group_diagrams(song.chords)),
            )
            for i, (song, _) in enumerate(songs)
        ),
        reference=tuple(
            (root, tuple(group_diagrams([root, root + "m", root + "7"])))
            for root in REFERENCE_ROOTS
        ),
        warnings=tuple(found),
        a_to_z=a_to_z,
        subtitle=subtitle,
        notes=notes,
        sources=sources,
    )


def sort_key(song: Song) -> tuple[str, str]:
    """A to Z by sort title, ignoring case, with "#" first."""
    return index_letter(song.sort_title), song.sort_title.casefold()
