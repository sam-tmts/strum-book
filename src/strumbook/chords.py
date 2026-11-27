"""Ukulele chord shapes from StrumBook's own tables, one per tuning: chords-gcea.json
and chords-dgbe.json.

Each table lists frets per string as drawn (G C E A, or D G B E), for one spelling of
each chord. Sharps and flats are interchangeable (Gb finds F#), and slash chords use
the base chord's shape.
"""

import json
import re
from functools import cache
from importlib.resources import files

# The values --tuning and [build] tuning accept, in any case, and the tuning each
# means. A new tuning needs a line in each of these and a chords-<tuning>.json.
TUNINGS = {"GCEA": "GCEA", "ukulele": "GCEA", "DGBE": "DGBE", "baritone": "DGBE"}
# Each tuning's name in a book: "Standard (GCEA)".
TUNING_NAMES = {"GCEA": "Standard", "DGBE": "Baritone"}
# Each tuning's default for slash chords: simplified only on a re-entrant ukulele,
# which has no real bass string.
SLASH_DEFAULTS = {"GCEA": "simplify", "DGBE": "as-written"}

_NAME = re.compile(r"([A-G][#b]?)([^/]*)(?:/([A-G][#b]?))?")
_ENHARMONIC = {"C#": "Db", "D#": "Eb", "Gb": "F#", "G#": "Ab", "A#": "Bb"}
_QUALITY = {"min": "m", "sus": "sus4", "+": "aug"}
_PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
# The notes of each chord type, in semitones above the root.
_NOTES = {
    "": {0, 4, 7}, "m": {0, 3, 7}, "7": {0, 4, 7, 10}, "maj7": {0, 4, 7, 11},
    "m7": {0, 3, 7, 10}, "sus2": {0, 2, 7}, "sus4": {0, 5, 7}, "aug": {0, 4, 8},
    "dim": {0, 3, 6}, "dim7": {0, 3, 6, 9},
}  # fmt: skip


def tuning(value: str) -> str | None:
    """The tuning ("GCEA" or "DGBE") a value names, in any case, or None."""
    return {k.casefold(): v for k, v in TUNINGS.items()}.get(value.casefold())


def tunings(values: object) -> list[str] | None:
    """The tuning each of a list of values names, in order, or None if it isn't a
    non-empty list of tuning names."""
    if not isinstance(values, list) or not values:
        return None
    found = [tuning(v.strip()) if isinstance(v, str) else None for v in values]
    return None if None in found else found


@cache
def _table(tuning: str) -> dict[str, tuple[int, ...]]:
    name = f"chords-{tuning.lower()}.json"
    raw = json.loads(files("strumbook").joinpath(name).read_text("utf-8"))
    return {name: tuple(int(f) for f in frets) for name, frets in raw.items()}


def shape(name: str, tuning: str = "GCEA") -> tuple[int, ...] | None:
    """Frets for a chord name in a tuning, or None if its table has no shape for it."""
    match = _NAME.fullmatch(name.strip())
    if not match:
        return None
    root, quality, _ = match.groups()
    root = _ENHARMONIC.get(root, root)
    quality = _QUALITY.get(quality, quality)
    table = _table(tuning)
    if quality == "dim" and root + "dim" not in table:
        quality = "dim7"  # as most ukulele books do
    return table.get(root + quality)


@cache
def chord_notes() -> dict:
    """The notes in each chord, for the Reference pages: fixed data, checked by a
    person, because spelling them is easy to get subtly wrong."""
    return json.loads(
        files("strumbook").joinpath("chord-notes.json").read_text("utf-8")
    )


def simplify_slash(name: str) -> str:
    """The chord without its bass note if that note is already in the chord, so
    "Am/C" is "Am" but "C/B" stays. Anything it can't read comes back unchanged."""
    match = _NAME.fullmatch(name.strip())
    if not match or match[3] is None:
        return name
    root, quality, bass = match.groups()
    notes = _NOTES.get(_QUALITY.get(quality, quality))
    if notes is None:
        return name
    if (_pitch(bass) - _pitch(root)) % 12 in notes:
        return name.strip()[: match.start(3) - 1]
    return name


def _pitch(note: str) -> int:
    """A note's pitch class: C is 0, C# and Db are 1, and so on."""
    return _PITCH[note[0]] + {"#": 1, "b": -1}.get(note[1:], 0)
