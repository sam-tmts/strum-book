"""Read the ChordPro subset StrumBook uses: title, artist, credits, sort title, verses,
choruses and chords."""

import re
from dataclasses import dataclass
from pathlib import Path

# A name may contain spaces if a colon follows: "{Latin Text: J.F. Wade}". Without
# one, "{Repeat chorus}" is a note to players and stays in the lyrics.
_DIRECTIVE = re.compile(r"\{\s*([\w-]+(?:[ \t]+[\w-]+)*)\s*(?::\s*(.*?))?\s*\}")
_CHORD = re.compile(r"\[([^\]]*)\]")
_START_CHORUS = {"start_of_chorus", "soc"}
_END_CHORUS = {"end_of_chorus", "eoc"}
_VERSE = {"start_of_verse", "sov", "end_of_verse", "eov"}
# Credit directives, with their label in the credit line, in display order. The
# nonstandard ones come from real collections.
_CREDITS = {
    "words": "Words", "text": "Words", "lyricist": "Words", "latin text": "Words",
    "music": "Music", "composer": "Music",
    "translation": "Translation", "translated": "Translation",
}  # fmt: skip
_LABELS = ("Words", "Music", "Translation")
# Directives books don't show; skipped without a warning. Capo is ignored because
# chords are played as written. Some are oddities of real collections.
_IGNORED = {
    "arranger", "copyright", "album", "year", "key", "time", "tempo", "duration",
    "capo", "meta", "ccli", "column_break", "colb", "flow", "ci", "arrangment",
}  # fmt: skip


class SongError(Exception):
    """A song file that can't be read."""


@dataclass(frozen=True)
class Segment:
    """Lyric text, with the chord (or "") played at its start."""

    chord: str
    text: str


@dataclass(frozen=True)
class Block:
    chorus: bool
    lines: tuple[tuple[Segment, ...], ...]


@dataclass(frozen=True)
class Song:
    title: str
    artist: str
    blocks: tuple[Block, ...]
    skipped: frozenset[str]  # unknown directives, without braces
    sort_title: str  # the title, unless {sorttitle} gives another
    subtitle: str
    credits: tuple[tuple[str, str], ...]  # (label, names), in _LABELS order

    @property
    def credit_line(self) -> str:
        """The subtitle and credits as one line, e.g. "Words: … · Music: …"."""
        parts = [self.subtitle] if self.subtitle != self.artist else []
        parts += [f"{label}: {name}" for label, name in self.credits]
        return " · ".join(p for p in parts if p)

    @property
    def chords(self) -> list[str]:
        """Distinct chord names in order of first use."""
        names = (s.chord for b in self.blocks for line in b.lines for s in line)
        return list(dict.fromkeys(n for n in names if n))


def parse_line(line: str) -> tuple[Segment, ...]:
    parts = _CHORD.split(line)
    segments = [Segment("", parts[0])] if parts[0] else []
    for chord, text in zip(parts[1::2], parts[2::2], strict=True):
        segments.append(Segment(chord.strip(), text))
    return tuple(segments)


def read_song(path: Path) -> Song:
    try:
        text = path.read_text(encoding="utf-8-sig")  # some Windows editors add a BOM
    except UnicodeDecodeError:
        raise SongError(f"{path.name} isn't UTF-8 text") from None
    except OSError as e:
        raise SongError(f"can't read {path.name}: {e.strerror}") from None

    meta: dict[str, str] = {}
    credits: dict[str, list[str]] = {}
    skipped: set[str] = set()
    blocks: list[Block] = []
    lines: list[tuple[Segment, ...]] = []
    chorus = False

    def end_block() -> None:
        if lines:
            blocks.append(Block(chorus, tuple(lines)))
            lines.clear()

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.startswith("#"):
            continue
        match = _DIRECTIVE.fullmatch(line.strip())
        if match and " " in match.group(1) and match.group(2) is None:
            match = None  # "{Repeat chorus}"
        if match:
            name = " ".join(match.group(1).lower().split())
            value = (match.group(2) or "").strip()
            if name in _START_CHORUS | _END_CHORUS | _VERSE:
                end_block()
                chorus = name in _START_CHORUS
            elif name in ("title", "t", "artist", "sorttitle", "subtitle", "st"):
                name = {"t": "title", "st": "subtitle"}.get(name, name)
                meta.setdefault(name, value)
            elif name in _CREDITS:
                if value:
                    credits.setdefault(_CREDITS[name], []).append(value)
            elif name not in _IGNORED:
                skipped.add(name)
        elif line.strip():
            lines.append(parse_line(line))
        else:
            end_block()
    end_block()

    title = meta.get("title") or path.stem
    return Song(
        title=title,
        artist=meta.get("artist", ""),
        blocks=tuple(blocks),
        skipped=frozenset(skipped),
        sort_title=meta.get("sorttitle") or title,
        subtitle=meta.get("subtitle", ""),
        credits=tuple(
            (label, ", ".join(credits[label])) for label in _LABELS if label in credits
        ),
    )
