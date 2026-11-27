"""Issue #25: the full chord chart and the notes in each chord."""

import json
import re
from importlib.resources import files
from pathlib import Path

import pytest
from book_helpers import (
    AWAY,
    built,
    page_text,
    run,
    warning_lines,
    write_book,
    write_songs,
)
from pdf_helpers import STRIP_CELLS, book_map, split_links, text_of
from pypdf import PdfReader

from strumbook.chords import shape

TUNINGS = [("GCEA", "Standard (GCEA)"), ("DGBE", "Baritone (DGBE)")]
TYPE_HEADINGS = ["major", "m", "7", "maj7", "m7", "sus2", "sus4", "+", "dim7"]
ROOT_LABELS = ["C", "D♭", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"]
NOTES = json.loads(files("strumbook").joinpath("chord-notes.json").read_text("utf-8"))

# A fretted dot is a circle path at its own offset (as in test_baritone.py).
# The scale is 1 in a song and smaller on the chart, so match any scale.
_DOT = re.compile(r"q ([\d.]+) 0 0 -\1 (\S+) (\S+) cm/c0 cs [\d. ]+ scn 0 3\.6850393 m")


def _dots(reader: PdfReader, pages: range) -> list[tuple[str, str]]:
    found = []
    for n in pages:
        stream = reader.pages[n].get_contents().get_data().decode("latin-1")
        found += [(x, y) for _, x, y in _DOT.findall(stream.replace("\n", " "))]
    return sorted(found)


def _book(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], *options: str, name: str = "b"
) -> PdfReader:
    songs = write_songs(
        tmp_path / "songs",
        {"a": "{title:Apple}\n[G]la [C]la\n", "b": "{title:Mango}\n[Am]la [D7]la\n"},
    )
    return built(songs, tmp_path / f"{name}.pdf", *options, capsys=capsys)


def _children(reader: PdfReader, title: str) -> list[str]:
    """Titles of the bookmarks nested directly under a top-level bookmark."""
    outline = list(reader.outline)
    for i, item in enumerate(outline):
        if not isinstance(item, list) and item.title == title:
            nxt = outline[i + 1] if i + 1 < len(outline) else None
            return (
                [c.title for c in nxt if not isinstance(c, list)]
                if isinstance(nxt, list)
                else []
            )
    raise AssertionError(f"no bookmark {title}")


def _child_page(reader: PdfReader, parent: str, child: str) -> int:
    outline = list(reader.outline)
    for i, item in enumerate(outline):
        if not isinstance(item, list) and item.title == parent:
            for c in outline[i + 1]:
                if not isinstance(c, list) and c.title == child:
                    return reader.get_destination_page_number(c)
    raise AssertionError(f"no bookmark {parent} > {child}")


# Chord names in songs.


@pytest.mark.parametrize("tuning", ["GCEA", "DGBE"])
def test_aug_has_two_spellings_and_the_new_types_have_shapes(tuning: str) -> None:
    assert shape("C+", tuning) is not None
    assert shape("C+", tuning) == shape("Caug", tuning)
    assert shape("Csus2", tuning) is not None
    assert shape("Cdim7", tuning) is not None
    assert shape("Csus", tuning) == shape("Csus4", tuning) is not None
    assert shape("C#dim", tuning) == shape("Dbdim7", tuning) is not None


@pytest.mark.parametrize("tuning", ["GCEA", "DGBE"])
def test_dim_uses_its_own_shape_else_the_dim7_shape(tuning: str) -> None:
    assert shape("Ddim", tuning) == shape("Ddim7", tuning) is not None
    assert shape("Bbdim", tuning) != shape("Bbdim7", tuning)
    assert shape("A#dim", tuning) == shape("Bbdim", tuning)
    own = {"GCEA": (3, 1, 0, 1), "DGBE": (2, 3, 2, 0)}[tuning]
    assert shape("Bbdim", tuning) == own


def test_a_song_with_the_new_chord_names_gets_diagrams_and_no_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    body = "{title:Tune}\n[C+]a [Caug]b [Csus2]c [Cdim7]d [Ddim]e [Bbdim]f [Csus]g\n"
    for tuning in ("GCEA", "DGBE"):
        songs = write_songs(tmp_path / tuning, {"a": body})
        code, err = run(
            songs, tmp_path / f"{tuning}.pdf", "--tuning", tuning, capsys=capsys
        )
        assert code == 0, err
        assert not [w for w in warning_lines(err) if "no diagram" in w], err
        reader = PdfReader(tmp_path / f"{tuning}.pdf")
        # C+ and Caug share a diagram, so six different shapes are drawn
        tune = book_map(reader).pages_of("Tune")
        assert len(_dots(reader, tune)) >= 6


# Where the Reference pages are.


def test_reference_is_two_pages_with_two_nested_bookmarks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = _book(tmp_path, capsys)
    pages = book_map(reader)
    assert pages.titles == ["Title", "Index", "Apple", "Mango", "Reference", "Credits"]
    ref = pages.pages_of("Reference")
    assert len(ref) == 2
    assert _children(reader, "Reference") == ["Chord shapes", "Notes in each chord"]
    assert _child_page(reader, "Reference", "Chord shapes") == ref[0]
    assert _child_page(reader, "Reference", "Notes in each chord") == ref[1]
    assert _children(reader, "Credits") == ["About this book"]  # unchanged


