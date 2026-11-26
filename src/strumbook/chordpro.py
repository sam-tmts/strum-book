"""Read the ChordPro subset StrumBook uses: title, artist, verses, choruses, chords."""

import re
from dataclasses import dataclass
from pathlib import Path

_DIRECTIVE = re.compile(r"\{\s*([\w-]+)\s*(?::\s*(.*?))?\s*\}")
_CHORD = re.compile(r"\[([^\]]*)\]")
_START_CHORUS = {"start_of_chorus", "soc"}
_END_CHORUS = {"end_of_chorus", "eoc"}
_VERSE = {"start_of_verse", "sov", "end_of_verse", "eov"}
# Standard ChordPro metadata that books don't show yet; skipped without a warning.
_IGNORED = {
    "subtitle", "st", "sorttitle", "composer", "lyricist", "arranger", "copyright",
    "album", "year", "key", "time", "tempo", "duration", "capo", "meta",
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
        if match := _DIRECTIVE.fullmatch(line.strip()):
            name, value = match.group(1).lower(), (match.group(2) or "").strip()
            if name in _START_CHORUS | _END_CHORUS | _VERSE:
                end_block()
                chorus = name in _START_CHORUS
            elif name in ("title", "t", "artist"):
                meta.setdefault("title" if name == "t" else name, value)
            elif name not in _IGNORED:
                skipped.add(name)
        elif line.strip():
            lines.append(parse_line(line))
        else:
            end_block()
    end_block()

    return Song(
        title=meta.get("title") or path.stem,
        artist=meta.get("artist", ""),
        blocks=tuple(blocks),
        skipped=frozenset(skipped),
    )
