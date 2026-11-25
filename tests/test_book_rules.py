"""The diagram rules, chord grouping and the chord table."""

import pytest
from strumbook.book import group_diagrams, show_diagrams
from strumbook.chords import shape


@pytest.mark.parametrize(
    ("diagrams", "pages_with", "pages_without", "expected"),
    [
        (9, 1, 1, True),  # more than 8 but fits on one page with them
        (9, 2, 1, False),  # rule 1: more than 8 and does not fit on one page
        (9, 2, 2, False),  # rule 1 again
        (8, 2, 2, True),  # 8 is not "more than 8"; the song needs 2 pages anyway
        (3, 2, 2, True),
        (3, 2, 1, False),  # rule 2: diagrams push a one-page song onto two
        (8, 2, 1, False),  # rule 2 applies at 8 too
        (3, 1, 1, True),
        (0, 1, 1, True),
    ],
)
def test_show_diagrams_rules(
    diagrams: int, pages_with: int, pages_without: int, expected: bool
) -> None:
    assert show_diagrams(diagrams, pages_with, pages_without) is expected


def test_chords_with_the_same_fingering_share_one_diagram() -> None:
    diagrams = group_diagrams(["Am", "Am/C", "G", "Am/E"])
    assert len(diagrams) == 2
    assert diagrams[0].names == ("Am", "Am/C", "Am/E")
    assert diagrams[1].names == ("G",)
    assert diagrams[0].frets == shape("Am")


def test_diagrams_are_in_order_of_first_use() -> None:
    diagrams = group_diagrams(["G", "Am", "G", "C"])
    assert [d.names for d in diagrams] == [("G",), ("Am",), ("C",)]


def test_sharps_and_flats_share_a_diagram() -> None:
    assert len(group_diagrams(["F#", "Gb"])) == 1


def test_chords_without_a_shape_are_left_out() -> None:
    assert group_diagrams(["Xyz"]) == []
    assert [d.names for d in group_diagrams(["Xyz", "G"])] == [("G",)]


def test_shared_diagrams_count_once_when_applying_the_rules() -> None:
    # O Little Town's nine chord names are eight distinct fingerings.
    names = ["D", "G", "A7", "B7", "Em", "A", "Bm", "F#", "D/A"]
    diagrams = group_diagrams(names)
    assert len(diagrams) == 8
    assert show_diagrams(len(diagrams), 2, 2) is True


def test_shape_is_frets_for_strings_g_c_e_a() -> None:
    assert shape("C") == (0, 0, 0, 3)


def test_slash_chords_use_the_base_shape() -> None:
    assert shape("D/A") == shape("D")


def test_sharps_and_flats_are_interchangeable() -> None:
    assert shape("Gb") == shape("F#") is not None


def test_unknown_chord_has_no_shape() -> None:
    assert shape("Xyz7b13") is None
