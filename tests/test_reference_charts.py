"""Issue #34: `--reference-charts GCEA,DGBE` and `reference-charts = [...]`, one chord
shapes page in Reference per listed tuning. Synthetic songs only."""

import re
from pathlib import Path

import pytest
from book_helpers import (
    assert_clean_error,
    built,
    index_targets,
    page_text,
    run,
    warning_lines,
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
STANDARD = "Standard (GCEA)"
BARITONE = "Baritone (DGBE)"
_DOT = re.compile(r"q ([\d.]+) 0 0 -\1 (\S+) (\S+) cm/c0 cs [\d. ]+ scn 0 3\.6850393 m")
VALUES = ["GCEA", "ukulele", "DGBE", "baritone"]


def _library(tmp_path: Path, build: str = "") -> Path:
    return write_book(
        tmp_path,
        sources=f"[sources.s]\npath = '{write_songs(tmp_path / 'songs', SONGS)}'\n",
        build=build,
    )


def _dots(reader: PdfReader, page: int) -> list[tuple[str, str]]:
    stream = reader.pages[page].get_contents().get_data().decode("latin-1")
    return sorted((x, y) for _, x, y in _DOT.findall(stream.replace("\n", " ")))


def _flat(reader: PdfReader, page: int) -> str:
    return page_text(reader, range(page, page + 1))


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


def _nested_pages(reader: PdfReader, parent: str) -> list[int]:
    outline = list(reader.outline)
    for i, item in enumerate(outline):
        if not isinstance(item, list) and item.title == parent:
            return [
                reader.get_destination_page_number(c)
                for c in outline[i + 1]
                if not isinstance(c, list)
            ]
    raise AssertionError(f"no bookmark {parent}")


def _top(reader: PdfReader) -> list[str]:
    return [i.title for i in reader.outline if not isinstance(i, list)]


def _single(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], tuning: str
) -> tuple[PdfReader, int]:
    """The dots of the one chart in a book of that tuning, for comparison."""
    reader = built(
        _library(tmp_path),
        tmp_path / f"single-{tuning}.pdf",
        "--tuning",
        tuning,
        capsys=capsys,
    )
    return reader, book_map(reader).first_page("Reference")


def _both(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], *options: str
) -> PdfReader:
    return built(
        _library(tmp_path),
        tmp_path / "both.pdf",
        "--reference-charts",
        "GCEA,DGBE",
        *options,
        capsys=capsys,
    )


# Two charts, then the notes.


def test_two_charts_then_the_notes_page_each_with_its_own_heading_and_shapes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = _both(tmp_path, capsys)
    pages = book_map(reader)
    assert pages.titles == ["Title", "Index", "Apple", "Mango", "Reference", "Credits"]
    ref = pages.pages_of("Reference")
    assert len(ref) == 3
    first, second, notes = ref
    assert STANDARD in _flat(reader, first)
    assert BARITONE not in _flat(reader, first)
    assert BARITONE in _flat(reader, second)
    assert STANDARD not in _flat(reader, second)
    for n in (first, second):
        assert "Chord shapes" in _flat(reader, n)
        assert "Notes in each chord" not in _flat(reader, n)
    assert "Notes in each chord" in _flat(reader, notes)
    assert not _dots(reader, notes)
    # each chart is the same page a single-tuning book draws
    for n, tuning in ((first, "GCEA"), (second, "DGBE")):
        single, at = _single(tmp_path, capsys, tuning)
        assert _dots(reader, n)  # not vacuous
        assert _dots(reader, n) == _dots(single, at)
    assert _dots(reader, first) != _dots(reader, second)


def test_the_order_of_the_list_is_the_order_of_the_charts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        _library(tmp_path),
        tmp_path / "b.pdf",
        "--reference-charts",
        "DGBE,GCEA",
        capsys=capsys,
    )
    first, second, _ = book_map(reader).pages_of("Reference")
    assert BARITONE in _flat(reader, first)
    assert STANDARD in _flat(reader, second)
    assert _nested(reader, "Reference") == [
        "Chord shapes: Baritone (DGBE)",
        "Chord shapes: Standard (GCEA)",
        "Notes in each chord",
    ]


