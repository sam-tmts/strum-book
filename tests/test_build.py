"""`strumbook build` on the public-domain fixture carols and synthetic songs."""

import shutil
from pathlib import Path

import pytest
from pdf_helpers import FIXTURES, STRIP_CELLS, book_map, split_links, text_of
from pypdf import PdfReader

from strumbook.cli import main

SONGS = [
    "Away In A Manger",
    "O Come, O Come, Emmanuel",
    "O Little Town Of Bethlehem",
]


def build(
    songs: Path, out: Path, *options: str, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str]:
    code = main(["build", str(songs), "-o", str(out), *options])
    return code, capsys.readouterr().err


def write_song(folder: Path, name: str, body: str) -> None:
    folder.mkdir(exist_ok=True)
    (folder / f"{name}.cho").write_text(body, encoding="utf-8")


@pytest.fixture
def carols(tmp_path: Path) -> Path:
    songs = tmp_path / "carols"
    songs.mkdir()
    for song in FIXTURES.glob("*.cho"):
        shutil.copy(song, songs / song.name)
    return songs


@pytest.fixture
def book(carols: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> PdfReader:
    out = tmp_path / "book.pdf"
    code, _ = build(carols, out, capsys=capsys)
    assert code == 0
    return PdfReader(out)


def test_build_writes_index_songs_in_title_order_and_reference(
    book: PdfReader,
) -> None:
    pages = book_map(book)
    assert pages.titles == ["Index", *SONGS, "Reference"]
    assert pages.pages[0] == 0
    assert pages.pages == sorted(pages.pages)
    assert pages.page_count >= 5
    assert pages.pages_of("Reference") == range(pages.page_count - 1, pages.page_count)


def test_title_defaults_to_folder_name(book: PdfReader) -> None:
    assert book.metadata is not None
    assert book.metadata.title == "carols"


def test_title_option_sets_pdf_title(
    carols: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "titled.pdf"
    code, _ = build(carols, out, "--title", "Winter Singalong", capsys=capsys)
    assert code == 0
    assert PdfReader(out).metadata.title == "Winter Singalong"


def test_lyrics_are_searchable_and_chord_names_are_not(book: PdfReader) -> None:
    text = text_of(book)
    assert "crib for a bed" in text
    for chord in ["Em/G", "A7", "Am/C", "D/F#", "B7", "Bm"]:
        assert chord not in text


def test_every_page_has_a_link_strip_of_28_equal_targets(book: PdfReader) -> None:
    pages = book_map(book)
    index = pages.first_page("Index")
    away = pages.first_page("Away In A Manger")
    emmanuel = pages.first_page("O Come, O Come, Emmanuel")
    reference = pages.first_page("Reference")
    # Index, A, B-N (next letter with songs is O), O, P-Z (after last letter), Reference
    expected = [index, away, *[emmanuel] * 13, emmanuel, *[reference] * 11, reference]
    assert len(expected) == STRIP_CELLS
    for number in range(pages.page_count):
        strip, _ = split_links(book, number)
        assert len(strip) == STRIP_CELLS, f"page {number}"
        assert len({link.size for link in strip}) == 1, f"page {number}"
        assert [link.target for link in strip] == expected, f"page {number}"


def test_index_entries_link_to_each_songs_first_page(book: PdfReader) -> None:
    pages = book_map(book)
    first_pages = {pages.first_page(title) for title in SONGS}
    index_pages = pages.pages_of("Index")
    targets = {
        link.target
        for number in index_pages
        for link in split_links(book, number)[1]
        if link.target != pages.first_page("Reference")
    }
    assert targets == first_pages


def test_song_titles_and_page_numbers_link_back_to_the_index(book: PdfReader) -> None:
    pages = book_map(book)
    index_pages = set(pages.pages_of("Index"))
    for title in SONGS:
        song_pages = pages.pages_of(title)
        for number in song_pages:
            _, others = split_links(book, number)
            assert others, f"{title} page {number} has no title/page-number link"
            assert {link.target for link in others} <= index_pages
        _, first = split_links(book, song_pages[0])
        assert len(first) >= 2, "title and page number are separate links"


def test_pdf_tags_are_on_by_default_and_can_be_turned_off(
    carols: Path, tmp_path: Path, book: PdfReader, capsys: pytest.CaptureFixture[str]
) -> None:
    assert "/StructTreeRoot" in book.trailer["/Root"]
    out = tmp_path / "untagged.pdf"
    code, _ = build(carols, out, "--pdf-tags", "off", capsys=capsys)
    assert code == 0
    assert "/StructTreeRoot" not in PdfReader(out).trailer["/Root"]


def test_mid_word_chords_above_keeps_words_whole(
    carols: Path, tmp_path: Path, book: PdfReader, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "above.pdf"
    code, _ = build(carols, out, "--mid-word-chords", "above", capsys=capsys)
    assert code == 0
    assert "Israel" in text_of(PdfReader(out))
    # Inline chords split the word for search: "Is[D]ra[Em]el".
    assert "Israel" not in text_of(book)


def test_unknown_chord_builds_without_diagram_and_warns_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = tmp_path / "songs"
    write_song(
        songs,
        "tune",
        "{title:Synthetic Tune}\n[G]La la [Xyz7b13]la [G]la\n[Xyz7b13]La la [G]la\n",
    )
    out = tmp_path / "book.pdf"
    code, err = build(songs, out, capsys=capsys)
    assert code == 0
    assert out.exists()
    warnings = [line for line in err.splitlines() if "Xyz7b13" in line]
    assert len(warnings) == 1
    assert warnings[0].startswith("warning: ")
    assert "Synthetic Tune" in warnings[0]
    assert "Traceback" not in err


def test_unknown_directive_is_skipped_with_a_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = tmp_path / "songs"
    write_song(songs, "tune", "{title:Synthetic Tune}\n{frobnicate: yes}\n[G]La la\n")
    out = tmp_path / "book.pdf"
    code, err = build(songs, out, capsys=capsys)
    assert code == 0
    assert any(
        line.startswith("warning: ") and "frobnicate" in line
        for line in err.splitlines()
    )
    assert book_map(PdfReader(out)).titles == ["Index", "Synthetic Tune", "Reference"]


def _only_readme(folder: Path) -> Path:
    folder.mkdir()
    (folder / "README.md").write_text("not a song\n")
    return folder


@pytest.mark.parametrize("kind", ["missing", "empty", "no-cho-files"])
def test_unusable_song_folder_is_a_clear_error(
    kind: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "songs"
    if kind == "empty":
        folder.mkdir()
    elif kind == "no-cho-files":
        _only_readme(folder)
    out = tmp_path / "book.pdf"
    code, err = build(folder, out, capsys=capsys)
    assert code != 0
    assert "error:" in err
    assert "Traceback" not in err
    assert not out.exists()
