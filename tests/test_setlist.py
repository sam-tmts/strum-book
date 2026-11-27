"""Issue #13: the `set-list` type, with sets, set breaks and spares. Built from StrumBook
files with local `path` sources, on the fixture carols and synthetic songs."""

import re
from pathlib import Path

import pytest
from book_helpers import (
    AWAY,
    BETHLEHEM,
    EMMANUEL,
    FULL_BOOK,
    assert_clean_error,
    built,
    page_text,
    run,
    warning_lines,
    write_book,
    write_songs,
)
from pdf_helpers import FIXTURES, book_map, split_links
from pypdf import PdfReader

AWAY_T = "Away In A Manger"
EMMANUEL_T = "O Come, O Come, Emmanuel"
BETHLEHEM_T = "O Little Town Of Bethlehem"
SPARES = "Spares and encores"
CAROLS_T = [AWAY_T, EMMANUEL_T, BETHLEHEM_T]
SETLIST = 'type = "set-list"'


def one_set(name: str, songs: list[str], time: str = "", notes: str = "") -> str:
    text = f'[[songs.set]]\nname = "{name}"\n'
    if time:
        text += f'running-time = "{time}"\n'
    if notes:
        text += f"notes = '''\n{notes}\n'''\n"
    return text + "songs = [" + ", ".join(f'"{s}"' for s in songs) + "]\n"


def gig(spares: list[str] | None = None, sets: tuple[str, ...] = ("one", "two")) -> str:
    """The `[songs]` text for the example gig: Set 1 and Set 2, then spares."""
    text = ""
    if spares:
        text += "spares = [" + ", ".join(f'"{s}"' for s in spares) + "]\n"
    first = one_set("Set 1", [AWAY], "25 min", "Start 6:30. Twice if children join.")
    second = one_set("Set 2", [EMMANUEL], "20 min", "Collection buckets out.")
    return text + "\n" + "\n".join([first, second][: len(sets)])


EXAMPLE = gig([BETHLEHEM])
EXAMPLE_TITLES = [
    "Title",
    "Running order",
    "Set 1",
    AWAY_T,
    "Set 2",
    EMMANUEL_T,
    SPARES,
    BETHLEHEM_T,
]


def setlist(
    tmp_path: Path,
    songs: str = EXAMPLE,
    *,
    build: str = "",
    book: str = SETLIST,
    name: str = "gig.strumbook.toml",
) -> Path:
    return write_book(tmp_path, songs=songs, book=book, build=build, name=name)


def song_text(reader: PdfReader, pages: range) -> str:
    """Page text without digits, so books with shifted page numbers compare."""
    return re.sub(r"\d+", "", page_text(reader, pages))


def strip_targets(reader: PdfReader, page: int) -> list[int]:
    return [link.target for link in split_links(reader, page)[0]]


def pages_after_title(reader: PdfReader) -> range:
    return range(1, len(reader.pages))


# The example book.


def test_the_example_builds_in_running_order_with_break_pages_and_notes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(setlist(tmp_path), tmp_path / "gig.pdf", capsys=capsys)
    pages = book_map(reader)
    assert pages.titles == EXAMPLE_TITLES
    assert pages.pages == sorted(pages.pages)
    assert "Test Book" in page_text(reader, range(1))
    set_1 = page_text(reader, pages.pages_of("Set 1"))
    assert len(pages.pages_of("Set 1")) == 1
    for text in ["Set 1", "25 min", "Start 6:30. Twice if children join."]:
        assert text in set_1
    set_2 = page_text(reader, pages.pages_of("Set 2"))
    for text in ["Set 2", "20 min", "Collection buckets out."]:
        assert text in set_2
    assert "Set 2" not in set_1
    assert SPARES in page_text(reader, pages.pages_of(SPARES))
    assert len(pages.pages_of(SPARES)) == 1
    assert warning_lines(capsys.readouterr().err) == []


