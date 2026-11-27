"""Issue #24: baritone books (--tuning GCEA | DGBE) and, as a stretch, simplified slash
chords. Built on the public-domain fixture carols and synthetic songs."""

import json
from importlib.resources import files
from pathlib import Path

import pytest
from book_helpers import (
    AWAY,
    EMMANUEL,
    assert_clean_error,
    built,
    run,
    write_book,
    write_songs,
)
from pdf_helpers import book_map, text_of
from pypdf import PdfReader

from strumbook import chords
from strumbook.book import group_diagrams
from strumbook.chords import shape
from strumbook.cli import main

EMMANUEL_T = "O Come, O Come, Emmanuel"
STANDARD_LINE = "Chord shapes: Standard ukulele (GCEA)"
BARITONE_LINE = "Chord shapes: Baritone ukulele (DGBE)"
BARITONE_VALUES = ["DGBE", "dgbe", "Dgbe", "baritone", "Baritone", "BARITONE"]
STANDARD_VALUES = ["GCEA", "gcea", "ukulele", "Ukulele", "UKULELE"]


# The chord lookup, per tuning.


@pytest.mark.parametrize(
    ("name", "frets"),
    [("G", (0, 0, 0, 3)), ("C", (2, 0, 1, 0)), ("D", (0, 2, 3, 2))]
    + [("Am", (2, 2, 1, 0)), ("Em", (2, 0, 0, 0))],
)
def test_baritone_shapes_are_frets_for_strings_d_g_b_e(
    name: str, frets: tuple[int, ...]
) -> None:
    assert shape(name, "DGBE") == frets


@pytest.mark.parametrize(
    ("name", "frets"),
    [("G", (0, 2, 3, 2)), ("C", (0, 0, 0, 3)), ("Am", (2, 0, 0, 0))],
)
def test_standard_shapes_are_unchanged_and_are_the_default(
    name: str, frets: tuple[int, ...]
) -> None:
    assert shape(name) == frets
    assert shape(name, "GCEA") == frets


def test_sharps_flats_and_slash_chords_work_in_the_baritone_table() -> None:
    assert shape("Gb", "DGBE") == shape("F#", "DGBE") is not None
    assert shape("A#", "DGBE") == shape("Bb", "DGBE") is not None
    assert shape("D/A", "DGBE") == shape("D", "DGBE")
    assert shape("Esus", "DGBE") == shape("Esus4", "DGBE") is not None
    assert shape("Xyz7b13", "DGBE") is None


def test_the_two_tunings_give_different_shapes_for_the_same_name() -> None:
    assert shape("G", "DGBE") != shape("G", "GCEA")


def _table(name: str) -> dict[str, str]:
    text = files("strumbook").joinpath(name).read_text("utf-8")
    return json.loads(text)


def test_there_is_one_packaged_table_per_tuning_and_no_old_chords_json() -> None:
    assert files("strumbook").joinpath("chords-gcea.json").is_file()
    assert files("strumbook").joinpath("chords-dgbe.json").is_file()
    assert not files("strumbook").joinpath("chords.json").is_file()


def test_the_baritone_table_has_every_chord_the_standard_table_has() -> None:
    gcea, dgbe = _table("chords-gcea.json"), _table("chords-dgbe.json")
    assert set(dgbe) == set(gcea)
    roots = ["C", "Db", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]
    types = ["", "m", "7", "maj7", "m7", "sus2", "sus4", "aug", "dim7"]
    assert set(gcea) == {r + t for r in roots for t in types} | {"Bbdim"}
    assert len(gcea) == 109


def test_every_chord_has_four_frets_in_both_tunings() -> None:
    for name in _table("chords-gcea.json"):
        for tuning in ("GCEA", "DGBE"):
            frets = shape(name, tuning)
            assert frets is not None, (name, tuning)
            assert len(frets) == 4
            assert all(isinstance(f, int) and f >= 0 for f in frets)


