"""Issue #30: `--chords on|off` and `chords = true|false`, a book without chord
diagrams. Synthetic songs and the fixture carols only."""

import re
from pathlib import Path

import pytest
from book_helpers import (
    AWAY,
    BETHLEHEM,
    assert_clean_error,
    built,
    page_text,
    run,
    warning_lines,
    write_book,
    write_songs,
)
from pdf_helpers import book_map, text_of
from pypdf import PdfReader

from strumbook.cli import main

# A fretted dot is a circle path at its own offset (as in test_reference.py).
_DOT = re.compile(r"q ([\d.]+) 0 0 -\1 (\S+) (\S+) cm/c0 cs [\d. ]+ scn 0 3\.6850393 m")

SONGS = {
    "apple": "{title:Apple}\n[G]Fa la [C]la la\n[Am]Tra la [D7]la la\n",
    "mango": "{title:Mango}\n[F]Sing a [Zq9]song\n",  # Zq9 has no diagram
}
SETLIST_BODY = f'[[songs.set]]\nname = "Set 1"\nsongs = ["{AWAY}", "{BETHLEHEM}"]\n'


def _dots(reader: PdfReader, pages: range) -> int:
    found = 0
    for n in pages:
        stream = reader.pages[n].get_contents().get_data().decode("latin-1")
        found += len(_DOT.findall(stream.replace("\n", " ")))
    return found


def _song_pages(reader: PdfReader, titles: list[str]) -> list[int]:
    pages = book_map(reader)
    return [n for t in titles for n in pages.pages_of(t)]


def _has_column(reader: PdfReader, titles: list[str]) -> bool:
    return any(
        "GCEA" in reader.pages[n].extract_text() for n in _song_pages(reader, titles)
    )


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
    """Page text without digits and the tuning heading, to compare across layouts."""
    return " ".join(re.sub(r"\d+|GCEA", "", page_text(reader, pages)).split())


# The command line.


def test_a_song_library_has_diagrams_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(_library(tmp_path), tmp_path / "b.pdf", capsys=capsys)
    assert _has_column(reader, ["Apple", "Mango"])
    assert _dots(reader, range(len(reader.pages)))


def test_chords_off_leaves_no_diagrams_on_any_song_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        _library(tmp_path), tmp_path / "b.pdf", "--chords", "off", capsys=capsys
    )
    pages = _song_pages(reader, ["Apple", "Mango"])
    assert pages
    assert not _has_column(reader, ["Apple", "Mango"])
    assert not _dots(reader, pages_range(pages))
    assert len(book_map(reader).pages_of("Apple")) == 1


def pages_range(pages: list[int]) -> range:
    assert pages == list(range(pages[0], pages[-1] + 1))
    return range(pages[0], pages[-1] + 1)


