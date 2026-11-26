"""The command-line interface: `strumbook build`."""

import argparse
import sys
from collections.abc import Sequence
from dataclasses import replace
from datetime import date
from importlib.metadata import version
from pathlib import Path

from strumbook.book import BuildError, read_book
from strumbook.bookfile import CHOICES, STYLES, BookFile, read_book_file

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
        help="build a tablet songbook PDF from a book file or a folder of songs",
        description="Build a tablet songbook PDF from a book file (.book.toml), or "
        "from every .cho file in a folder. Options given here override the book "
        "file's [build] settings.",
    )
    build.add_argument("book", type=Path, metavar="BOOK.book.toml|SONGS_DIR")
    build.add_argument("-o", "--output", type=Path, required=True, metavar="BOOK.pdf")
    build.add_argument(
        "--title",
        help="the book's title (default: the book file's title, or the folder's name)",
    )
    build.add_argument(
        "--edition", help="the edition line on the title page (default: today's date)"
    )
    build.add_argument(
        "--style", choices=list(STYLES), help="the book's style (default: songbook)"
    )
    build.add_argument(
        "--title-page", choices=_ON_OFF, help="include the title page (default on)"
    )
    build.add_argument(
        "--credits", choices=_ON_OFF, help="include Credits (default on)"
    )
    build.add_argument(
        "--mid-word-chords",
        choices=CHOICES["mid-word-chords"],
        help="draw a chord inside a word inline (default), or above the word so "
        "search finds the whole word",
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
            recipe = read_book_file(args.book)
        else:  # the shortcut: every song in one folder
            recipe = BookFile(read_book(args.book), "songbook", None, {})
        book = recipe.book
        if args.title is not None:
            book = replace(book, title=args.title)
        # Settings layers: the style's defaults, the book file's [build], then
        # options given here.
        given = {
            key: _ON_OFF.get(value, value)
            for key in STYLES["songbook"]
            if (value := getattr(args, key.replace("-", "_"))) is not None
        }
        settings = {**STYLES[args.style or recipe.style], **recipe.build, **given}
        for warning in book.warnings:
            print(f"warning: {warning}", file=sys.stderr)
        render(
            book,
            args.output,
            mid_word=settings["mid-word-chords"],
            pdf_tags=settings["pdf-tags"],
            edition=args.edition or recipe.edition or built,
            built=built,
            title_page=settings["title-page"],
            credits=settings["credits"],
        )
    except BuildError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    songs, warnings = len(book.songs), len(book.warnings)
    print(
        f"Wrote {args.output}: {songs} song{'s' if songs != 1 else ''}, "
        f"{warnings} warning{'s' if warnings != 1 else ''}"
    )
    return 0