def test_diagrams_are_grouped_by_the_tunings_fingering() -> None:
    names = ["G", "Am", "G/B", "C"]
    standard = group_diagrams(names)
    assert group_diagrams(names, "GCEA") == standard
    baritone = group_diagrams(names, "DGBE")
    assert [d.names for d in baritone] == [d.names for d in standard]
    assert baritone[0].frets == (0, 0, 0, 3)
    assert standard[0].frets == shape("G")
    assert baritone[1].frets == (2, 2, 1, 0)


# The command line and the [build] table.


def _carols(tmp_path: Path) -> Path:
    return write_book(tmp_path)


def _song_text(reader: PdfReader, title: str) -> str:
    pages = book_map(reader).pages_of(title)
    return " ".join(reader.pages[n].extract_text() for n in pages)


def _assert_tuning(reader: PdfReader, letters: str, heading: str, line: str) -> None:
    pages = book_map(reader)
    title_page = reader.pages[0].extract_text()
    assert " ".join(line.split()) in " ".join(title_page.split())
    reference = " ".join(_song_text(reader, "Reference").split())
    assert heading in reference
    other = "GCEA" if letters == "DGBE" else "DGBE"
    for title in pages.titles:
        if title in {"Title", "Index", "Reference", "Credits"}:
            continue
        text = _song_text(reader, title)
        assert letters in text, title  # the diagram column's heading
        assert other not in text, title
    index = " ".join(_song_text(reader, "Index").split())
    assert f"Chord shapes {letters}" in index


def test_a_book_with_no_tuning_is_standard_throughout(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(_carols(tmp_path), tmp_path / "book.pdf", capsys=capsys)
    _assert_tuning(reader, "GCEA", "Standard (GCEA)", STANDARD_LINE)
    assert "Baritone" not in text_of(reader)
    assert "Standard tuning" not in text_of(reader)  # the heading's old wording


@pytest.mark.parametrize("value", BARITONE_VALUES)
def test_tuning_on_the_command_line_gives_a_baritone_book_in_any_case(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "book.pdf"
    reader = built(_carols(tmp_path), out, "--tuning", value, capsys=capsys)
    _assert_tuning(reader, "DGBE", "Baritone (DGBE)", BARITONE_LINE)
    assert "Standard (GCEA)" not in text_of(reader)


@pytest.mark.parametrize("value", STANDARD_VALUES)
def test_standard_values_give_a_standard_book(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        _carols(tmp_path), tmp_path / "book.pdf", "--tuning", value, capsys=capsys
    )
    _assert_tuning(reader, "GCEA", "Standard (GCEA)", STANDARD_LINE)


@pytest.mark.parametrize("value", ["baritone", "DGBE", "Baritone"])
def test_tuning_in_the_build_table_gives_a_baritone_book(
    value: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, build=f'tuning = "{value}"')
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    _assert_tuning(reader, "DGBE", "Baritone (DGBE)", BARITONE_LINE)


def test_the_command_line_overrides_the_build_tuning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, build='tuning = "baritone"')
    reader = built(book, tmp_path / "a.pdf", "--tuning", "ukulele", capsys=capsys)
    _assert_tuning(reader, "GCEA", "Standard (GCEA)", STANDARD_LINE)
    book = write_book(tmp_path, build='tuning = "GCEA"', name="b.strumbook.toml")
    reader = built(book, tmp_path / "b.pdf", "--tuning", "baritone", capsys=capsys)
    _assert_tuning(reader, "DGBE", "Baritone (DGBE)", BARITONE_LINE)


def test_the_chord_names_in_the_lyrics_do_not_change_with_the_tuning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Chord names are outlined, so the lyrics are all that is searchable: they stay
    # the same words in both books.
    book = _carols(tmp_path)
    standard = built(book, tmp_path / "a.pdf", capsys=capsys)
    baritone = built(book, tmp_path / "b.pdf", "--tuning", "DGBE", capsys=capsys)
    for title in ["Away In A Manger", EMMANUEL_T]:
        a = _song_text(standard, title).replace("GCEA", "")
        b = _song_text(baritone, title).replace("DGBE", "")
        assert a == b


def test_a_song_library_without_a_reference_page_still_names_the_tuning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, build='reference = false\ntuning = "baritone"')
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert BARITONE_LINE in " ".join(reader.pages[0].extract_text().split())