def test_songs_are_in_running_order_not_a_to_z(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = one_set("Late", [EMMANUEL, AWAY]) + "\n" + one_set("Early", [BETHLEHEM])
    reader = built(setlist(tmp_path, songs), tmp_path / "gig.pdf", capsys=capsys)
    assert book_map(reader).titles == [
        "Title",
        "Running order",
        "Late",
        EMMANUEL_T,
        AWAY_T,
        "Early",
        BETHLEHEM_T,
    ]


def test_the_notes_are_plain_text_shown_as_typed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    typed = "Drop *Away* if _late_: #1 costs $5 <ok>"
    songs = one_set("Set 1", [AWAY], notes=typed) + "\n" + one_set("Set 2", [EMMANUEL])
    reader = built(setlist(tmp_path, songs), tmp_path / "gig.pdf", capsys=capsys)
    assert typed in page_text(reader, book_map(reader).pages_of("Set 1"))


# The running-order page.


def test_the_running_order_lists_every_set_and_the_spares_with_links_to_songs(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(setlist(tmp_path), tmp_path / "gig.pdf", capsys=capsys)
    pages = book_map(reader)
    assert len(pages.pages_of("Running order")) == 1
    order = pages.first_page("Running order")
    text = page_text(reader, range(order, order + 1))
    expected = ["Set 1", "25 min", AWAY_T, "Set 2", "20 min", EMMANUEL_T]
    expected += [SPARES, BETHLEHEM_T]
    positions = [text.index(item) for item in expected]
    assert positions == sorted(positions)
    songs = {pages.first_page(t): t for t in [AWAY_T, EMMANUEL_T, BETHLEHEM_T]}
    _, others = split_links(reader, order)
    others.sort(key=lambda link: -link.rect[3])  # top to bottom
    targets = [link.target for link in others if link.target in songs]
    assert targets == [pages.first_page(t) for t in [AWAY_T, EMMANUEL_T, BETHLEHEM_T]]


def test_a_typical_gig_fits_on_one_running_order_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    names = [f"Gig Song {n:02d}" for n in range(1, 19)]
    folder = write_songs(
        tmp_path / "gig", {n: f"{{title:{n}}}\n[G]La la la\n" for n in names}
    )
    sets = [
        one_set("Set 1", [f"gig:{n}" for n in names[:7]], "25 min"),
        one_set("Set 2", [f"gig:{n}" for n in names[7:14]], "25 min"),
    ]
    songs = f'spares = ["gig:{names[14]}", "gig:{names[15]}"]\n\n' + "\n".join(sets)
    book = write_book(
        tmp_path,
        sources=f"[sources.gig]\npath = '{folder}'\n",
        songs=songs,
        book=SETLIST,
    )
    reader = built(book, tmp_path / "gig.pdf", capsys=capsys)
    pages = book_map(reader)
    assert len(pages.pages_of("Running order")) == 1
    text = page_text(reader, pages.pages_of("Running order"))
    for name in [*names[:14], names[14], names[15], SPARES]:
        assert name in text
    assert names[16] not in text


def test_each_song_links_back_to_the_running_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(setlist(tmp_path), tmp_path / "gig.pdf", capsys=capsys)
    pages = book_map(reader)
    order = pages.first_page("Running order")
    for title in [AWAY_T, EMMANUEL_T, BETHLEHEM_T]:
        for n in pages.pages_of(title):
            _, others = split_links(reader, n)
            assert order in {link.target for link in others}, f"{title} page {n}"


def test_back_links_to_the_running_order_work_with_the_index_on_too(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        setlist(tmp_path, build="index = true\nnavigation = true"),
        tmp_path / "gig.pdf",
        capsys=capsys,
    )
    pages = book_map(reader)
    order = pages.first_page("Running order")
    for title in [AWAY_T, EMMANUEL_T, BETHLEHEM_T]:
        for n in pages.pages_of(title):
            _, others = split_links(reader, n)
            assert order in {link.target for link in others}, f"{title} page {n}"


def test_two_page_songs_link_back_from_every_page_of_the_song(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    lines = "\n".join(
        f"[G]Line {n} of a long synthetic song [C]here" for n in range(90)
    )
    folder = write_songs(
        tmp_path / "long",
        {"Long": f"{{title:Long Song}}\n{lines}\n", "S": "{title:S}\n"},
    )
    book = write_book(
        tmp_path,
        sources=f"[sources.x]\npath = '{folder}'\n",
        songs=one_set("Set 1", ["x:Long", "x:S"]),
        book=SETLIST,
    )
    reader = built(book, tmp_path / "gig.pdf", capsys=capsys)
    pages = book_map(reader)
    order = pages.first_page("Running order")
    long_pages = pages.pages_of("Long Song")
    assert len(long_pages) > 1
    for n in long_pages:
        assert order in {link.target for link in split_links(reader, n)[1]}


# Defaults and options.


def test_setlist_defaults_leave_out_index_strip_reference_and_credits(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(setlist(tmp_path), tmp_path / "gig.pdf", capsys=capsys)
    titles = book_map(reader).titles
    for absent in ["Index", "Reference", "Credits"]:
        assert absent not in titles
    for n in range(len(reader.pages)):
        assert split_links(reader, n)[0] == [], f"page {n} has a strip"


ON_IN_BUILD = {
    "index": "index = true",
    "reference": "reference = true",
    "credits": "credits = true",
}


@pytest.mark.parametrize("option", ["index", "reference", "credits"])
@pytest.mark.parametrize("where", ["build", "command line"])
def test_each_extra_can_be_turned_on_in_build_or_on_the_command_line(
    option: str, where: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if where == "build":
        book, flags = setlist(tmp_path, build=ON_IN_BUILD[option]), []
    else:
        book, flags = setlist(tmp_path), [f"--{option}", "on"]
    reader = built(book, tmp_path / "gig.pdf", *flags, capsys=capsys)
    titles = book_map(reader).titles
    assert option.capitalize() in titles
    others = {"Index", "Reference", "Credits"} - {option.capitalize()}
    assert not others & set(titles)


@pytest.mark.parametrize("where", ["build", "command line"])
def test_navigation_can_be_turned_on_in_build_or_on_the_command_line(
    where: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if where == "build":
        book, flags = setlist(tmp_path, build="navigation = true"), []
    else:
        book, flags = setlist(tmp_path), ["--navigation", "on"]
    reader = built(book, tmp_path / "gig.pdf", *flags, capsys=capsys)
    assert split_links(reader, 0)[0] == []
    for n in pages_after_title(reader):
        assert split_links(reader, n)[0], f"page {n} has no strip"


def test_the_index_comes_straight_after_the_running_order(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        setlist(tmp_path), tmp_path / "gig.pdf", "--index", "on", capsys=capsys
    )
    assert book_map(reader).titles == [
        "Title",
        "Running order",
        "Index",
        *EXAMPLE_TITLES[2:],
    ]
    pages = book_map(reader)
    index = page_text(reader, pages.pages_of("Index"))
    for title in [AWAY_T, EMMANUEL_T, BETHLEHEM_T]:
        assert title in index


def test_reference_and_credits_come_last_when_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = setlist(tmp_path, build="reference = true\ncredits = true")
    reader = built(book, tmp_path / "gig.pdf", capsys=capsys)
    assert book_map(reader).titles == [*EXAMPLE_TITLES, "Reference", "Credits"]


def test_command_line_options_override_the_build_table_for_a_setlist(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = setlist(tmp_path, build="index = true\nreference = true\nnavigation = true")
    reader = built(
        book,
        tmp_path / "gig.pdf",
        "--index",
        "off",
        "--reference",
        "off",
        "--navigation",
        "off",
        capsys=capsys,
    )
    assert book_map(reader).titles == EXAMPLE_TITLES
    assert all(split_links(reader, n)[0] == [] for n in range(len(reader.pages)))


def test_type_on_the_command_line_gives_a_picked_book_the_setlist_defaults(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'pick = ["{AWAY}", "{EMMANUEL}"]'
    book = write_book(tmp_path, songs=songs)
    plain = built(book, tmp_path / "a.pdf", capsys=capsys)
    assert book_map(plain).titles[1] == "Index"
    reader = built(book, tmp_path / "b.pdf", "--type", "set-list", capsys=capsys)
    assert book_map(reader).titles == ["Title", "Running order", AWAY_T, EMMANUEL_T]


def test_set_list_type_in_the_file_is_accepted_without_warnings(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code, err = run(setlist(tmp_path), tmp_path / "gig.pdf", capsys=capsys)
    assert code == 0, err
    assert warning_lines(err) == []


# A song library with the new options.


def test_song_library_defaults_have_index_navigation_and_reference_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(write_book(tmp_path), tmp_path / "book.pdf", capsys=capsys)
    assert book_map(reader).titles == FULL_BOOK
    assert split_links(reader, 1)[0]


@pytest.mark.parametrize("where", ["build", "command line"])
def test_a_song_library_can_turn_index_navigation_and_reference_off(
    where: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if where == "build":
        book = write_book(
            tmp_path, build="index = false\nnavigation = false\nreference = false"
        )
        flags: list[str] = []
    else:
        book = write_book(tmp_path)
        flags = ["--index", "off", "--navigation", "off", "--reference", "off"]
    reader = built(book, tmp_path / "book.pdf", *flags, capsys=capsys)
    assert book_map(reader).titles == ["Title", *_carols(), "Credits"]
    assert all(split_links(reader, n)[0] == [] for n in range(len(reader.pages)))
    assert warning_lines(capsys.readouterr().err) == []


def _carols() -> list[str]:
    return [AWAY_T, EMMANUEL_T, BETHLEHEM_T]


# The link strip.


def strip_book(tmp_path: Path, songs: str, build: str = "navigation = true") -> Path:
    return setlist(tmp_path, songs, build=build)


def test_the_strip_links_running_order_each_set_and_the_spares(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(strip_book(tmp_path, EXAMPLE), tmp_path / "g.pdf", capsys=capsys)
    pages = book_map(reader)
    expected = [
        pages.first_page(t) for t in ["Running order", "Set 1", "Set 2", SPARES]
    ]
    assert split_links(reader, 0) == ([], [])
    for n in pages_after_title(reader):
        strip, _ = split_links(reader, n)
        assert [link.target for link in strip] == expected, f"page {n}"
        assert len({link.size for link in strip}) == 1, f"page {n}"
        assert strip[0].rect[0] < strip[-1].rect[0]


def test_the_strip_has_no_spares_cell_without_spares(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(strip_book(tmp_path, gig()), tmp_path / "g.pdf", capsys=capsys)
    pages = book_map(reader)
    expected = [pages.first_page(t) for t in ["Running order", "Set 1", "Set 2"]]
    for n in pages_after_title(reader):
        assert strip_targets(reader, n) == expected, f"page {n}"


def test_the_strip_ends_with_reference_when_it_is_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = strip_book(tmp_path, EXAMPLE, "navigation = true\nreference = true")
    reader = built(book, tmp_path / "g.pdf", capsys=capsys)
    pages = book_map(reader)
    titles = ["Running order", "Set 1", "Set 2", SPARES, "Reference"]
    expected = [pages.first_page(t) for t in titles]
    for n in pages_after_title(reader):
        strip, _ = split_links(reader, n)
        assert [link.target for link in strip] == expected, f"page {n}"
        assert len({link.size for link in strip}) == 1


def test_the_strip_goes_to_first_songs_when_there_are_no_break_pages(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = strip_book(tmp_path, EXAMPLE, "navigation = true\nset-breaks = false")
    reader = built(book, tmp_path / "g.pdf", capsys=capsys)
    pages = book_map(reader)
    first = [pages.first_page(t) for t in [AWAY_T, EMMANUEL_T, BETHLEHEM_T]]
    expected = [pages.first_page("Running order"), *first]
    for n in pages_after_title(reader):
        assert strip_targets(reader, n) == expected, f"page {n}"


def test_a_single_set_strip_goes_to_running_order_and_the_set(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = one_set("Only", [AWAY, EMMANUEL])
    reader = built(strip_book(tmp_path, songs), tmp_path / "g.pdf", capsys=capsys)
    pages = book_map(reader)
    expected = [pages.first_page("Running order"), pages.first_page(AWAY_T)]
    for n in pages_after_title(reader):
        assert strip_targets(reader, n) == expected, f"page {n}"


def test_a_book_with_no_named_sets_has_no_strip_even_with_navigation_on(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'pick = ["{AWAY}", "{EMMANUEL}"]'
    reader = built(strip_book(tmp_path, songs), tmp_path / "g.pdf", capsys=capsys)
    for n in range(len(reader.pages)):
        assert split_links(reader, n)[0] == [], f"page {n}"
    reader = built(
        setlist(tmp_path, songs, name="b.strumbook.toml"),
        tmp_path / "h.pdf",
        "--navigation",
        "on",
        capsys=capsys,
    )
    for n in range(len(reader.pages)):
        assert split_links(reader, n)[0] == [], f"page {n}"


def test_navigation_off_in_a_setlist_removes_the_strip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = strip_book(tmp_path, EXAMPLE)
    reader = built(book, tmp_path / "g.pdf", "--navigation", "off", capsys=capsys)
    assert all(split_links(reader, n)[0] == [] for n in range(len(reader.pages)))


# Set breaks.


def test_set_breaks_false_leaves_out_the_break_pages_and_nothing_else(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    full = built(setlist(tmp_path), tmp_path / "full.pdf", capsys=capsys)
    book = setlist(tmp_path, build="set-breaks = false", name="b.strumbook.toml")
    plain = built(book, tmp_path / "plain.pdf", capsys=capsys)
    full_map, plain_map = book_map(full), book_map(plain)
    assert plain_map.titles == [
        "Title",
        "Running order",
        AWAY_T,
        EMMANUEL_T,
        BETHLEHEM_T,
    ]
    assert plain_map.page_count == full_map.page_count - 3
    for title in [AWAY_T, EMMANUEL_T, BETHLEHEM_T]:
        assert song_text(plain, plain_map.pages_of(title)) == song_text(
            full, full_map.pages_of(title)
        )
    order = page_text(plain, plain_map.pages_of("Running order"))
    for text in ["Set 1", "25 min", "Set 2", "20 min", SPARES]:
        assert text in order
    assert "Collection buckets out." not in page_text(plain, range(len(plain.pages)))
    assert split_links(plain, 1)[0] == []


def test_set_breaks_can_be_turned_off_on_the_command_line(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(
        setlist(tmp_path),
        tmp_path / "g.pdf",
        "--set-breaks",
        "off",
        capsys=capsys,
    )
    assert book_map(reader).titles == [
        "Title",
        "Running order",
        AWAY_T,
        EMMANUEL_T,
        BETHLEHEM_T,
    ]


def test_set_breaks_on_the_command_line_overrides_the_build_table(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = setlist(tmp_path, build="set-breaks = false")
    reader = built(book, tmp_path / "g.pdf", "--set-breaks", "on", capsys=capsys)
    assert book_map(reader).titles == EXAMPLE_TITLES


def test_running_order_links_still_work_without_break_pages(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = setlist(tmp_path, build="set-breaks = false")
    reader = built(book, tmp_path / "g.pdf", capsys=capsys)
    pages = book_map(reader)
    targets = {link.target for link in split_links(reader, 1)[1]}
    for title in [AWAY_T, EMMANUEL_T, BETHLEHEM_T]:
        assert pages.first_page(title) in targets


def test_a_single_set_with_no_spares_gets_no_break_page_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = one_set("Only set", [AWAY, EMMANUEL], "30 min", "A note.")
    reader = built(setlist(tmp_path, songs), tmp_path / "g.pdf", capsys=capsys)
    pages = book_map(reader)
    assert pages.titles == ["Title", "Running order", AWAY_T, EMMANUEL_T]
    assert "A note." not in page_text(reader, range(2, len(reader.pages)))
    assert "Only set" in page_text(reader, pages.pages_of("Running order"))


def test_a_single_set_with_no_spares_can_still_ask_for_a_break_page(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = one_set("Only set", [AWAY, EMMANUEL], "30 min", "A note.")
    book = setlist(tmp_path, songs, build="set-breaks = true")
    reader = built(book, tmp_path / "g.pdf", capsys=capsys)
    pages = book_map(reader)
    assert pages.titles == ["Title", "Running order", "Only set", AWAY_T, EMMANUEL_T]
    assert "A note." in page_text(reader, pages.pages_of("Only set"))


def test_a_single_set_with_spares_gets_break_pages_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'spares = ["{BETHLEHEM}"]\n\n' + one_set("Only set", [AWAY, EMMANUEL])
    reader = built(setlist(tmp_path, songs), tmp_path / "g.pdf", capsys=capsys)
    assert book_map(reader).titles == [
        "Title",
        "Running order",
        "Only set",
        AWAY_T,
        EMMANUEL_T,
        SPARES,
        BETHLEHEM_T,
    ]


def test_two_sets_with_no_spares_get_break_pages_by_default(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    reader = built(setlist(tmp_path, gig()), tmp_path / "g.pdf", capsys=capsys)
    assert book_map(reader).titles == EXAMPLE_TITLES[:6]


def test_a_picked_list_is_one_unnamed_set_with_no_set_break(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'pick = ["{AWAY}", "{EMMANUEL}"]'
    reader = built(setlist(tmp_path, songs), tmp_path / "g.pdf", capsys=capsys)
    assert book_map(reader).titles == ["Title", "Running order", AWAY_T, EMMANUEL_T]
    forced = built(
        setlist(tmp_path, songs, name="b.strumbook.toml"),
        tmp_path / "h.pdf",
        "--set-breaks",
        "on",
        capsys=capsys,
    )
    assert book_map(forced).titles == ["Title", "Running order", AWAY_T, EMMANUEL_T]


def test_a_picked_list_with_spares_gets_a_break_page_for_the_spares_only(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'pick = ["{AWAY}", "{EMMANUEL}"]\nspares = ["{BETHLEHEM}"]'
    reader = built(setlist(tmp_path, songs), tmp_path / "g.pdf", capsys=capsys)
    pages = book_map(reader)
    assert pages.titles == [
        "Title",
        "Running order",
        AWAY_T,
        EMMANUEL_T,
        SPARES,
        BETHLEHEM_T,
    ]
    order = page_text(reader, pages.pages_of("Running order"))
    assert order.index(AWAY_T) < order.index(SPARES) < order.index(BETHLEHEM_T)


# Errors: a clear message, no partial PDF.

NOPE = "carols:No Such Song"
EXTRA = f'[[songs.set]]\nname = "Set 2"\nsongs = ["{EMMANUEL}"]\n'


def fails(
    tmp_path: Path,
    songs: str,
    capsys: pytest.CaptureFixture[str],
    *needles: str,
    book: str = SETLIST,
) -> None:
    out = tmp_path / "gig.pdf"
    code, err = run(setlist(tmp_path, songs, book=book), out, capsys=capsys)
    assert_clean_error(code, err, out, *needles)


def test_a_missing_song_in_a_set_is_an_error_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = one_set("Set 1", [AWAY, NOPE]) + EXTRA
    fails(tmp_path, songs, capsys, "No Such Song")


def test_a_missing_song_in_the_spares_is_an_error_naming_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fails(tmp_path, gig([NOPE]), capsys, "No Such Song")


def test_an_empty_set_is_an_error_naming_the_set(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = (
        one_set("Set 1", [AWAY]) + '\n[[songs.set]]\nname = "Empty one"\nsongs = []\n'
    )
    fails(tmp_path, songs, capsys, "Empty one")


def test_a_set_with_no_songs_key_is_an_error_naming_the_set(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = one_set("Set 1", [AWAY]) + '\n[[songs.set]]\nname = "Bare set"\n'
    fails(tmp_path, songs, capsys, "Bare set")


def test_a_set_without_a_name_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = one_set("Set 1", [AWAY]) + f'\n[[songs.set]]\nsongs = ["{EMMANUEL}"]\n'
    fails(tmp_path, songs, capsys, "name")


@pytest.mark.parametrize(
    "case", ["in one set", "in two sets", "in a set and the spares"]
)
def test_a_song_in_two_places_is_an_error_naming_the_song(
    case: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    if case == "in one set":
        songs = one_set("Set 1", [AWAY, EMMANUEL, AWAY])
    elif case == "in two sets":
        songs = one_set("Set 1", [AWAY]) + "\n" + one_set("Set 2", [EMMANUEL, AWAY])
    else:
        songs = f'spares = ["{AWAY}"]\n\n' + one_set("Set 1", [AWAY, EMMANUEL])
    fails(tmp_path, songs, capsys, "Away In A Manger")


def test_a_song_twice_in_the_spares_is_an_error_naming_the_song(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'spares = ["{BETHLEHEM}", "{BETHLEHEM}"]\n\n' + one_set("Set 1", [AWAY])
    fails(tmp_path, songs, capsys, "O Little Town Of Bethlehem")


def test_include_in_a_setlist_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    fails(tmp_path, 'include = "all"\n\n' + one_set("Set 1", [AWAY]), capsys, "include")
    fails(tmp_path, 'include = "all"', capsys, "include")


def test_exclude_in_a_setlist_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'exclude = ["{AWAY}"]\n\n' + one_set("Set 1", [AWAY, EMMANUEL])
    fails(tmp_path, songs, capsys, "exclude")


def test_sets_and_pick_together_are_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'pick = ["{AWAY}"]\n\n' + one_set("Set 1", [EMMANUEL])
    fails(tmp_path, songs, capsys, "pick")


def test_order_is_just_an_unknown_key_in_a_set_list(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'pick = ["{EMMANUEL}", "{AWAY}"]\norder = "a-z"'
    out = tmp_path / "g.pdf"
    code, err = run(setlist(tmp_path, songs), out, capsys=capsys)
    assert code == 0, err
    warnings = warning_lines(err)
    assert len(warnings) == 1 and "order" in warnings[0]
    reader = PdfReader(out)
    assert book_map(reader).titles == ["Title", "Running order", EMMANUEL_T, AWAY_T]


def test_sets_in_a_song_library_are_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = 'include = "all"\n\n' + one_set("Set 1", [AWAY])
    fails(tmp_path, songs, capsys, "set", book='type = "song-library"')


def test_spares_in_a_song_library_are_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'include = "all"\nspares = ["{AWAY}"]'
    fails(tmp_path, songs, capsys, "spares", book='type = "song-library"')
    fails(tmp_path, songs, capsys, "spares", book="")


def test_the_set_list_type_on_a_folder_build_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "folder.pdf"
    code, err = run(FIXTURES, out, "--type", "set-list", capsys=capsys)
    assert_clean_error(code, err, out, "set-list")


def test_a_failed_setlist_build_leaves_an_existing_pdf_alone(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "gig.pdf"
    out.write_bytes(b"earlier build")
    book = setlist(tmp_path, one_set("Set 1", [AWAY, NOPE]))
    code, err = run(book, out, capsys=capsys)
    assert code == 1, err
    assert "No Such Song" in err
    assert out.read_bytes() == b"earlier build"


# Partial song library strips.


def strip_of_default(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> list[int]:
    reader = built(
        write_book(tmp_path, name="d.strumbook.toml"), tmp_path / "d.pdf", capsys=capsys
    )
    return strip_targets(reader, 1)


@pytest.mark.parametrize("where", ["build", "command line"])
def test_a_song_library_without_an_index_has_a_strip_without_its_cell(
    where: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    default = strip_of_default(tmp_path, capsys)
    if where == "build":
        book, flags = write_book(tmp_path, build="index = false"), []
    else:
        book, flags = write_book(tmp_path), ["--index", "off"]
    reader = built(book, tmp_path / "b.pdf", *flags, capsys=capsys)
    pages = book_map(reader)
    assert "Index" not in pages.titles
    credits = set(pages.pages_of("Credits"))
    for n in pages_after_title(reader):
        strip, _ = split_links(reader, n)
        assert len(strip) == 27, f"page {n}"
        assert len({link.size for link in strip}) == 1
        assert [link.target for link in strip] == [t - 1 for t in default[1:]], (
            f"page {n}"
        )  # the index page is gone
    assert strip_targets(reader, 1)[-1] == pages.first_page("Reference")
    for title in CAROLS_T:
        for n in pages.pages_of(title):
            others = {link.target for link in split_links(reader, n)[1]}
            assert others <= credits, f"{title} page {n}"


def test_a_song_library_without_reference_ends_its_strip_on_the_last_song(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    default = strip_of_default(tmp_path, capsys)
    book = write_book(tmp_path, build="reference = false")
    reader = built(book, tmp_path / "b.pdf", capsys=capsys)
    pages = book_map(reader)
    assert "Reference" not in pages.titles
    last = pages.first_page(BETHLEHEM_T)
    for n in pages_after_title(reader):
        strip, _ = split_links(reader, n)
        assert len(strip) == 27, f"page {n}"
        assert len({link.size for link in strip}) == 1
        targets = [link.target for link in strip]
        assert targets[0] == pages.first_page("Index")
        assert targets[1:16] == default[1:16]  # A to O
        assert targets[16:] == [last] * 11  # P to Z


def test_a_song_library_without_index_or_reference_has_just_a_to_z(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    default = strip_of_default(tmp_path, capsys)
    book = write_book(tmp_path, build="index = false\nreference = false")
    reader = built(book, tmp_path / "b.pdf", capsys=capsys)
    for n in pages_after_title(reader):
        strip, _ = split_links(reader, n)
        assert len(strip) == 26, f"page {n}"
        assert len({link.size for link in strip}) == 1
    pages = book_map(reader)
    targets = strip_targets(reader, 1)
    assert targets[:15] == [t - 1 for t in default[1:16]]
    assert targets[15:] == [pages.first_page(BETHLEHEM_T)] * 11


# A set list with pick and spares.


def test_a_picked_list_with_spares_has_a_two_cell_strip(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    songs = f'pick = ["{AWAY}", "{EMMANUEL}"]\nspares = ["{BETHLEHEM}"]'
    book = setlist(tmp_path, songs, build="navigation = true")
    reader = built(book, tmp_path / "g.pdf", capsys=capsys)
    pages = book_map(reader)
    expected = [pages.first_page("Running order"), pages.first_page(SPARES)]
    for n in pages_after_title(reader):
        strip, _ = split_links(reader, n)
        assert [link.target for link in strip] == expected, f"page {n}"
        assert len({link.size for link in strip}) == 1


# Bad values and error wording.


@pytest.mark.parametrize(
    "line",
    [
        'index = "yes"',
        "navigation = 1",
        'reference = "off"',
        'set-breaks = "on"',
    ],
)
def test_a_bad_value_for_a_new_build_key_is_an_error_naming_the_key(
    line: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "gig.pdf"
    code, err = run(setlist(tmp_path, build=line), out, capsys=capsys)
    assert_clean_error(code, err, out, line.split(" ")[0])


def test_song_library_on_the_command_line_rejects_a_book_with_sets(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "gig.pdf"
    code, err = run(setlist(tmp_path), out, "--type", "song-library", capsys=capsys)
    assert_clean_error(code, err, out, "set", "song")
