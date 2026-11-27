"""Issue #8: what the complete Christmas book needs, on synthetic songs."""

import re
from pathlib import Path

import pytest
from pdf_helpers import book_map, text_of
from pypdf import PdfReader

from strumbook.book import read_book
from strumbook.chordpro import read_song
from strumbook.chords import shape
from strumbook.cli import main


def make_songs(tmp_path: Path, **songs: str) -> Path:
    folder = tmp_path / "songs"
    folder.mkdir()
    for name, body in songs.items():
        (folder / f"{name}.cho").write_text(body, encoding="utf-8")
    return folder


def build(
    folder: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[PdfReader, str]:
    out = tmp_path / "book.pdf"
    code = main(["build", str(folder), "-o", str(out)])
    err = capsys.readouterr().err
    assert code == 0, err
    return PdfReader(out), err


def song_text(reader: PdfReader, title: str) -> str:
    pages = book_map(reader).pages_of(title)
    return " ".join(re.sub(r"\s+", " ", reader.pages[n].extract_text()) for n in pages)


@pytest.mark.parametrize(
    ("name", "frets"),
    [("Bm7", (2, 2, 2, 2)), ("Asus", (2, 2, 0, 0)), ("A#dim/C#", (3, 1, 0, 1))],
)
def test_extra_chord_shapes_exist(name: str, frets: tuple[int, ...]) -> None:
    assert shape(name) == frets


def test_songs_with_those_chords_build_without_a_diagram_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = make_songs(
        tmp_path, a="{title:Odd Chords}\n[Bm7]La [Asus]la [A#dim/C#]la\n"
    )
    _, err = build(folder, tmp_path, capsys)
    assert "no diagram" not in err


def test_choruses_get_a_label_and_verses_do_not(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = make_songs(
        tmp_path,
        short="{title:Short Form}\n{soc}\n[G]La la\n{eoc}\n\n[C]Verse words\n",
        long=("{title:Long Form}\n{start_of_chorus}\n[G]Sing sing\n{end_of_chorus}\n"),
        plain="{title:Plain Verses}\n[G]Just a verse\n\n[C]Another verse\n",
    )
    reader, _ = build(folder, tmp_path, capsys)
    assert song_text(reader, "Short Form").count("Chorus") == 1
    assert song_text(reader, "Long Form").count("Chorus") == 1
    assert "Chorus" not in song_text(reader, "Plain Verses")


def test_credit_line_under_the_title(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = make_songs(
        tmp_path,
        full=(
            "{title:Full Credits}\n{st:A Fine Tune}\n{Text:A. Writer}\n"
            "{Music:B. Composer}\n{Translation:C. Turner}\n[G]La la\n"
        ),
        alias="{title:Alias Credits}\n{words:D. Poet}\n{translated:E. Turner}\n[G]La\n",
        latin="{title:Latin Credit}\n{Latin Text:J. Q. Author}\n[G]La la\n",
        bare="{title:Bare Song}\n{subtitle:}\n[G]La la\n",
    )
    reader, _ = build(folder, tmp_path, capsys)
    assert (
        "A Fine Tune · Words: A. Writer · Music: B. Composer · Translation: C. Turner"
    ) in song_text(reader, "Full Credits")
    assert "Words: D. Poet · Translation: E. Turner" in song_text(
        reader, "Alias Credits"
    )
    assert "Words: J. Q. Author" in song_text(reader, "Latin Credit")
    bare = song_text(reader, "Bare Song")
    assert "Words:" not in bare
    assert "Music:" not in bare
    assert "·" not in bare


def test_subtitle_equal_to_artist_is_shown_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = make_songs(
        tmp_path,
        a="{title:Twice}\n{artist:Traditional Zed}\n{subtitle:Traditional Zed}\n[G]La\n",
    )
    reader, _ = build(folder, tmp_path, capsys)
    assert song_text(reader, "Twice").count("Traditional Zed") == 1


def test_latin_text_directive_is_not_sung_as_a_lyric(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "s.cho"
    path.write_text("{title:Hymn}\n{Latin Text:J.F. Wade}\n[G]La la\n", "utf-8")
    lyrics = [s.text for b in read_song(path).blocks for l in b.lines for s in l]
    assert not any("Wade" in t or "Latin" in t for t in lyrics)
    folder = make_songs(tmp_path, h=path.read_text("utf-8"))
    _, err = build(folder, tmp_path, capsys)
    assert "Latin" not in err  # a credit, not an unknown directive


def test_sorttitle_decides_order_and_index_letter(tmp_path: Path) -> None:
    folder = make_songs(
        tmp_path,
        a="{title:The Apple Song}\n{sorttitle:Apple Song, The}\n[G]La\n",
        b="{title:Banana}\n[G]La\n",
        u="{title:Umbrella}\n[G]La\n",
    )
    book = read_book(folder)
    assert [s.song.title for s in book.songs] == [
        "The Apple Song", "Banana", "Umbrella",
    ]  # fmt: skip
    assert [s.letter for s in book.songs] == ["A", "B", "U"]


def test_repeated_credits_are_joined(tmp_path: Path) -> None:
    path = tmp_path / "s.cho"
    path.write_text(
        "{title:Two Hands}\n{text:A. One}\n{Latin Text:B. Two}\n"
        "{composer:C. Three}\n{composer:D. Four}\n[G]La\n",
        "utf-8",
    )
    assert read_song(path).credit_line == (
        "Words: A. One, B. Two · Music: C. Three, D. Four"
    )


def test_a_braced_note_without_a_colon_stays_in_the_lyrics(tmp_path: Path) -> None:
    path = tmp_path / "s.cho"
    path.write_text("{title:Note}\n[G]La la\n{Repeat chorus}\n", "utf-8")
    song = read_song(path)
    lyrics = [s.text for b in song.blocks for line in b.lines for s in line]
    assert "{Repeat chorus}" in lyrics
    assert not song.skipped


def test_the_summary_counts_songs_and_warnings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    clean = make_songs(tmp_path, a="{title:Clean}\n[G]La\n")
    assert main(["build", str(clean), "-o", str(tmp_path / "a.pdf")]) == 0
    assert "1 song, 0 warnings" in capsys.readouterr().out
    (clean / "b.cho").write_text("{title:Odd}\n{frobnicate: x}\n[G]La\n", "utf-8")
    assert main(["build", str(clean), "-o", str(tmp_path / "b.pdf")]) == 0
    assert "2 songs, 1 warning\n" in capsys.readouterr().out


def test_known_directives_are_ignored_quietly_and_unknown_ones_warn_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    quiet = (
        "{key:G}\n{time:4/4}\n{ccli:123}\n{column_break}\n{flow:x}\n"
        "{capo:2}\n{ci:x}\n{arrangment:x}\n"
    )
    folder = make_songs(
        tmp_path,
        a="{title:One}\n" + quiet + "{frobnicate: x}\n[G]La\n",
        b="{title:Two}\n{frobnicate: y}\n[G]La\n",
    )
    _, err = build(folder, tmp_path, capsys)
    warnings = [ln for ln in err.splitlines() if ln.startswith("warning: ")]
    assert len(warnings) == 1
    assert "skipped unknown directive {frobnicate} in 2 songs" in warnings[0]


def test_capo_does_not_transpose_the_chords(tmp_path: Path) -> None:
    path = tmp_path / "s.cho"
    path.write_text("{title:Capo}\n{capo:2}\n[G]La [C]la\n", "utf-8")
    assert read_song(path).chords == ["G", "C"]


def test_lyrics_are_searchable_and_chords_are_not_in_the_feature_book(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = make_songs(
        tmp_path,
        a="{title:Odd Chords}\n{soc}\n[Bm7]Silver [Asus]bells [A#dim/C#]ring\n{eoc}\n",
    )
    reader, _ = build(folder, tmp_path, capsys)
    ref = book_map(reader).pages_of("Reference")  # its notes page names chords
    text = " ".join(
        re.sub(r"\s+", " ", p.extract_text())
        for n, p in enumerate(reader.pages)
        if n not in ref
    )
    assert "Silver bells ring" in text_of(reader)
    for chord in ["Bm7", "Asus", "A#dim", "C#"]:
        assert chord not in text