def test_a_set_list_title_page_names_the_tuning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'pick = ["{AWAY}", "{EMMANUEL}"]'
    for tuning, line in [("GCEA", STANDARD_LINE), ("baritone", BARITONE_LINE)]:
        book = write_book(
            tmp_path,
            songs=songs,
            book='type = "set-list"',
            build=f'tuning = "{tuning}"',
            name=f"{tuning}.strumbook.toml",
        )
        reader = built(book, tmp_path / f"{tuning}.pdf", capsys=capsys)
        assert line in " ".join(reader.pages[0].extract_text().split())


def test_a_set_list_with_no_tuning_names_standard_on_its_title_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, songs=f'pick = ["{AWAY}"]', book='type = "set-list"')
    reader = built(book, tmp_path / "gig.pdf", capsys=capsys)
    assert STANDARD_LINE in " ".join(reader.pages[0].extract_text().split())


def test_a_folder_of_songs_builds_a_baritone_book_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = write_songs(tmp_path / "songs", {"a": "{title:Tune}\n[G]la [C]la\n"})
    out = tmp_path / "book.pdf"
    code = main(["build", str(songs), "-o", str(out), "--tuning", "baritone"])
    assert code == 0, capsys.readouterr().err
    reader = PdfReader(out)
    assert BARITONE_LINE in " ".join(reader.pages[0].extract_text().split())
    assert "DGBE" in _song_text(reader, "Tune")


# Unknown values.


