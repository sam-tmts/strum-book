"""The Typst page renderer, the only code that knows about Typst.

Three passes, all offline: outline the chord names to SVG, measure each song with and
without its diagrams to apply the diagram rules, then compile the book once.
"""

import json
import re
from pathlib import Path

import typst

from strumbook.book import Book, BookSong, BuildError, diagram_columns, show_diagrams

LAYOUT = Path(__file__).parent / "layout"
_OPTIONS = {
    "root": str(LAYOUT),
    "font_paths": [str(LAYOUT / "fonts")],
    "ignore_system_fonts": True,
}
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_SVG_SIZE = re.compile(rb'width="([\d.]+)pt" height="([\d.]+)pt"')


def render(book: Book, output: Path, *, mid_word: str, pdf_tags: bool) -> None:
    """Write `book` as a PDF. `mid_word` is "inline" or "above"."""
    songs = [_song_data(s) for s in book.songs]
    reference = [
        {"root": root, "diagrams": [_diagram_data(d) for d in diagrams]}
        for root, diagrams in book.reference
    ]
    labels = {d["label"] for s in songs for d in s["diagrams"]}
    labels |= {d["label"] for g in reference for d in g["diagrams"]}
    data = {
        "title": book.title,
        "edition": f"{len(songs)} song{'s' if len(songs) != 1 else ''}",
        "tuning": "GCEA",
        "mid_word": mid_word,
        "songs": songs,
        "letters": _letters(book),
        "reference": reference,
    }
    try:
        data["chords"] = {
            "inline": _outline(sorted({c for s in book.songs for c in s.song.chords})),
            "label": _outline(sorted(labels), style="label"),
        }
        spans = _measure(data)
        for song in songs:
            n = len(song["diagrams"])
            with_, without = spans[song["id"], "-with"], spans[song["id"], "-without"]
            song["show_diagrams"] = show_diagrams(n, with_, without)
        data["index_columns"] = 1 if spans["index", ""] == 1 else 2
        pdf = typst.compile(
            str(LAYOUT / "book.typ"),
            sys_inputs={"data": json.dumps(data)},
            pdf_tags=pdf_tags,
            **_OPTIONS,
        )
    except typst.TypstError as e:
        raise BuildError(f"Typst couldn't lay out the book: {e.message}") from None
    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(pdf)
    except OSError as e:
        raise BuildError(f"can't write {output}: {e.strerror}") from None


def _diagram_data(diagram) -> dict:
    return {"label": diagram.label, "frets": diagram.frets}


def _song_data(book_song: BookSong) -> dict:
    song = book_song.song
    blocks = []
    for block in song.blocks:
        lines = []
        for line in block.lines:
            segments = []
            for i, seg in enumerate(line):
                before = line[i - 1].text if i else ""
                # A chord inside a word: "a[D]wakes".
                mid = (
                    bool(before) and not before[-1].isspace() and seg.text[:1].isalpha()
                )
                segments.append({"chord": seg.chord, "text": seg.text, "mid": mid})
            lines.append(segments)
        blocks.append({"chorus": block.chorus, "lines": lines})
    return {
        "id": book_song.id,
        "title": song.title,
        "artist": song.artist,
        "credit": song.credit_line,
        "letter": book_song.letter,
        "blocks": blocks,
        "diagrams": [_diagram_data(d) for d in book_song.diagrams],
        "diagram_columns": diagram_columns(len(book_song.diagrams)),
    }


def _letters(book: Book) -> list[dict]:
    """Link strip letters. An empty letter targets the next letter with songs, and
    after the last one the reference page ("ref")."""
    first = {s.letter: s.id for s in reversed(book.songs)}
    letters, target = [], "ref"
    for letter in reversed(_LETTERS):
        target = first.get(letter, target)
        letters.append({"letter": letter, "has": letter in first, "target": target})
    return letters[::-1]


def _outline(names: list[str], style: str = "inline") -> dict[str, dict]:
    """Chord names as outlined SVGs with their sizes in points."""
    if not names:
        return {}
    pages = typst.compile(
        str(LAYOUT / "chord-names.typ"),
        format="svg",
        sys_inputs={"names": json.dumps(names), "style": style},
        **_OPTIONS,
    )
    pages = pages if isinstance(pages, list) else [pages]
    result = {}
    for name, svg in zip(names, pages, strict=True):
        w, h = (float(x) for x in _SVG_SIZE.search(svg).groups())
        result[name] = {"svg": svg.decode("utf-8"), "w": w, "h": h}
    return result


def _measure(data: dict) -> dict[tuple[str, str], int]:
    """Page spans of the index and of each song with ("-with") and without
    ("-without") its diagrams."""
    marks = typst.query(
        str(LAYOUT / "book.typ"),
        "<pages>",
        field="value",
        sys_inputs={"data": json.dumps(data), "mode": "measure"},
        **_OPTIONS,
    )
    return {
        (m["id"], m["variant"]): m["last"] - m["first"] + 1 for m in json.loads(marks)
    }
