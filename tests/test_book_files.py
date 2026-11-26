"""Issue #12: book files with local `path` sources, on the fixture carols and
synthetic songs. Git sources are in test_git_sources.py."""

import shutil
from datetime import date
from pathlib import Path

import pytest
from book_helpers import (
    AWAY,
    BETHLEHEM,
    CAROLS,
    CAROLS_SOURCE,
    EMMANUEL,
    FULL_BOOK,
    assert_clean_error,
    built,
    error_lines,
    index_targets,
    page_text,
    run,
    uris,
    warning_lines,
    write_book,
    write_songs,
)
from pdf_helpers import FIXTURES, STRIP_CELLS, book_map, split_links, text_of
from pypdf import PdfReader

from strumbook.cli import main

NOTES = "Bring mince pies.\n\nCarols marked with a capo are played as written.\n"


def titles(reader: PdfReader) -> list[str]:
    return book_map(reader).titles


# The book described by a book file.


def test_the_christmas_style_example_builds_the_same_book_plus_subtitle_and_notes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = built(FIXTURES, tmp_path / "folder.pdf", capsys=capsys)
    book = write_book(
        tmp_path,
        title="Christmas Carols",
        book=(
            'style = "songbook"\nedition = "2026-12-01"\n'
            f'subtitle = "Christmas 2026"\nnotes = """\n{NOTES}"""'
        ),
        build="title-page = true\ncredits = true",
    )
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)

    pages = book_map(reader)
    assert pages.titles == FULL_BOOK
    assert pages.pages == book_map(folder).pages  # same layout, page for page
    songs = range(pages.first_page("Away In A Manger"), pages.first_page("Reference"))
    for n in songs:
        assert page_text(reader, range(n, n + 1)) == page_text(folder, range(n, n + 1))
    title_page = page_text(reader, range(1))
    for text in [
        "Christmas Carols",
        "2026-12-01",
        "Christmas 2026",
        "Bring mince pies.",
        "Carols marked with a capo are played as written.",
    ]:
        assert text in title_page
    assert title_page.index("Bring mince pies.") < title_page.index("Carols marked")
    assert reader.metadata is not None
    assert reader.metadata.title == "Christmas Carols"


