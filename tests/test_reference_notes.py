"""Issue #35: `--reference-notes on|off` and `reference-notes = true|false`, a Reference
without the "Notes in each chord" page. Synthetic songs and the fixture carols only."""

import re
from pathlib import Path

import pytest
from book_helpers import (
    AWAY,
    assert_clean_error,
    built,
    page_text,
    run,
    write_book,
    write_songs,
)
from pdf_helpers import STRIP_CELLS, book_map, split_links, text_of
from pypdf import PdfReader

from strumbook.cli import main

SONGS = {
    "apple": "{title:Apple}\n[G]Fa la [C]la la\n",
    "mango": "{title:Mango}\n[Am]Tra la [D7]la la\n",
}
SETLIST_BODY = f'[[songs.set]]\nname = "Set 1"\nsongs = ["{AWAY}"]\n'
TITLES_WITH_NOTES = ["Title", "Index", "Apple", "Mango", "Reference", "Credits"]


def _library(tmp_path: Path, build: str = "") -> Path:
    return write_book(
        tmp_path,
        sources=f"[sources.s]\npath = '{write_songs(tmp_path / 'songs', SONGS)}'\n",
        build=build,
    )


def _setlist(tmp_path: Path, build: str = "") -> Path:
    return write_book(
        tmp_path, songs=SETLIST_BODY, book='type = "set-list"', build=build
    )


def _words(reader: PdfReader, pages: range) -> str:
    """Page text without digits: page numbers shift when a page goes."""
    return re.sub(r"\d+", "", page_text(reader, pages))


def _nested(reader: PdfReader, parent: str) -> list[str]:
    outline = list(reader.outline)
    for i, item in enumerate(outline):
        if not isinstance(item, list) and item.title == parent:
            nxt = outline[i + 1] if i + 1 < len(outline) else None
            return (
                [c.title for c in nxt if not isinstance(c, list)]
                if isinstance(nxt, list)
                else []
            )
    raise AssertionError(f"no bookmark {parent}")


def _top(reader: PdfReader) -> list[str]:
    return [i.title for i in reader.outline if not isinstance(i, list)]


def _has_notes_page(reader: PdfReader) -> bool:
    return "Notes in each chord" in text_of(reader)


def _only_the_chart(reader: PdfReader) -> None:
    ref = book_map(reader).pages_of("Reference")
    assert len(ref) == 1
    assert "Chord shapes" in page_text(reader, ref)
    assert not _has_notes_page(reader)
    assert _nested(reader, "Reference") == ["Chord shapes"]


# The command line.


def test_notes_off_leaves_a_one_page_reference_with_only_the_chart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        _library(tmp_path),
        tmp_path / "b.pdf",
        "--reference-notes",
        "off",
        capsys=capsys,
    )
    assert book_map(reader).titles == TITLES_WITH_NOTES
    _only_the_chart(reader)
    assert _nested(reader, "Credits") == ["About this book"]


def test_notes_off_is_exactly_one_page_shorter_and_changes_nothing_else(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    on = built(_library(tmp_path), tmp_path / "on.pdf", capsys=capsys)
    off = built(
        _library(tmp_path),
        tmp_path / "off.pdf",
        "--reference-notes",
        "off",
        capsys=capsys,
    )
    m_on, m_off = book_map(on), book_map(off)
    assert len(m_on.pages_of("Reference")) == 2  # not vacuous
    assert m_off.titles == m_on.titles
    assert m_off.page_count == m_on.page_count - 1
    for title in ["Title", "Index", "Apple", "Mango", "Credits"]:
        assert _words(off, m_off.pages_of(title)) == _words(on, m_on.pages_of(title))
    # the chart page is the very page that was first before
    chart_on, chart_off = m_on.first_page("Reference"), m_off.first_page("Reference")
    assert _words(off, range(chart_off, chart_off + 1)) == _words(
        on, range(chart_on, chart_on + 1)
    )


def test_notes_on_on_the_command_line_is_the_same_as_the_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    default = built(_library(tmp_path), tmp_path / "d.pdf", capsys=capsys)
    chosen = built(
        _library(tmp_path),
        tmp_path / "o.pdf",
        "--reference-notes",
        "on",
        capsys=capsys,
    )
    assert text_of(chosen) == text_of(default)
    assert len(chosen.pages) == len(default.pages)
    assert _nested(chosen, "Reference") == ["Chord shapes", "Notes in each chord"]


def test_the_icon_and_index_row_still_go_to_the_chart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        _library(tmp_path),
        tmp_path / "b.pdf",
        "--reference-notes",
        "off",
        capsys=capsys,
    )
    pages = book_map(reader)
    chart = pages.first_page("Reference")
    for n in range(1, pages.page_count):  # the title page has no strip
        strip, _ = split_links(reader, n)
        assert len(strip) == STRIP_CELLS, n
        assert strip[-1].target == chart, n
    _, entries = split_links(reader, pages.first_page("Index"))
    entries.sort(key=lambda link: -link.rect[3])
    assert entries[-2].target == chart
    assert entries[-1].target == pages.first_page("Credits")