def test_an_unknown_tuning_on_the_command_line_is_a_usage_error_listing_the_values(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "book.pdf"
    with pytest.raises(SystemExit) as exc:
        main(["build", str(_carols(tmp_path)), "-o", str(out), "--tuning", "EADG"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "usage:" in err
    for value in ["GCEA", "ukulele", "DGBE", "baritone"]:
        assert value in err
    assert not out.exists()


@pytest.mark.parametrize("setting", ['tuning = "EADG"', "tuning = 4", "tuning = true"])
def test_an_unknown_tuning_in_the_build_table_is_an_error_listing_the_values(
    setting: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "book.pdf"
    code, err = run(write_book(tmp_path, build=setting), out, capsys=capsys)
    assert_clean_error(code, err, out, "[build] tuning")
    for value in ["GCEA", "ukulele", "DGBE", "baritone"]:
        assert value in err


# Stretch: slash chords.


@pytest.mark.parametrize(
    ("name", "printed"),
    [
        ("Am/C", "Am"),
        ("Am/E", "Am"),
        ("G/B", "G"),
        ("D/F#", "D"),
        ("D/A", "D"),
        ("Em/G", "Em"),
        ("G7/F", "G7"),
        ("Cmaj7/B", "Cmaj7"),
        ("Am7/G", "Am7"),
        ("Csus2/D", "Csus2"),
        ("Gsus/C", "Gsus"),
        ("Cdim7/A", "Cdim7"),
        ("Caug/G#", "Caug"),
        ("Ab/D#", "Ab"),  # D# is Eb: enharmonic spellings match
        ("A/Db", "A"),  # Db is C#
    ],
)
def test_the_bass_is_dropped_when_it_is_already_a_note_of_the_chord(
    name: str, printed: str
) -> None:
    assert chords.simplify_slash(name) == printed


@pytest.mark.parametrize(
    "name",
    ["C/B", "Am/G", "F/E", "Am/F#", "C/Db", "G/F#", "C", "Am7", "G"],
)
def test_the_bass_is_kept_when_it_is_not_a_note_of_the_chord(name: str) -> None:
    assert chords.simplify_slash(name) == name


@pytest.mark.parametrize("name", ["Xyz/C", "C/H", "N.C.", "Cfoo/G", "/C", "C/"])
def test_a_chord_it_cannot_read_comes_back_unchanged_without_an_error(
    name: str,
) -> None:
    assert chords.simplify_slash(name) == name


class SlashBuilder:
    def __init__(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        # Chord names are outlined shapes, so the setting shows only in the drawing
        # of the song's pages. Emmanuel has Am/C and Am/E.
        self.tmp_path, self.capsys, self.count = tmp_path, capsys, 0

    def __call__(self, *options: str, build: str = "") -> bytes:
        self.count += 1
        name = f"b{self.count}"
        book = write_book(self.tmp_path, build=build, name=f"{name}.strumbook.toml")
        reader = built(
            book, self.tmp_path / f"{name}.pdf", *options, capsys=self.capsys
        )
        pages = book_map(reader).pages_of(EMMANUEL_T)
        return b"".join(reader.pages[n].get_contents().get_data() for n in pages)


@pytest.fixture
def slash(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> SlashBuilder:
    return SlashBuilder(tmp_path, capsys)


def test_slash_chords_setting_changes_how_the_chords_are_drawn(
    slash: SlashBuilder,
) -> None:
    simplified = slash("--slash-chords", "simplify")
    written = slash("--slash-chords", "as-written")
    assert simplified != written


def test_slash_chords_default_to_simplify_for_standard_and_as_written_for_baritone(
    slash: SlashBuilder,
) -> None:
    simplified = slash("--slash-chords", "simplify")
    written = slash("--slash-chords", "as-written")
    assert slash() == simplified
    assert slash("--tuning", "GCEA") == simplified
    # The baritone book differs in its diagrams too, so compare like with like.
    baritone_written = slash("--tuning", "DGBE", "--slash-chords", "as-written")
    baritone_simplified = slash("--tuning", "DGBE", "--slash-chords", "simplify")
    assert baritone_written != baritone_simplified
    assert slash("--tuning", "DGBE") == baritone_written
    assert simplified != written


def test_the_slash_chords_build_setting_applies_and_the_command_line_overrides_it(
    slash: SlashBuilder,
) -> None:
    simplified = slash("--slash-chords", "simplify")
    written = slash("--slash-chords", "as-written")
    assert slash(build='slash-chords = "as-written"') == written
    assert slash(build='slash-chords = "simplify"') == simplified
    assert slash("--slash-chords", "simplify", build='slash-chords = "as-written"') == (
        simplified
    )
    assert slash("--slash-chords", "as-written", build='slash-chords = "simplify"') == (
        written
    )


def test_slash_chords_setting_in_the_file_beats_the_tunings_default(
    slash: SlashBuilder,
) -> None:
    standard_as_written = slash("--slash-chords", "as-written")
    assert slash(build='slash-chords = "as-written"') == standard_as_written
    baritone_simplified = slash("--tuning", "DGBE", "--slash-chords", "simplify")
    assert slash(build='tuning = "DGBE"\nslash-chords = "simplify"') == (
        baritone_simplified
    )


def test_a_bad_slash_chords_option_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(
            ["build", str(_carols(tmp_path)), "-o", "x.pdf", "--slash-chords", "maybe"]
        )
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "simplify" in err
    assert "as-written" in err


@pytest.mark.parametrize(
    "setting", ['slash-chords = "maybe"', "slash-chords = true", "slash-chords = 1"]
)
def test_a_bad_slash_chords_build_value_is_an_error_naming_the_key(
    setting: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "book.pdf"
    code, err = run(write_book(tmp_path, build=setting), out, capsys=capsys)
    assert_clean_error(code, err, out, "slash-chords")


def test_an_unknown_bass_note_builds_without_error_or_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = write_songs(tmp_path / "songs", {"a": "{title:Odd}\n[C/H]la [G/B]la\n"})
    for option in ["simplify", "as-written"]:
        out = tmp_path / f"{option}.pdf"
        code = main(["build", str(songs), "-o", str(out), "--slash-chords", option])
        err = capsys.readouterr().err
        assert code == 0, err
        assert "error" not in err