def test_title_page_edition_defaults_to_todays_date(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(write_book(tmp_path), tmp_path / "book.pdf", capsys=capsys)
    today = date.today()  # this can flake only if the build runs over midnight
    assert f"{today.day} {today:%B %Y}" in page_text(reader, range(1))
    assert "Test Book" in page_text(reader, range(1))


def test_notes_are_plain_text_shown_as_typed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    typed = "Bring *mince* pies, _lots_: #1 costs $5 @home <ok> = fun"
    book = write_book(tmp_path, book=f"notes = '''\n{typed}\n'''")
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert typed in page_text(reader, range(1))


def test_relative_paths_are_relative_to_the_book_file_not_the_working_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    shutil.copytree(FIXTURES, tmp_path / "collections" / "carols")
    book = write_book(
        tmp_path, sources="[sources.carols]\npath = '../collections/carols'\n"
    )
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == FULL_BOOK


def test_songs_folder_is_songs_if_it_exists_and_folder_overrides_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    collection = tmp_path / "collection"
    write_songs(collection / "songs", {"inner": "{title:Inner Song}\n[G]La\n"})
    write_songs(collection / "other", {"o": "{title:Other Song}\n[G]La\n"})
    write_songs(collection, {"outer": "{title:Outer Song}\n[G]La\n"})
    source = f"[sources.c]\npath = '{collection}'\n"
    default = built(
        write_book(tmp_path, sources=source, name="a.book.toml"),
        tmp_path / "a.pdf",
        capsys=capsys,
    )
    assert titles(default) == ["Title", "Index", "Inner Song", "Reference", "Credits"]
    chosen = built(
        write_book(tmp_path, sources=source + "folder = 'other'\n", name="b.book.toml"),
        tmp_path / "b.pdf",
        capsys=capsys,
    )
    assert titles(chosen) == ["Title", "Index", "Other Song", "Reference", "Credits"]


def test_a_collection_with_no_songs_folder_uses_its_top_level(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    collection = write_songs(tmp_path / "flat", {"x": "{title:Flat Song}\n[G]La\n"})
    book = write_book(tmp_path, sources=f"[sources.flat]\npath = '{collection}'\n")
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == ["Title", "Index", "Flat Song", "Reference", "Credits"]


# Choosing and ordering songs.


def two_collections(tmp_path: Path) -> str:
    write_songs(
        tmp_path / "one",
        {
            "Zebra Song": "{title:Zebra Song}\n[G]La\n",
            "Mango": "{title:Mango}\n[G]La\n",
        },
    )
    write_songs(
        tmp_path / "two",
        {"Apple Tree": "{title:Apple Tree}\n[G]La\n", "Kiwi": "{title:Kiwi}\n[G]La\n"},
    )
    return (
        f"[sources.one]\npath = '{tmp_path / 'one'}'\n"
        f"[sources.two]\npath = '{tmp_path / 'two'}'\n"
    )


def test_include_all_takes_every_song_in_every_source_a_to_z(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, sources=two_collections(tmp_path))
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == [
        "Title",
        "Index",
        "Apple Tree",
        "Kiwi",
        "Mango",
        "Zebra Song",
        "Reference",
        "Credits",
    ]


def test_include_a_list_of_sources_takes_only_those(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(
        tmp_path, sources=two_collections(tmp_path), songs='include = ["two"]'
    )
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == [
        "Title",
        "Index",
        "Apple Tree",
        "Kiwi",
        "Reference",
        "Credits",
    ]


def test_pick_takes_just_those_songs_a_to_z_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, songs=f'pick = ["{BETHLEHEM}", "{AWAY}"]')
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == [
        "Title",
        "Index",
        "Away In A Manger",
        "O Little Town Of Bethlehem",
        "Reference",
        "Credits",
    ]


def test_pick_and_include_can_be_mixed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(
        tmp_path,
        sources=two_collections(tmp_path),
        songs='include = ["two"]\npick = ["one:Zebra Song"]',
    )
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == [
        "Title",
        "Index",
        "Apple Tree",
        "Kiwi",
        "Zebra Song",
        "Reference",
        "Credits",
    ]


def test_exclude_leaves_songs_out_of_what_include_brings_in(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, songs=f'include = "all"\nexclude = ["{EMMANUEL}"]')
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    expected = ["Away In A Manger", "O Little Town Of Bethlehem"]
    assert titles(reader) == ["Title", "Index", *expected, "Reference", "Credits"]
    assert "Veni, Emmanuel" not in text_of(reader)


def test_listed_order_follows_pick_but_the_index_stays_a_to_z(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(
        tmp_path,
        songs=f'pick = ["{BETHLEHEM}", "{EMMANUEL}", "{AWAY}"]\norder = "listed"',
    )
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    pages = book_map(reader)
    listed = [CAROLS[2], CAROLS[1], CAROLS[0]]
    assert pages.titles == ["Title", "Index", *listed, "Reference", "Credits"]
    assert pages.pages == sorted(pages.pages)
    az = [pages.first_page(title) for title in CAROLS]
    assert index_targets(reader, pages.first_page("Index")) == [
        *az,
        pages.first_page("Reference"),
        pages.first_page("Credits"),
    ]


def test_order_a_to_z_can_be_asked_for_by_name(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(
        tmp_path, songs=f'pick = ["{BETHLEHEM}", "{AWAY}"]\norder = "a-z"'
    )
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader)[2:4] == ["Away In A Manger", "O Little Town Of Bethlehem"]


def test_same_file_name_in_two_sources_appears_twice_with_the_artist_to_tell_apart(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for name, artist in [("left", "Ann Poet"), ("right", "Bob Writer")]:
        write_songs(
            tmp_path / name,
            {"Shared Tune": f"{{title:Shared Tune}}\n{{artist:{artist}}}\n[G]La\n"},
        )
    sources = (
        f"[sources.left]\npath = '{tmp_path / 'left'}'\n"
        f"[sources.right]\npath = '{tmp_path / 'right'}'\n"
    )
    for songs in [
        'include = "all"',
        'pick = ["left:Shared Tune", "right:Shared Tune"]',
    ]:
        book = write_book(tmp_path, sources=sources, songs=songs)
        reader = built(book, tmp_path / "book.pdf", capsys=capsys)
        assert titles(reader) == [
            "Title",
            "Index",
            "Shared Tune",
            "Shared Tune",
            "Reference",
            "Credits",
        ]
        index = page_text(reader, book_map(reader).pages_of("Index"))
        assert "Ann Poet" in index
        assert "Bob Writer" in index


# The link strip.


def test_an_a_to_z_book_keeps_todays_link_strip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = built(FIXTURES, tmp_path / "folder.pdf", capsys=capsys)
    book = write_book(tmp_path)
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    pages = book_map(reader)
    assert split_links(reader, 0) == ([], [])
    for n in range(1, pages.page_count):
        strip, _ = split_links(reader, n)
        assert len(strip) == STRIP_CELLS, f"page {n}"
        expected, _ = split_links(folder, n)
        assert [link.target for link in strip] == [link.target for link in expected]
        assert [link.size for link in strip] == [link.size for link in expected]
    assert strip[0].target == pages.first_page("Index")
    assert strip[-1].target == pages.first_page("Reference")


def test_a_picked_a_to_z_book_also_has_the_strip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, songs=f'pick = ["{BETHLEHEM}", "{AWAY}"]')
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    for n in range(1, len(reader.pages)):
        assert len(split_links(reader, n)[0]) == STRIP_CELLS, f"page {n}"


def test_a_listed_book_has_no_link_strip_but_index_and_title_links_work(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(
        tmp_path,
        songs=f'pick = ["{BETHLEHEM}", "{EMMANUEL}", "{AWAY}"]\norder = "listed"',
    )
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    pages = book_map(reader)
    for n in range(pages.page_count):
        assert split_links(reader, n)[0] == [], f"page {n} has a strip"
    index_pages = set(pages.pages_of("Index"))
    credits = set(pages.pages_of("Credits"))
    entries = index_targets(reader, pages.first_page("Index"))
    assert len(entries) == len(CAROLS) + 2  # songs, Reference, Credits
    for title in CAROLS:
        for n in pages.pages_of(title):
            _, others = split_links(reader, n)
            assert others, f"{title} page {n} has no title/page-number link"
            assert {link.target for link in others} - credits <= index_pages


# Settings: style defaults, then [build], then command-line options.


def test_build_settings_in_the_book_file_apply(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(
        tmp_path,
        build=(
            'title-page = false\ncredits = false\nmid-word-chords = "above"\n'
            "pdf-tags = false"
        ),
    )
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == ["Index", *CAROLS, "Reference"]
    assert "Israel" in text_of(reader)  # chords above words keep them whole
    assert "/StructTreeRoot" not in reader.trailer["/Root"]


def test_anything_left_out_of_build_takes_the_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(write_book(tmp_path), tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == FULL_BOOK
    assert "Israel" not in text_of(reader)
    assert "/StructTreeRoot" in reader.trailer["/Root"]


def test_command_line_options_override_the_build_table(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(
        tmp_path,
        build=(
            'title-page = false\ncredits = false\nmid-word-chords = "above"\n'
            "pdf-tags = false"
        ),
    )
    reader = built(
        book,
        tmp_path / "book.pdf",
        *["--title-page", "on", "--credits", "on"],
        *["--mid-word-chords", "inline", "--pdf-tags", "on"],
        capsys=capsys,
    )
    assert titles(reader) == FULL_BOOK
    assert "Israel" not in text_of(reader)
    assert "/StructTreeRoot" in reader.trailer["/Root"]


def test_command_line_can_turn_off_what_the_build_table_turns_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, build="title-page = true\ncredits = true")
    reader = built(book, tmp_path / "book.pdf", "--credits", "off", capsys=capsys)
    assert titles(reader) == ["Title", "Index", *CAROLS, "Reference"]


def test_edition_on_the_command_line_overrides_the_book_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, book='edition = "2026-12-01"')
    kept = built(book, tmp_path / "kept.pdf", capsys=capsys)
    assert "2026-12-01" in page_text(kept, range(1))
    over = built(book, tmp_path / "over.pdf", "--edition", "Advent 2026", capsys=capsys)
    assert "Advent 2026" in page_text(over, range(1))
    assert "2026-12-01" not in page_text(over, range(1))


def test_a_build_setting_survives_a_style_given_on_the_command_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, build="credits = false\ntitle-page = false")
    reader = built(book, tmp_path / "book.pdf", "--style", "songbook", capsys=capsys)
    assert titles(reader) == ["Index", *CAROLS, "Reference"]


def test_style_songbook_is_accepted_for_a_folder_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(FIXTURES, tmp_path / "b.pdf", "--style", "songbook", capsys=capsys)
    assert titles(reader) == FULL_BOOK


def test_an_unknown_style_on_the_command_line_is_a_usage_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exc:
        main(["build", str(FIXTURES), "-o", str(tmp_path / "b.pdf"), "--style", "gig"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "usage:" in err
    assert "invalid choice" in err
    assert not (tmp_path / "b.pdf").exists()


# `strumbook build SONGS_DIR` and the removal of --source.


def test_a_folder_build_still_works_and_has_no_source_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(FIXTURES, tmp_path / "b.pdf", capsys=capsys)
    assert titles(reader) == FULL_BOOK
    credits = book_map(reader).pages_of("Credits")
    assert "Songs came from" not in page_text(reader, credits)


@pytest.mark.parametrize("target", ["folder", "book-file"])
def test_source_option_is_gone_and_is_a_usage_error(
    target: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = FIXTURES if target == "folder" else write_book(tmp_path)
    out = tmp_path / "b.pdf"
    with pytest.raises(SystemExit) as exc:
        main(["build", str(path), "-o", str(out), "--source", "https://example.org/x"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "usage:" in err
    assert "unrecognized arguments" in err
    assert "--source" in err
    assert not out.exists()


# Credits: where the songs come from.


def about_of(reader: PdfReader) -> str:
    last = book_map(reader).pages_of("Credits")[-1]
    return page_text(reader, range(last, last + 1))


def test_a_sources_link_is_credited_with_a_clickable_address(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    link = "https://example.org/our-songs"
    book = write_book(tmp_path, sources=CAROLS_SOURCE + f"link = '{link}'\n")
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert link in uris(reader)
    about = about_of(reader)
    assert "Songs came from" in about
    assert "example.org/our-songs" in about


def test_an_http_link_is_accepted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    link = "http://example.org/our-songs"
    book = write_book(tmp_path, sources=CAROLS_SOURCE + f"link = '{link}'\n")
    assert link in uris(built(book, tmp_path / "book.pdf", capsys=capsys))


def test_a_path_source_without_a_link_is_left_out_of_credits(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(write_book(tmp_path), tmp_path / "book.pdf", capsys=capsys)
    assert uris(reader) == {
        "https://github.com/sam-tmts/strumbook",
        "https://typst.app",
        "https://www.brailleinstitute.org/freefont/",
    }
    assert "Songs came from" not in about_of(reader)
    assert str(FIXTURES) not in text_of(reader)  # a private path is not printed


def test_only_the_sources_with_a_link_are_credited(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    sources = two_collections(tmp_path).replace(
        "[sources.two]", "[sources.two]\nlink = 'https://example.org/two'"
    )
    reader = built(
        write_book(tmp_path, sources=sources), tmp_path / "b.pdf", capsys=capsys
    )
    found = uris(reader)
    assert "https://example.org/two" in found
    assert not any(str(tmp_path) in uri for uri in found)
    assert "example.org/two" in about_of(reader)


@pytest.mark.parametrize(
    "link", ["github.com/x/songs", "ftp://example.org/x", "file:///tmp/x", ""]
)
def test_a_link_that_is_not_a_web_address_is_an_error(
    link: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, sources=CAROLS_SOURCE + f"link = '{link}'\n")
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out, "carols", "link")


# Things that go wrong.


@pytest.mark.parametrize(
    ("kind", "needles"),
    [
        ("missing-song", ["No Such Song"]),
        ("unknown-source-in-pick", ["nope"]),
        ("unknown-source-in-include", ["nope"]),
        ("empty-source", ["hollow"]),
        ("source-folder-missing", ["carols"]),
        ("bad-source-name", ["Carols_1"]),
        ("path-and-git", ["carols"]),
        ("neither-path-nor-git", ["carols"]),
    ],
)
def test_each_error_names_the_problem_and_leaves_no_pdf(
    kind: str,
    needles: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    hollow = tmp_path / "hollow"
    hollow.mkdir()
    cases = {
        "missing-song": {"songs": 'pick = ["carols:No Such Song"]'},
        "unknown-source-in-pick": {"songs": 'pick = ["nope:Away In A Manger"]'},
        "unknown-source-in-include": {"songs": 'include = ["nope"]'},
        "empty-source": {"sources": f"[sources.hollow]\npath = '{hollow}'\n"},
        "source-folder-missing": {
            "sources": f"[sources.carols]\npath = '{tmp_path / 'nowhere'}'\n"
        },
        "bad-source-name": {"sources": f"[sources.Carols_1]\npath = '{FIXTURES}'\n"},
        "path-and-git": {
            "sources": CAROLS_SOURCE + "git = 'https://example.test/c.git'\n"
        },
        "neither-path-nor-git": {"sources": "[sources.carols]\nfolder = 'x'\n"},
    }
    book = write_book(tmp_path, **cases[kind])
    out = tmp_path / "out" / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out, *needles)


def test_a_book_file_with_no_title_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = tmp_path / "untitled.book.toml"
    book.write_text(f'[book]\n\n{CAROLS_SOURCE}\n[songs]\ninclude = "all"\n')
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err.replace(str(book), "BOOK"), out, "title")


def test_a_book_file_that_is_not_toml_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = tmp_path / "broken.book.toml"
    book.write_text("[book\ntitle = = 'x'\n", encoding="utf-8")
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out, "broken.book.toml")
    assert "folder" not in err  # read as a book file, not taken for a songs folder


def test_a_missing_book_file_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "book.pdf"
    code, err = run(tmp_path / "missing.book.toml", out, capsys=capsys)
    assert_clean_error(code, err, out, "missing.book.toml")
    assert "folder" not in err  # it is named as a book file, not a songs folder


def test_bad_chordpro_builds_what_it_can_with_warnings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = write_songs(
        tmp_path / "synthetic",
        {
            "tune": "{title:Synthetic Tune}\n{frobnicate: yes}\n[G]La [Xyz7b13]la\n",
            "fine": "{title:Fine Tune}\n[G]La\n",
        },
    )
    book = write_book(tmp_path, sources=f"[sources.s]\npath = '{songs}'\n")
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert code == 0, err
    assert titles(PdfReader(out))[2:4] == ["Fine Tune", "Synthetic Tune"]
    warnings = warning_lines(err)
    assert any("frobnicate" in line for line in warnings)
    assert any("Xyz7b13" in line for line in warnings)
    assert not error_lines(err)


@pytest.mark.parametrize(
    ("place", "key", "args"),
    [
        ("book", "flavour", {"book": 'flavour = "mint"'}),
        ("sources", "sparkle", {"sources": CAROLS_SOURCE + "sparkle = 'yes'\n"}),
        ("songs", "shuffle", {"songs": 'include = "all"\nshuffle = true'}),
        ("build", "glitter", {"build": "glitter = true"}),
        ("table", "[future]", {"sources": CAROLS_SOURCE + "\n[future]\nx = 1\n"}),
    ],
)
def test_unknown_keys_warn_and_the_book_still_builds(
    place: str,
    key: str,
    args: dict[str, str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    book = write_book(tmp_path, **args)
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert code == 0, err
    assert titles(PdfReader(out)) == FULL_BOOK
    name = key.strip("[]")
    assert any(name in line for line in warning_lines(err)), err
    assert not error_lines(err)


def test_a_clean_book_file_prints_no_warnings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(
        tmp_path,
        book='style = "songbook"\nedition = "2026"\nsubtitle = "s"\nnotes = "n"',
        build="title-page = true\ncredits = true\nmid-word-chords = 'inline'\n"
        "pdf-tags = true",
    )
    code, err = run(book, tmp_path / "book.pdf", capsys=capsys)
    assert code == 0
    assert err == ""
