"""The Typst page renderer, the only code that knows about Typst.

Three passes, all offline: outline the chord names to SVG, measure each song with and
without its diagrams to apply the diagram rules, then compile the book once.
"""

import json
import re
from pathlib import Path

import typst

from strumbook.book import (
    CHART_TYPES,
    Book,
    BookSong,
    BuildError,
    chord_chart,
    diagram_columns,
    group_diagrams,
    show_diagrams,
    sort_key,
)
from strumbook.chords import SLASH_DEFAULTS, TUNING_NAMES, chord_notes, simplify_slash

LAYOUT = Path(__file__).parent / "layout"
_OPTIONS = {
    "root": str(LAYOUT),
    "font_paths": [str(LAYOUT / "fonts")],
    "ignore_system_fonts": True,
}
_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_SVG_SIZE = re.compile(rb'width="([\d.]+)pt" height="([\d.]+)pt"')


def render(
    book: Book,
    output: Path,
    settings: dict,
    *,
    kind: str,
    edition: str,
    built: str,
) -> None:
    """Write `book` as a PDF of type `kind` ("song-library" or "set-list"), with the
    build `settings` (see bookfile.TYPES). `built` is the build date, for the About page."""
    tuning = settings["tuning"]
    slash = settings["slash-chords"] or SLASH_DEFAULTS[tuning]
    printed = simplify_slash if slash == "simplify" else str
    songs = [_song_data(s, tuning, printed) for s in book.songs]
    sections = _sections(book, songs, settings["set-breaks"])
    labels = {d["label"] for s in songs for d in s["diagrams"]}
    data = {
        "title": book.title,
        "subtitle": book.subtitle,
        "notes": _paragraphs(book.notes),
        "count": f"{len(songs)} song{'s' if len(songs) != 1 else ''}",
        "edition": edition,
        "built": built,
        "sources": [{"name": name, "link": link} for name, link in book.sources],
        "type": kind,
        "title_page": settings["title-page"],
        "chord_diagrams": settings["chords"],
        "index_page": settings["index"],
        "reference_page": settings["reference"],
        "notes_page": settings["reference-notes"],
        "credits": settings["credits"],
        "tuning": {"letters": tuning, "name": TUNING_NAMES[tuning]},
        "mid_word": settings["mid-word-chords"],
        "sections": sections,
        "songs": songs,
        # The index is always A to Z, even in a set list.
        "index": [
            {
                "id": s.id,
                "title": s.song.title,
                "artist": s.song.artist,
                "letter": s.letter,
            }
            for s in sorted(book.songs, key=lambda s: sort_key(s.song))
        ],
        "strip": _strip(book, settings, sections) if settings["navigation"] else [],
        # The chart's cells are diagrams only: its row and column name the chord.
        "chart": {
            "headings": [{"": "major", "aug": "+"}.get(t, t) for t in CHART_TYPES],
            "rows": [
                {"root": root.replace("b", "♭").replace("#", "♯"), "shapes": shapes}
                for root, shapes in chord_chart(tuning)
            ],
        },
        "chord_notes": chord_notes(),
    }
    try:
        data["chords"] = {
            "inline": _outline(
                sorted({printed(c) for s in book.songs for c in s.song.chords})
            ),
            "label": _outline(sorted(labels), style="label"),
        }
        spans = _measure(data)
        for song in songs:
            n = len(song["diagrams"])
            with_, without = spans[song["id"], "-with"], spans[song["id"], "-without"]
            song["show_diagrams"] = settings["chords"] and show_diagrams(
                n, with_, without
            )
        data["index_columns"] = 1 if spans["index", ""] == 1 else 2
        pdf = typst.compile(
            str(LAYOUT / "book.typ"),
            sys_inputs={"data": json.dumps(data)},
            pdf_tags=settings["pdf-tags"],
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


def _song_data(book_song: BookSong, tuning: str, printed) -> dict:
    """A song for the layout, with its chord names as printed (`printed` maps each
    name) and its diagrams in `tuning`."""
    song = book_song.song
    diagrams = group_diagrams([printed(c) for c in song.chords], tuning)
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
                chord = printed(seg.chord)
                segments.append({"chord": chord, "text": seg.text, "mid": mid})
            lines.append(segments)
        blocks.append({"chorus": block.chorus, "lines": lines})
    return {
        "id": book_song.id,
        "title": song.title,
        "artist": song.artist,
        "credit": song.credit_line,
        "key": book_song.letter,  # the strip cell this song lights up
        "blocks": blocks,
        "diagrams": [_diagram_data(d) for d in diagrams],
        "diagram_columns": diagram_columns(len(diagrams)),
    }


def _paragraphs(text: str) -> list[list[str]]:
    """Plain text as paragraphs of lines: blank lines separate paragraphs."""
    paragraphs = re.split(r"\n\s*\n", text.strip())
    return [[line.strip() for line in p.splitlines()] for p in paragraphs if p.strip()]


def _sections(book: Book, songs: list[dict], set_breaks: bool | None) -> list[dict]:
    """A set list's sets and spares, each with its songs. A named one gets a break
    page before its first song when set breaks are on: by default, when there's more
    than one section."""
    if set_breaks is None:
        set_breaks = len(book.sections) > 1
    result, start = [], 0
    for k, section in enumerate(book.sections):
        part = songs[start : start + section.count]
        start += section.count
        data = {
            "key": f"set-{k}",
            "name": section.name,
            "running_time": section.running_time,
            "notes": _paragraphs(section.notes),
            "songs": [{f: s[f] for f in ("id", "title", "artist")} for s in part],
            "break": set_breaks and bool(section.name),
        }
        result.append(data)
        for song in part:
            song["key"] = data["key"]
        if data["break"]:
            part[0]["break"] = data
    return result


def _strip(book: Book, settings: dict, sections: list[dict]) -> list[dict]:
    """The cells of the link strip, left to right: each has a `key` (what a page
    lights up), a `target` label and an `icon` or `text`. Empty when there's no strip:
    a set list needs named sections."""
    if sections:
        named = [s for s in sections if s["name"]]
        if not named:
            return []
        cells = [{"key": "running-order", "icon": "index", "target": "running-order"}]
        cells += [
            {
                "key": s["key"],
                "text": s["name"],
                "target": s["key"] if s["break"] else "song-" + s["songs"][0]["id"],
            }
            for s in named
        ]
    else:
        index = settings["index"]
        cells = [{"key": "index", "icon": "index", "target": "index"}] if index else []
        cells += _letters(book, "reference" if settings["reference"] else None)
    if settings["reference"]:
        cells.append({"key": "ref", "icon": "ref", "target": "reference"})
    return cells


def _letters(book: Book, end: str | None) -> list[dict]:
    """Link strip letters. An empty letter targets the next letter with songs, and
    after the last one `end` (or, with none, the last song)."""
    first = {s.letter: f"song-{s.id}" for s in reversed(book.songs)}
    letters, target = [], end or f"song-{book.songs[-1].id}"
    for letter in reversed(_LETTERS):
        target = first.get(letter, target)
        letters.append(
            {
                "key": letter,
                "text": letter,
                "dim": letter not in first,
                "target": target,
            }
        )
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
