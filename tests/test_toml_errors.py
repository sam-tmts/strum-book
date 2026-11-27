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


# Errors at the very end of the file: tomllib says "(at end of document)" with no
# line or column, so the message must say where in plain words instead.
AT_THE_END = {
    "an unclosed list as the last thing": (
        '[book]\ntitle = "Carols"\n\n[songs]\npick = [\n  "carols:Silent Night"\n'
    ),
    "an unclosed multi-line string": '[book]\ntitle = "Carols"\nnotes = """\nHello\n',
    "an unclosed string on the last line, with no newline": ('[book]\ntitle = "Carols'),
}


@pytest.mark.parametrize("text", AT_THE_END.values(), ids=AT_THE_END.keys())
def test_an_error_at_the_end_of_the_file_says_so_in_plain_words(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], text: str
) -> None:
    out = tmp_path / "book.pdf"
    code, err = run(write(tmp_path, text), out, capsys=capsys)
    assert_clean_error(code, err, out, NAME, "https://")
    message = error_lines(err)[0]
    assert re.search(r"end of (the |this )?file", message, re.IGNORECASE), err
    assert "end of document" not in message, err
    assert "isn't valid TOML: " not in message, err


# An address with sign-in details is never echoed, even inside a slip's message.
@pytest.mark.parametrize(
    "line",
    [
        "git = https://user:SECRET@example.com/x.git",
        "git: https://user:SECRET@example.com/x.git",
    ],
)
def test_a_slip_never_echoes_sign_in_details(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], line: str
) -> None:
    out = tmp_path / "book.pdf"
    text = f'[book]\ntitle = "Carols"\n\n[sources.a]\n{line}\n'
    code, err = run(write(tmp_path, text), out, capsys=capsys)
    assert_clean_error(code, err, out, NAME)
    assert "SECRET" not in err
    assert says_line(error_lines(err)[0], 5), err


# A value that is already valid TOML keeps its form; on and off become true and false.
KEEPS_ITS_FORM = {
    "a quoted value after a colon": (
        '[book]\ntitle: "Carols"\n',
        'title = "Carols"',
        None,
    ),
    "false after a colon": (
        '[book]\ntitle = "Carols"\n\n[build]\ncredits: false\n',
        "credits = false",
        'credits = "false"',
    ),
    "off as a word": (
        '[book]\ntitle = "Carols"\n\n[build]\ncredits = off\n',
        "credits = false",
        'credits = "off"',
    ),
    "on as a word": (
        '[book]\ntitle = "Carols"\n\n[build]\ncredits = on\n',
        "credits = true",
        'credits = "on"',
    ),
    "off after a colon": (
        '[book]\ntitle = "Carols"\n\n[build]\ncredits: off\n',
        "credits = false",
        'credits = "off"',
    ),
}


@pytest.mark.parametrize(
    ("text", "shown", "not_shown"), KEEPS_ITS_FORM.values(), ids=KEEPS_ITS_FORM.keys()
)
def test_the_toml_form_keeps_valid_values_as_they_are(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    text: str,
    shown: str,
    not_shown: str | None,
) -> None:
    out = tmp_path / "book.pdf"
    code, err = run(write(tmp_path, text), out, capsys=capsys)
    assert_clean_error(code, err, out, NAME, shown)
    assert '\\"' not in err
    if not_shown:
        assert not_shown not in err


# A key written twice is a general TOML error, even when each line alone looks like a
# slip: no advice to rewrite the line, and no "on or off".
REPEATED_KEYS = {
    "a boolean written twice": (
        '[book]\ntitle = "Carols"\n\n[build]\ncredits = false\ncredits = false\n',
        6,
        16,
    ),
    "a date written twice": (
        '[book]\ntitle = "Carols"\nedition = 2026-12-01\nedition = 2026-12-01\n',
        4,
        21,
    ),
}


@pytest.mark.parametrize(
    ("text", "line", "column"), REPEATED_KEYS.values(), ids=REPEATED_KEYS.keys()
)
def test_a_key_written_twice_is_a_general_error_not_a_rewrite_suggestion(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    text: str,
    line: int,
    column: int,
) -> None:
    out = tmp_path / "book.pdf"
    code, err = run(write(tmp_path, text), out, capsys=capsys)
    assert_clean_error(code, err, out, NAME, "https://")
    message = error_lines(err)[0]
    assert says_line(message, line), err
    assert says_column(message, column), err
    assert "on or off" not in message, err
    assert "needs" not in message, err
    assert "(at line" not in message, err