def test_icon_index_row_and_strip_on_both_pages_go_to_the_first_reference_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = _book(tmp_path, capsys)
    pages = book_map(reader)
    first = pages.first_page("Reference")
    for n in pages.pages_of("Reference"):
        strip, _ = split_links(reader, n)
        assert len(strip) == STRIP_CELLS, n
        assert strip[-1].target == first, n
    for n in range(1, pages.page_count):
        strip, _ = split_links(reader, n)
        assert strip[-1].target == first, n
    _, entries = split_links(reader, pages.first_page("Index"))
    entries.sort(key=lambda link: -link.rect[3])
    assert entries[-2].target == first
    assert entries[-1].target == pages.first_page("Credits")


# The chord shapes page.


@pytest.mark.parametrize(("tuning", "heading"), TUNINGS)
def test_the_chart_is_one_page_headed_with_the_tuning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], tuning: str, heading: str
) -> None:
    reader = _book(tmp_path, capsys, "--tuning", tuning)
    chart = book_map(reader).first_page("Reference")
    text = reader.pages[chart].extract_text()
    flat = " ".join(text.split())
    assert "REFERENCE" in flat
    assert "Chord shapes" in flat
    assert heading in flat
    lines = [ln.strip() for ln in text.splitlines()]
    other = TUNINGS[1][1] if tuning == "GCEA" else TUNINGS[0][1]
    assert other not in flat
    tokens = flat.split()
    for h in TYPE_HEADINGS:
        assert h in tokens, h
    for root in ROOT_LABELS:
        assert root in tokens, root
    assert "Notes in each chord" not in flat
    assert lines  # real text, not outlines


@pytest.mark.parametrize("tuning", ["GCEA", "DGBE"])
def test_the_chart_draws_all_108_diagrams_in_the_books_tuning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], tuning: str
) -> None:
    reader = _book(tmp_path, capsys, "--tuning", tuning)
    chart = book_map(reader).first_page("Reference")
    names = [
        m
        for m in json.loads(
            files("strumbook")
            .joinpath(f"chords-{tuning.lower()}.json")
            .read_text("utf-8")
        )
        if m != "Bbdim"
    ]
    assert len(names) == 108
    # one dot per fretted string, none for open strings
    expected = sum(1 for n in names for f in shape(n, tuning) or () if f > 0)
    assert len(_dots(reader, range(chart, chart + 1))) == expected


def test_the_chart_differs_by_tuning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a = _book(tmp_path, capsys, name="a")
    b = _book(tmp_path, capsys, "--tuning", "DGBE", name="b")
    first_a, first_b = (book_map(r).first_page("Reference") for r in (a, b))
    assert _dots(a, range(first_a, first_a + 1))  # not vacuous
    assert _dots(a, range(first_a, first_a + 1)) != _dots(
        b, range(first_b, first_b + 1)
    )


# The notes page.


@pytest.mark.parametrize(("tuning", "_"), TUNINGS)
def test_the_notes_page_matches_the_checked_table(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], tuning: str, _: str
) -> None:
    reader = _book(tmp_path, capsys, "--tuning", tuning)
    ref = book_map(reader).pages_of("Reference")
    text = page_text(reader, range(ref[1], ref[1] + 1))
    assert "REFERENCE" in text
    assert "Notes in each chord" in text
    for t in NOTES["types"]:
        assert t["name"] in text, t
        assert t["formula"] in text, t
    assert len(NOTES["rows"]) == 12
    for row in NOTES["rows"]:
        assert row["root"] in text, row["root"]
        assert len(row["cells"]) == 9
        for cell in row["cells"]:
            assert f"{cell['chord']} {cell['notes']}" in text, cell
    assert "Standard (GCEA)" not in text and "Baritone (DGBE)" not in text


def test_the_notes_page_is_the_same_in_both_tunings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a = _book(tmp_path, capsys, name="a")
    b = _book(tmp_path, capsys, "--tuning", "DGBE", name="b")
    na, nb = (book_map(r).pages_of("Reference")[1] for r in (a, b))
    assert page_text(a, range(na, na + 1)) == page_text(b, range(nb, nb + 1))
    assert not _dots(a, range(na, na + 1))  # words only, no diagrams


# Turning it off.


def test_reference_off_drops_both_pages_and_changes_nothing_else(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    on = _book(tmp_path, capsys, name="on")
    off = _book(tmp_path, capsys, "--reference", "off", name="off")
    pages_on, pages_off = book_map(on), book_map(off)
    assert pages_off.titles == ["Title", "Index", "Apple", "Mango", "Credits"]
    assert "Reference" not in _children_titles(off)
    assert pages_off.page_count == pages_on.page_count - 2
    for title in ["Title", "Apple", "Mango", "Credits"]:
        # page numbers move when the Reference pages go, so compare without digits
        def words(r: PdfReader, pages: range) -> str:
            return re.sub(r"\d+", "", page_text(r, pages))

        assert words(off, pages_off.pages_of(title)) == words(
            on, pages_on.pages_of(title)
        )
    text = text_of(off)
    assert "Notes in each chord" not in text


def _children_titles(reader: PdfReader) -> list[str]:
    return [i.title for i in reader.outline if not isinstance(i, list)]


def test_a_set_list_leaves_out_both_pages_unless_reference_is_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    body = f'[[songs.set]]\nname = "Set 1"\nsongs = ["{AWAY}"]\n'
    default = write_book(tmp_path, songs=body, book='type = "set-list"', name="d.toml")
    reader = built(default, tmp_path / "d.pdf", capsys=capsys)
    assert "Reference" not in _children_titles(reader)
    assert "Notes in each chord" not in text_of(reader)
    chosen = write_book(
        tmp_path,
        songs=body,
        book='type = "set-list"',
        build="reference = true",
        name="o.toml",
    )
    reader = built(chosen, tmp_path / "o.pdf", capsys=capsys)
    assert len(book_map(reader).pages_of("Reference")) == 2
