"""Ukulele chord shapes (GCEA) from StrumBook's own table, chords.json.

The table lists frets per string as drawn, G C E A, for one spelling of each chord.
Sharps and flats are interchangeable (Gb finds F#), and slash chords use the base
chord's shape: on a re-entrant ukulele the bass note can't be honoured anyway.
"""

import json
import re
from functools import cache
from importlib.resources import files

_NAME = re.compile(r"([A-G][#b]?)([^/]*)(?:/[A-G][#b]?)?")
_ENHARMONIC = {"C#": "Db", "D#": "Eb", "Gb": "F#", "G#": "Ab", "A#": "Bb"}
_QUALITY = {"min": "m", "sus": "sus4"}


@cache
def _table() -> dict[str, tuple[int, ...]]:
    raw = json.loads(files("strumbook").joinpath("chords.json").read_text("utf-8"))
    return {name: tuple(int(f) for f in frets) for name, frets in raw.items()}


def shape(name: str) -> tuple[int, ...] | None:
    """Frets for a chord name, G C E A, or None if the table has no shape for it."""
    match = _NAME.fullmatch(name.strip())
    if not match:
        return None
    root, quality = match.groups()
    root = _ENHARMONIC.get(root, root)
    return _table().get(root + _QUALITY.get(quality, quality))
