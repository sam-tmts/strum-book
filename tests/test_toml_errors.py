"""A StrumBook file that won't read gets a friendly error (issue #23): where it went
wrong (file and line), what was found, and how to write it in TOML."""

import re
from pathlib import Path

import pytest
from book_helpers import assert_clean_error, error_lines, run

NAME = "carols.strumbook.toml"


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / NAME
    path.write_text(text, encoding="utf-8")
    return path


def says_line(message: str, number: int) -> bool:
    return re.search(rf"\bline {number}\b", message, re.IGNORECASE) is not None


def says_column(message: str, number: int) -> bool:
    return re.search(rf"\bcolumn {number}\b", message, re.IGNORECASE) is not None


# (the file's text, its bad line, the line number, the TOML form that should be shown)
SLIPS = {
    "a ChordPro directive on the first line": (
        "{title: Carols}\n",
        "{title: Carols}",
        1,
        'title = "Carols"',
    ),
    "a directive with another key, lower down": (
        '[book]\ntitle = "Carols"\n{subtitle: Christmas 2026}\n',
        "{subtitle: Christmas 2026}",
        3,
        'subtitle = "Christmas 2026"',
    ),
    "a colon instead of an equals sign": (
        "[book]\ntitle: Carols\n",
        "title: Carols",
        2,
        'title = "Carols"',
    ),
    "a colon in another table, lower down": (
        '[book]\ntitle = "Carols"\n\n[songs]\ninclude: all\n',
        "include: all",
        5,
        'include = "all"',
    ),
    "text without quotes": (
        "[book]\ntitle = Carols\n",
        "title = Carols",
        2,
        'title = "Carols"',
    ),
    "unquoted text of several words, lower down": (
        '[book]\ntitle = "Carols"\nsubtitle = Christmas 2026\n',
        "subtitle = Christmas 2026",
        3,
        'subtitle = "Christmas 2026"',
    ),
}


@pytest.mark.parametrize(
    ("text", "found", "line", "toml_form"), SLIPS.values(), ids=SLIPS.keys()
)
def test_a_likely_slip_names_the_file_and_line_quotes_it_and_shows_the_toml_form(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    text: str,
    found: str,
    line: int,
    toml_form: str,
) -> None:
    out = tmp_path / "book.pdf"
    code, err = run(write(tmp_path, text), out, capsys=capsys)
    assert_clean_error(code, err, out, NAME, found, toml_form)
    assert says_line(error_lines(err)[0], line), err


def test_a_directive_slip_is_not_left_as_tomllibs_raw_message(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "book.pdf"
    code, err = run(write(tmp_path, "{title: Carols}\n"), out, capsys=capsys)
    assert code == 1
    assert "(at line" not in err


GENERAL = {
    "an unclosed table heading": ('[book\ntitle = "Carols"\n', 1, 6),
    "stray text after a value, lower down": (
        '[book]\ntitle = "Carols"\nsubtitle = "A" extra\n',
        3,
        16,
    ),
}


@pytest.mark.parametrize(
    ("text", "line", "column"), GENERAL.values(), ids=GENERAL.keys()
)
def test_any_other_toml_error_names_the_file_line_and_column_in_plain_words(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    text: str,
    line: int,
    column: int,
) -> None:
    out = tmp_path / "book.pdf"
    code, err = run(write(tmp_path, text), out, capsys=capsys)
    assert_clean_error(code, err, out, NAME)
    message = error_lines(err)[0]
    assert says_line(message, line), err
    assert says_column(message, column), err
    # plain words, not tomllib's "(at line N, column M)" tail
    assert "(at line" not in message, err
    assert "TOMLDecodeError" not in err


def test_any_other_toml_error_points_to_the_user_docs_with_a_link(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "book.pdf"
    code, err = run(write(tmp_path, '[book\ntitle = "Carols"\n'), out, capsys=capsys)
    assert_clean_error(code, err, out)
    assert "https://" in error_lines(err)[0]


def test_a_file_that_reads_fine_is_not_given_a_toml_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Valid TOML with a missing source is a different error, and not a TOML one.
    out = tmp_path / "book.pdf"
    text = '[book]\ntitle = "Carols"\n\n[songs]\ninclude = "all"\n'
    code, err = run(write(tmp_path, text), out, capsys=capsys)
    assert code == 1
    assert "TOML" not in err
    assert "(at line" not in err