def test_chords_off_keeps_the_songs_words_and_changes_nothing_else(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    on = built(_library(tmp_path), tmp_path / "on.pdf", capsys=capsys)
    off = built(
        _library(tmp_path), tmp_path / "off.pdf", "--chords", "off", capsys=capsys
    )
    on_map, off_map = book_map(on), book_map(off)
    assert off_map.titles == on_map.titles
    assert off_map.page_count == on_map.page_count
    for title in ["Apple", "Mango"]:
        words = _words(off, off_map.pages_of(title))
        assert words == _words(on, on_map.pages_of(title))
        assert "Fa la" in words or "Sing a" in words


def test_chords_on_on_the_command_line_is_the_same_as_the_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    default = built(_library(tmp_path), tmp_path / "d.pdf", capsys=capsys)
    chosen = built(
        _library(tmp_path), tmp_path / "o.pdf", "--chords", "on", capsys=capsys
    )
    assert text_of(chosen) == text_of(default)
    assert _dots(chosen, range(len(chosen.pages))) == _dots(
        default, range(len(default.pages))
    )


def test_a_bad_value_on_the_command_line_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "b.pdf"
    with pytest.raises(SystemExit) as exc:
        main(["build", str(_library(tmp_path)), "-o", str(out), "--chords", "maybe"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "invalid choice" in err
    assert "--chords" in err
    assert not out.exists()


# Warnings.


def test_a_missing_diagram_warns_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, err = run(_library(tmp_path), tmp_path / "b.pdf", capsys=capsys)
    assert code == 0, err
    assert [w for w in warning_lines(err) if "Mango: no diagram for Zq9" in w]


def test_chords_off_prints_no_diagram_warnings_and_does_not_count_them(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["build", str(_library(tmp_path)), "-o", str(tmp_path / "b.pdf")])
    assert code == 0
    assert "1 warning\n" in capsys.readouterr().out
    code = main(
        [
            "build",
            str(_library(tmp_path)),
            "-o",
            str(tmp_path / "c.pdf"),
            "--chords",
            "off",
        ]
    )
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert "no diagram" not in captured.err
    assert "0 warnings" in captured.out


def test_other_warnings_are_still_printed_with_chords_off(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = write_songs(
        tmp_path / "songs", {"a": "{title:Tune}\n{frobnicate: x}\n[Zq9]la\n"}
    )
    code = main(["build", str(songs), "-o", str(tmp_path / "b.pdf"), "--chords", "off"])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    warnings = warning_lines(captured.err)
    assert len(warnings) == 1
    assert "frobnicate" in warnings[0]
    assert "1 warning\n" in captured.out


# The StrumBook file.


def test_chords_false_in_build_turns_diagrams_off(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "b.pdf"
    code, err = run(_library(tmp_path, "chords = false"), out, capsys=capsys)
    assert code == 0, err
    reader = PdfReader(out)
    assert not _has_column(reader, ["Apple", "Mango"])
    assert not _dots(reader, pages_range(_song_pages(reader, ["Apple", "Mango"])))
    assert "no diagram" not in err


def test_chords_true_in_build_keeps_diagrams(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        _library(tmp_path, "chords = true"), tmp_path / "b.pdf", capsys=capsys
    )
    assert _has_column(reader, ["Apple", "Mango"])


def test_chords_on_on_the_command_line_overrides_false_in_build(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _library(tmp_path, "chords = false")
    reader = built(book, tmp_path / "b.pdf", "--chords", "on", capsys=capsys)
    assert _has_column(reader, ["Apple", "Mango"])


def test_chords_off_on_the_command_line_overrides_true_in_build(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _library(tmp_path, "chords = true")
    reader = built(book, tmp_path / "b.pdf", "--chords", "off", capsys=capsys)
    assert not _has_column(reader, ["Apple", "Mango"])


@pytest.mark.parametrize(
    "line", ['chords = "off"', 'chords = "on"', "chords = 1", 'chords = "false"']
)
def test_a_bad_value_in_build_is_a_one_line_error(
    line: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "b.pdf"
    code, err = run(_library(tmp_path, line), out, capsys=capsys)
    assert_clean_error(code, err, out, "[build] chords must be true or false")


# Set lists.


def test_a_set_list_has_no_diagrams_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(_setlist(tmp_path), tmp_path / "g.pdf", capsys=capsys)
    pages = _song_pages(reader, ["Away In A Manger", "O Little Town Of Bethlehem"])
    assert pages
    assert not _has_column(reader, ["Away In A Manger", "O Little Town Of Bethlehem"])
    assert not _dots(reader, pages_range(pages))


@pytest.mark.parametrize("where", ["build", "command line"])
def test_a_set_list_can_bring_diagrams_back(
    where: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if where == "build":
        book, flags = _setlist(tmp_path, "chords = true"), []
    else:
        book, flags = _setlist(tmp_path), ["--chords", "on"]
    reader = built(book, tmp_path / "g.pdf", *flags, capsys=capsys)
    assert _has_column(reader, ["Away In A Manger", "O Little Town Of Bethlehem"])


def test_a_set_list_with_diagrams_on_can_be_turned_off_again_on_the_command_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _setlist(tmp_path, "chords = true")
    reader = built(book, tmp_path / "g.pdf", "--chords", "off", capsys=capsys)
    assert not _has_column(reader, ["Away In A Manger", "O Little Town Of Bethlehem"])


def test_the_picked_list_type_given_on_the_command_line_has_no_diagrams(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, songs=f'pick = ["{AWAY}"]')
    reader = built(book, tmp_path / "g.pdf", "--type", "set-list", capsys=capsys)
    assert not _has_column(reader, ["Away In A Manger"])


# The Reference pages are separate.


@pytest.mark.parametrize("tuning", ["GCEA", "DGBE"])
def test_the_reference_chart_keeps_its_diagrams_with_chords_off(
    tuning: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    flags = ["--tuning", tuning]
    on = built(_library(tmp_path), tmp_path / "on.pdf", *flags, capsys=capsys)
    off = built(
        _library(tmp_path),
        tmp_path / "off.pdf",
        *flags,
        "--chords",
        "off",
        capsys=capsys,
    )
    on_ref, off_ref = (
        book_map(on).pages_of("Reference"),
        book_map(off).pages_of("Reference"),
    )
    assert len(off_ref) == len(on_ref) == 2
    assert _dots(off, off_ref) == _dots(on, on_ref) > 0
    assert page_text(off, off_ref) == page_text(on, on_ref)
    assert "Chord shapes" in page_text(off, off_ref)


def test_a_set_list_with_chords_off_and_reference_on_still_has_the_chart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _setlist(tmp_path, "reference = true")
    reader = built(book, tmp_path / "g.pdf", capsys=capsys)
    chart = book_map(reader).pages_of("Reference")
    assert len(chart) == 2
    assert _dots(reader, chart) > 0
    assert not _has_column(reader, ["Away In A Manger", "O Little Town Of Bethlehem"])


def test_reference_off_and_chords_on_are_independent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        _library(tmp_path), tmp_path / "b.pdf", "--reference", "off", capsys=capsys
    )
    assert "Reference" not in book_map(reader).titles
    assert _has_column(reader, ["Apple", "Mango"])