@pytest.mark.parametrize(
    "value", ["gcea,dgbe", "ukulele,baritone", "GCEA, DGBE", "Ukulele , BARITONE"]
)
def test_values_match_in_any_case_as_synonyms_with_spaces_around_commas(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        _library(tmp_path),
        tmp_path / "b.pdf",
        "--reference-charts",
        value,
        capsys=capsys,
    )
    first, second, _ = book_map(reader).pages_of("Reference")
    assert STANDARD in _flat(reader, first)
    assert BARITONE in _flat(reader, second)


def test_the_strumbook_file_takes_a_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _library(tmp_path, 'reference-charts = ["ukulele", "baritone"]')
    reader = built(book, tmp_path / "b.pdf", capsys=capsys)
    ref = book_map(reader).pages_of("Reference")
    assert len(ref) == 3
    assert STANDARD in _flat(reader, ref[0])
    assert BARITONE in _flat(reader, ref[1])
    assert "Notes in each chord" in _flat(reader, ref[2])


def test_a_single_listed_tuning_that_is_not_the_books_own_is_allowed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "b.pdf"
    code, err = run(
        _library(tmp_path), out, "--reference-charts", "DGBE", capsys=capsys
    )
    assert code == 0, err
    assert not warning_lines(err), err
    reader = PdfReader(out)
    ref = book_map(reader).pages_of("Reference")
    assert len(ref) == 2
    assert BARITONE in _flat(reader, ref[0])
    assert STANDARD not in _flat(reader, ref[0])
    assert _nested(reader, "Reference")[-1] == "Notes in each chord"


# The default is as before.


def test_with_no_setting_the_book_is_as_before_in_either_tuning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for tuning, heading in (("GCEA", STANDARD), ("DGBE", BARITONE)):
        plain = built(
            _library(tmp_path),
            tmp_path / f"p{tuning}.pdf",
            "--tuning",
            tuning,
            capsys=capsys,
        )
        same = built(
            _library(tmp_path),
            tmp_path / f"s{tuning}.pdf",
            "--tuning",
            tuning,
            "--reference-charts",
            tuning,
            capsys=capsys,
        )
        assert len(book_map(plain).pages_of("Reference")) == 2
        assert heading in _flat(plain, book_map(plain).first_page("Reference"))
        assert _nested(plain, "Reference") == ["Chord shapes", "Notes in each chord"]
        assert text_of(same) == text_of(plain)
        assert _nested(same, "Reference") == ["Chord shapes", "Notes in each chord"]
        assert len(same.pages) == len(plain.pages)


