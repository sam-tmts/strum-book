"""Issue #9: a title page and a Credits section, on synthetic songs."""

import re
from datetime import date
from pathlib import Path

import pytest
from pdf_helpers import book_map, links_on, split_links, text_of
from pypdf import PdfReader

from strumbook.cli import main

# Book order follows {sorttitle}: Apple, Mango, then "The Zebra Song" under Z.
SONGS = {
    "z": (
        "{title:The Zebra Song}\n{sorttitle:Zebra Song, The}\n"
        "{words:Zed Writer}\n{music:Zoe Composer}\n[G]La la\n"
    ),
    "a": "{title:Apple Tree}\n{subtitle:An Orchard Tune}\n{words:Ann Poet}\n[G]La\n",
    "m": "{title:Mango}\n[G]La la\n",  # no credits at all
}
ORDER = ["Apple Tree", "Mango", "The Zebra Song"]
CREDITED = ["Apple Tree", "The Zebra Song"]
TOOLS = {
    "https://github.com/sam-tmts/strumbook",
    "https://typst.app",
    "https://www.brailleinstitute.org/freefont/",
}


def build(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    *options: str,
    name: str = "book.pdf",
) -> PdfReader:
    folder = tmp_path / "songs"
    if not folder.exists():
        folder.mkdir()
        for stem, body in SONGS.items():
            (folder / f"{stem}.cho").write_text(body, encoding="utf-8")
    out = tmp_path / name
    args = ["--title", "Winter Singalong", "--edition", "Advent 2026", *options]
    code = main(["build", str(folder), "-o", str(out), *args])
    assert code == 0, capsys.readouterr().err
    return PdfReader(out)


def uris(reader: PdfReader, pages: range) -> set[str]:
    found = set()
    for n in pages:
        for ref in reader.pages[n].get("/Annots", []):
            action = ref.get_object().get("/A")
            if action is not None and "/URI" in action.get_object():
                found.add(str(action.get_object()["/URI"]))
    return found


def page_text(reader: PdfReader, pages: range) -> str:
    return re.sub(r"\s+", " ", " ".join(reader.pages[n].extract_text() for n in pages))


def test_book_order_and_bookmarks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = build(tmp_path, capsys)
    pages = book_map(reader)
    assert pages.titles == ["Title", "Index", *ORDER, "Reference", "Credits"]
    assert pages.pages[0] == 0
    assert pages.pages == sorted(pages.pages)


def test_title_page_shows_title_edition_and_made_with_and_no_link_strip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = build(tmp_path, capsys)
    pages = book_map(reader)
    assert len(pages.pages_of("Title")) == 1
    text = page_text(reader, pages.pages_of("Title"))
    assert "Winter Singalong" in text
    assert "Advent 2026" in text
    assert "Made with StrumBook" in text
    assert links_on(reader, 0) == []  # no strip, no index links
    strip, _ = split_links(reader, pages.first_page("Index"))
    assert len(strip) == 28  # other pages keep theirs


def test_credits_lists_only_credited_songs_in_book_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = build(tmp_path, capsys)
    text = page_text(reader, book_map(reader).pages_of("Credits"))
    assert "Mango" not in text
    assert all(title in text for title in CREDITED)
    assert text.index("Apple Tree") < text.index("The Zebra Song")
    assert "An Orchard Tune" in text
    assert "Words: Ann Poet" in text
    assert "Words: Zed Writer" in text
    assert "Music: Zoe Composer" in text


