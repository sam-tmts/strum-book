"""The command-line interface: `strumbook build`."""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from importlib.metadata import version
from pathlib import Path

from strumbook.book import BuildError, read_book
from strumbook.bookfile import CHOICES, TYPES, BookFile, read_book_file
from strumbook.chords import tuning

_ON_OFF = {"on": True, "off": False}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="strumbook",
        description="Build songbooks for ukulele groups from ChordPro collections.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('strumbook')}"
    )
    commands = parser.add_subparsers(dest="command", title="commands")
    build = commands.add_parser(
        "build",
        help="build a tablet songbook PDF from a StrumBook file or a folder of songs",
        description="Build a tablet songbook PDF from a StrumBook file "
        "(.strumbook.toml), or "
        "from every .cho file in a folder. Options given here override the StrumBook "
        "file's [build] settings.",
    )
    build.add_argument("book", type=Path, metavar="BOOK.strumbook.toml|SONGS_DIR")
    build.add_argument("-o", "--output", type=Path, required=True, metavar="BOOK.pdf")
    build.add_argument(
        "--title",
        help="the book's title (default: the StrumBook file's title, or the folder's name)",
    )
    build.add_argument(
        "--edition", help="the edition line on the title page (default: today's date)"
    )
    build.add_argument(
        "--type",
        choices=list(TYPES),
        help="song-library (A to Z, the default) or set-list (a gig's running "
        "order); the defaults below are for song-library",
    )
    for option, what, default in [
        ("title-page", "the title page", "on"),
        ("chords", "chord diagrams on song pages", "on; set-list off"),
        ("index", "the index", "on; set-list off"),
        ("navigation", "the strip of links along the bottom", "on; set-list off"),
        (
            "reference",
            "the Reference pages: chord shapes and notes",
            "on; set-list off",
        ),
        ("reference-notes", "the notes in each chord, in Reference", "on"),
        ("credits", "Credits", "on; set-list off"),
        ("set-breaks", "a page before each set", "set-list: on for 2+ sets or spares"),
    ]:
        build.add_argument(
            f"--{option}", choices=_ON_OFF, help=f"include {what} (default {default})"
        )
    build.add_argument(
        "--mid-word-chords",
        choices=CHOICES["mid-word-chords"],
        help="draw a chord inside a word inline (default), or above the word so "
        "search finds the whole word",
    )
    build.add_argument(
        "--tuning",
        type=lambda value: tuning(value) or value,
        choices=CHOICES["tuning"],
        help="the chord shapes: GCEA or ukulele (the default), or DGBE or baritone, "
        "in any case",
    )
    build.add_argument(
        "--slash-chords",
        choices=CHOICES["slash-chords"],
        help="simplify (Am/C prints as Am when the bass is already in the chord) or "
        "as-written (default: simplify for GCEA, as-written for DGBE)",
    )
    build.add_argument(
        "--pdf-tags",
        choices=_ON_OFF,
        help="tag the PDF for screen readers (default on); off makes it smaller",
    )
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    # Imported here so that --help works without the renderer.
    from strumbook.render import render

    today = date.today()
    built = f"{today.day} {today:%B %Y}"
    try:
        if args.book.is_file() or args.book.suffix == ".toml":
            recipe = read_book_file(args.book, args.type)
        elif args.type == "set-list":
            raise BuildError("the set-list type needs a StrumBook file with sets")
        else:  # the shortcut: every song in one folder
            recipe = BookFile(read_book(args.book), "song-library", None, {})
        book = recipe.book
        if args.title is not None:
            book = replace(book, title=args.title)
        # Settings layers: the type's defaults, the StrumBook file's [build], then
        # options given here.
        given = {
            key: _ON_OFF.get(value, value)
            for key in TYPES["song-library"]
            if (value := getattr(args, key.replace("-", "_"))) is not None
        }
        settings = {**TYPES[recipe.type], **recipe.build, **given}
        # A book without diagrams doesn't need to hear which chords have none.
        shown = [
            w
            for w in book.warnings
            if settings["chords"] or w not in book.missing_diagrams
        ]
        for warning in shown:
            print(f"warning: {warning}", file=sys.stderr)
        edition = args.edition or recipe.edition or built
        render(
            book,
            args.output,
            settings,
            kind=recipe.type,
            edition=edition,
            built=built,
        )
    except BuildError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    songs, warnings = len(book.songs), len(shown)
    print(
        f"Wrote {args.output}: {songs} song{'s' if songs != 1 else ''}, "
        f"{warnings} warning{'s' if warnings != 1 else ''}"
    )
    return 0