def test_the_books_own_tuning_alone_listed_is_the_default_book(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    default = built(_library(tmp_path), tmp_path / "d.pdf", capsys=capsys)
    listed = built(
        _library(tmp_path, 'reference-charts = ["GCEA"]'),
        tmp_path / "l.pdf",
        capsys=capsys,
    )
    assert text_of(listed) == text_of(default)
    assert _nested(listed, "Reference") == ["Chord shapes", "Notes in each chord"]


# Bookmarks, index and links.


def test_each_chart_and_the_notes_page_has_a_nested_bookmark(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = _both(tmp_path, capsys)
    ref = book_map(reader).pages_of("Reference")
    assert _nested(reader, "Reference") == [
        "Chord shapes: Standard (GCEA)",
        "Chord shapes: Baritone (DGBE)",
        "Notes in each chord",
    ]
    assert _nested_pages(reader, "Reference") == list(ref)
    assert book_map(reader).first_page("Reference") == ref[0]
    assert _nested(reader, "Credits") == ["About this book"]


def test_the_index_has_a_row_per_chart_each_going_to_its_own_chart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = _both(tmp_path, capsys)
    pages = book_map(reader)
    index = pages.first_page("Index")
    text = _flat(reader, index)
    assert text.index("Chord shapes GCEA") < text.index("Chord shapes DGBE")
    assert text.count("Chord shapes") == 2
    first, second, _ = pages.pages_of("Reference")
    targets = index_targets(reader, index)
    assert targets[-3:] == [first, second, pages.first_page("Credits")]


def test_reference_and_every_strip_icon_go_to_the_first_chart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = _both(tmp_path, capsys)
    pages = book_map(reader)
    first = pages.pages_of("Reference")[0]
    assert pages.first_page("Reference") == first
    for n in range(1, pages.page_count):  # the title page has no strip
        strip, _ = split_links(reader, n)
        assert len(strip) == STRIP_CELLS, n
        assert strip[-1].target == first, n


def test_song_diagrams_and_the_title_page_follow_tuning_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    both = _both(tmp_path, capsys, "--tuning", "DGBE")
    alone = built(
        _library(tmp_path), tmp_path / "a.pdf", "--tuning", "DGBE", capsys=capsys
    )
    pb, pa = book_map(both), book_map(alone)
    assert "Chord shapes: Baritone ukulele (DGBE)" in " ".join(
        both.pages[0].extract_text().split()
    )
    assert "GCEA" not in _flat(both, 0)
    for title in ["Title", "Apple", "Mango"]:
        a = [_flat(alone, n) for n in pa.pages_of(title)]
        b = [_flat(both, n) for n in pb.pages_of(title)]
        assert [re.sub(r"\d+", "", t) for t in a] == [re.sub(r"\d+", "", t) for t in b]
    for title in ["Apple", "Mango"]:
        text = page_text(both, pb.pages_of(title))
        assert "DGBE" in text and "GCEA" not in text
    # in a DGBE book the first listed chart is the standard one, after the song pages
    assert STANDARD in _flat(both, pb.first_page("Reference"))


# Notes and Reference off.


def test_notes_off_with_two_charts_leaves_exactly_the_two_charts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = _both(tmp_path, capsys, "--reference-notes", "off")
    ref = book_map(reader).pages_of("Reference")
    assert len(ref) == 2
    assert "Notes in each chord" not in text_of(reader)
    assert _nested(reader, "Reference") == [
        "Chord shapes: Standard (GCEA)",
        "Chord shapes: Baritone (DGBE)",
    ]
    assert STANDARD in _flat(reader, ref[0])
    assert BARITONE in _flat(reader, ref[1])


@pytest.mark.parametrize("notes", ["on", "off"])
def test_reference_off_drops_every_chart_and_the_notes_page(
    notes: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = _both(tmp_path, capsys, "--reference", "off", "--reference-notes", notes)
    assert book_map(reader).titles == ["Title", "Index", "Apple", "Mango", "Credits"]
    assert "Reference" not in _top(reader)
    text = text_of(reader)
    assert "Notes in each chord" not in text
    assert STANDARD not in text and BARITONE not in text
    assert "Chord shapes GCEA" not in text and "Chord shapes DGBE" not in text


def test_reference_false_in_the_file_drops_every_chart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _library(tmp_path, 'reference = false\nreference-charts = ["GCEA", "DGBE"]')
    reader = built(book, tmp_path / "b.pdf", capsys=capsys)
    assert "Reference" not in book_map(reader).titles
    assert BARITONE not in text_of(reader)


# Layering.


def test_the_command_line_overrides_the_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _library(tmp_path, 'reference-charts = ["GCEA", "DGBE"]')
    reader = built(
        book, tmp_path / "b.pdf", "--reference-charts", "DGBE", capsys=capsys
    )
    ref = book_map(reader).pages_of("Reference")
    assert len(ref) == 2
    assert BARITONE in _flat(reader, ref[0])
    assert STANDARD not in _flat(reader, ref[0])
    book = _library(tmp_path, 'reference-charts = ["DGBE"]')
    reader = built(
        book, tmp_path / "c.pdf", "--reference-charts", "GCEA,DGBE", capsys=capsys
    )
    assert len(book_map(reader).pages_of("Reference")) == 3


def test_a_set_list_with_reference_on_gets_every_chart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from book_helpers import AWAY

    body = f'[[songs.set]]\nname = "Set 1"\nsongs = ["{AWAY}"]\n'
    book = write_book(
        tmp_path,
        songs=body,
        book='type = "set-list"',
        build='reference = true\nreference-charts = ["GCEA", "DGBE"]',
    )
    reader = built(book, tmp_path / "g.pdf", capsys=capsys)
    assert len(book_map(reader).pages_of("Reference")) == 3
    assert _nested(reader, "Reference")[:2] == [
        "Chord shapes: Standard (GCEA)",
        "Chord shapes: Baritone (DGBE)",
    ]


# Repeats.


@pytest.mark.parametrize(
    "value", ["GCEA,DGBE,GCEA", "GCEA,gcea,DGBE", "ukulele,GCEA,DGBE"]
)
def test_a_repeated_tuning_gets_one_chart_at_its_first_place_and_a_warning(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "b.pdf"
    code = main(
        ["build", str(_library(tmp_path)), "-o", str(out), "--reference-charts", value]
    )
    captured = capsys.readouterr()
    assert code == 0, captured.err
    warnings = warning_lines(captured.err)
    assert len(warnings) == 1, captured.err
    assert "GCEA" in warnings[0]
    assert "2 warnings" not in captured.out
    assert "1 warning" in captured.out
    reader = PdfReader(out)
    ref = book_map(reader).pages_of("Reference")
    assert len(ref) == 3
    assert STANDARD in _flat(reader, ref[0])
    assert BARITONE in _flat(reader, ref[1])
    assert _nested(reader, "Reference")[:2] == [
        "Chord shapes: Standard (GCEA)",
        "Chord shapes: Baritone (DGBE)",
    ]


def test_a_repeat_counting_synonyms_leaves_a_single_chart_with_the_plain_bookmark(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "b.pdf"
    code, err = run(
        _library(tmp_path), out, "--reference-charts", "GCEA,ukulele", capsys=capsys
    )
    assert code == 0, err
    assert len(warning_lines(err)) == 1, err
    reader = PdfReader(out)
    assert len(book_map(reader).pages_of("Reference")) == 2
    assert _nested(reader, "Reference") == ["Chord shapes", "Notes in each chord"]


def test_a_repeat_in_the_file_warns_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = _library(tmp_path, 'reference-charts = ["baritone", "DGBE"]')
    out = tmp_path / "b.pdf"
    code, err = run(book, out, capsys=capsys)
    assert code == 0, err
    warnings = warning_lines(err)
    assert len(warnings) == 1, err
    assert "DGBE" in warnings[0]
    assert len(book_map(PdfReader(out)).pages_of("Reference")) == 2


def test_no_repeat_means_no_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, err = run(
        _library(tmp_path),
        tmp_path / "b.pdf",
        "--reference-charts",
        "GCEA,DGBE",
        capsys=capsys,
    )
    assert code == 0
    assert not warning_lines(err), err


# Bad values.


@pytest.mark.parametrize("value", ["EADG", "GCEA,EADG", "GCEA,,DGBE", ""])
def test_a_bad_list_on_the_command_line_is_a_usage_error_listing_the_values(
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
                "--reference-charts",
                value,
            ]
        )
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "usage:" in err
    assert "--reference-charts" in err
    for name in VALUES:
        assert name in err
    assert not out.exists()


@pytest.mark.parametrize(
    "setting",
    [
        'reference-charts = ["EADG"]',
        'reference-charts = ["GCEA", "EADG"]',
        'reference-charts = "GCEA"',
        "reference-charts = true",
        "reference-charts = 4",
        "reference-charts = []",
        "reference-charts = [4]",
        "reference-charts = [true]",
    ],
)
def test_a_bad_value_in_the_file_is_one_error_naming_the_key_and_listing_the_values(
    setting: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "b.pdf"
    code, err = run(_library(tmp_path, setting), out, capsys=capsys)
    assert_clean_error(code, err, out, "[build] reference-charts")
    for name in VALUES:
        assert name in err