def test_credits_entries_and_credit_lines_link_to_each_other(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = build(tmp_path, capsys)
    pages = book_map(reader)
    credits = pages.pages_of("Credits")
    entries = [
        t for n in credits for t in (x.target for x in split_links(reader, n)[1])
    ]
    firsts = [pages.first_page(title) for title in CREDITED]
    assert [t for t in entries if t in firsts] == firsts  # one entry per song, in order
    assert pages.first_page("Mango") not in entries
    for title in CREDITED:
        _, others = split_links(reader, pages.first_page(title))
        assert {link.target for link in others} & set(credits), title
    _, mango = split_links(reader, pages.first_page("Mango"))
    assert not {link.target for link in mango} & set(credits)


def test_about_page_says_how_the_book_was_made_with_links(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plain = build(tmp_path, capsys)
    credits = book_map(plain).pages_of("Credits")
    assert uris(plain, credits) == TOOLS
    about = page_text(plain, range(credits[-1], credits[-1] + 1))  # its own page
    assert "ABOUT THIS BOOK How it was made" in about
    assert "Words and music" not in about
    today = date.today()  # this can flake only if the build runs over midnight
    assert f"StrumBook built this book on {today.day} {today:%B %Y}" in about
    assert "Typst laid out the pages" in about
    assert "Atkinson Hyperlegible set the words" in about
    for address in ["github.com/sam-tmts/strumbook", "brailleinstitute.org/freefont"]:
        assert address in about
    assert "https://" not in about
    assert "freefont/" not in about
    assert "Songs came from" not in about  # a folder build has no source line
    assert "No public link" not in about


def test_credits_has_an_index_row_next_to_chord_shapes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = build(tmp_path, capsys)
    pages = book_map(reader)
    _, entries = split_links(reader, pages.first_page("Index"))
    entries.sort(key=lambda link: -link.rect[3])  # top to bottom
    targets = [link.target for link in entries]
    assert targets[-1] == pages.first_page("Credits")
    assert targets[-2] == pages.first_page("Reference")
    assert "Credits" in page_text(reader, pages.pages_of("Index"))
    for n in range(pages.page_count):
        strip, _ = split_links(reader, n)
        if n != 0:  # the strip is unchanged: still 28 cells, ending at Reference
            assert len(strip) == 28
            assert strip[-1].target == pages.first_page("Reference")


def test_title_page_off_removes_only_the_title_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = build(tmp_path, capsys, "--title-page", "off")
    pages = book_map(reader)
    assert pages.titles == ["Index", *ORDER, "Reference", "Credits"]
    assert "Made with StrumBook" not in page_text(reader, range(1))
    _, entries = split_links(reader, 0)
    assert len(entries) == len(ORDER) + 2  # songs, Reference, Credits


def test_credits_off_removes_only_the_credits(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    on = build(tmp_path, capsys)
    off = build(tmp_path, capsys, "--credits", "off", name="off.pdf")
    pages = book_map(off)
    assert pages.titles == ["Title", "Index", *ORDER, "Reference"]
    assert "Credits" not in page_text(off, pages.pages_of("Index"))
    _, entries = split_links(off, pages.first_page("Index"))
    assert len(entries) == len(ORDER) + 1  # songs and Reference
    assert not uris(off, range(len(off.pages)))
    assert len(off.pages) == len(on.pages) - len(book_map(on).pages_of("Credits"))
    for title in ORDER:  # song pages hold the same words, credit lines included
        assert page_text(off, pages.pages_of(title)) == page_text(
            on, book_map(on).pages_of(title)
        )


def test_both_off_leaves_just_index_songs_and_reference(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = build(tmp_path, capsys, "--title-page", "off", "--credits", "off")
    assert book_map(reader).titles == ["Index", *ORDER, "Reference"]
    text = text_of(reader)
    assert "Made with" not in text
    assert "How it was made" not in text


@pytest.mark.parametrize("option", ["--title-page", "--credits"])
def test_bad_on_off_values_are_usage_errors(
    option: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["build", "songs", "-o", "book.pdf", option, "maybe"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "usage:" in err
    assert "invalid choice" in err  # not merely "unrecognized arguments"


def test_edition_defaults_to_todays_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "songs"
    folder.mkdir()
    (folder / "a.cho").write_text("{title:Dated}\n[G]La\n", encoding="utf-8")
    out = tmp_path / "book.pdf"
    assert main(["build", str(folder), "-o", str(out)]) == 0, capsys.readouterr().err
    today = date.today()  # this can flake only if the build runs over midnight
    assert f"{today.day} {today:%B %Y}" in page_text(PdfReader(out), range(1))


def test_credits_without_credited_songs_is_just_the_about_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "plain"
    folder.mkdir()
    (folder / "m.cho").write_text(SONGS["m"], encoding="utf-8")
    out = tmp_path / "book.pdf"
    assert main(["build", str(folder), "-o", str(out)]) == 0, capsys.readouterr().err
    reader = PdfReader(out)
    credits = book_map(reader).pages_of("Credits")
    assert len(credits) == 1
    text = page_text(reader, credits)
    assert "How it was made" in text
    assert "Words and music" not in text


@pytest.mark.parametrize("value", ["https://example.org/our-songs", "", "x"])
def test_source_option_is_gone(value: str, capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["build", "songs", "-o", "book.pdf", "--source", value])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "usage:" in err
    assert "unrecognized arguments" in err
    assert "--source" in err