@pytest.mark.parametrize("value", ["maybe", "true", "off "])
def test_a_bad_value_on_the_command_line_is_a_usage_error(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "b.pdf"
    with pytest.raises(SystemExit) as exc:
        main(
            [
                "build",
                str(_library(tmp_path)),
                "-o",
                str(out),
                "--reference-notes",
                value,
            ]
        )
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "--reference-notes" in err
    assert "invalid choice" in err
    assert not out.exists()


# The StrumBook file.


def test_false_in_build_leaves_out_the_notes_page_and_changes_nothing_else(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    on = built(_library(tmp_path), tmp_path / "on.pdf", capsys=capsys)
    off = built(
        _library(tmp_path, "reference-notes = false"),
        tmp_path / "off.pdf",
        capsys=capsys,
    )
    _only_the_chart(off)
    m_on, m_off = book_map(on), book_map(off)
    assert m_off.titles == m_on.titles
    assert m_off.page_count == m_on.page_count - 1
    for title in ["Title", "Index", "Apple", "Mango", "Credits"]:
        assert _words(off, m_off.pages_of(title)) == _words(on, m_on.pages_of(title))


def test_true_in_build_keeps_the_notes_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    default = built(_library(tmp_path), tmp_path / "d.pdf", capsys=capsys)
    chosen = built(
        _library(tmp_path, "reference-notes = true"),
        tmp_path / "o.pdf",
        capsys=capsys,
    )
    assert text_of(chosen) == text_of(default)
    assert _nested(chosen, "Reference") == ["Chord shapes", "Notes in each chord"]


@pytest.mark.parametrize(
    "line",
    [
        'reference-notes = "off"',
        'reference-notes = "on"',
        "reference-notes = 1",
        'reference-notes = "false"',
    ],
)
def test_a_bad_value_in_build_is_a_one_line_error_naming_the_option(
    line: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "b.pdf"
    code, err = run(_library(tmp_path, line), out, capsys=capsys)
    assert_clean_error(code, err, out, "[build] reference-notes must be true or false")


# The command line wins, in both directions.


def test_notes_off_on_the_command_line_overrides_true_in_build(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _library(tmp_path, "reference-notes = true")
    reader = built(book, tmp_path / "b.pdf", "--reference-notes", "off", capsys=capsys)
    _only_the_chart(reader)


def test_notes_on_on_the_command_line_overrides_false_in_build(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _library(tmp_path, "reference-notes = false")
    reader = built(book, tmp_path / "b.pdf", "--reference-notes", "on", capsys=capsys)
    assert len(book_map(reader).pages_of("Reference")) == 2
    assert _nested(reader, "Reference") == ["Chord shapes", "Notes in each chord"]


# Reference off wins.


@pytest.mark.parametrize("notes", ["on", "off"])
def test_reference_off_drops_everything_whatever_notes_says(
    notes: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "b.pdf"
    code, err = run(
        _library(tmp_path),
        out,
        "--reference",
        "off",
        "--reference-notes",
        notes,
        capsys=capsys,
    )
    assert code == 0, err
    assert "error" not in err
    reader = PdfReader(out)
    assert book_map(reader).titles == ["Title", "Index", "Apple", "Mango", "Credits"]
    assert "Reference" not in _top(reader)
    assert not _has_notes_page(reader)
    assert "Chord shapes" not in [t for t in _top(reader)]


def test_reference_false_in_build_drops_everything_with_notes_true(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _library(tmp_path, "reference = false\nreference-notes = true")
    reader = built(book, tmp_path / "b.pdf", capsys=capsys)
    assert "Reference" not in book_map(reader).titles
    assert not _has_notes_page(reader)


def test_reference_off_with_notes_off_is_the_same_book_as_reference_off(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    a = built(
        _library(tmp_path),
        tmp_path / "a.pdf",
        "--reference",
        "off",
        capsys=capsys,
    )
    b = built(
        _library(tmp_path),
        tmp_path / "b.pdf",
        "--reference",
        "off",
        "--reference-notes",
        "off",
        capsys=capsys,
    )
    assert text_of(a) == text_of(b)
    assert len(a.pages) == len(b.pages)


# Set lists.


def test_a_set_list_is_still_without_reference_by_default_whatever_notes_says(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for i, build in enumerate(
        ["", "reference-notes = true", "reference-notes = false"]
    ):
        reader = built(_setlist(tmp_path, build), tmp_path / f"{i}.pdf", capsys=capsys)
        assert "Reference" not in _top(reader), build
        assert not _has_notes_page(reader), build


def test_a_set_list_with_reference_on_and_notes_off_has_only_the_chart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _setlist(tmp_path, "reference = true\nreference-notes = false")
    reader = built(book, tmp_path / "g.pdf", capsys=capsys)
    _only_the_chart(reader)


def test_a_set_list_with_reference_on_has_both_pages_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        _setlist(tmp_path, "reference = true"), tmp_path / "g.pdf", capsys=capsys
    )
    assert len(book_map(reader).pages_of("Reference")) == 2
    assert _nested(reader, "Reference") == ["Chord shapes", "Notes in each chord"]


def test_a_set_list_can_turn_reference_and_notes_off_on_the_command_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _setlist(tmp_path)
    reader = built(
        book,
        tmp_path / "g.pdf",
        "--reference",
        "on",
        "--reference-notes",
        "off",
        capsys=capsys,
    )
    _only_the_chart(reader)
