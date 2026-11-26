"""The command-line interface: `strumbook build`."""

import argparse
import sys
from collections.abc import Sequence
from datetime import date
from importlib.metadata import version
from pathlib import Path

from strumbook.book import BuildError, read_book


def _url(value: str) -> str:
    if not value.startswith(("https://", "http://")):
        raise argparse.ArgumentTypeError(f"not a web address: {value!r}")
    return value


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
        help="build a tablet songbook PDF from a folder of ChordPro songs",
        description="Build a tablet songbook PDF from the .cho files in a folder.",
    )
    build.add_argument("songs_dir", type=Path, metavar="SONGS_DIR")
    build.add_argument("-o", "--output", type=Path, required=True, metavar="BOOK.pdf")
    build.add_argument("--title", help="the book's title (default: the folder's name)")
    today = date.today()
    built = f"{today.day} {today:%B %Y}"
    build.add_argument(
        "--edition",
        default=built,
        help="the edition line on the title page (default: today's date)",
    )
    build.add_argument(
        "--source",
        type=_url,
        metavar="URL",
        help="where the songs come from, linked in Credits",
    )
    build.add_argument(
        "--title-page",
        choices=["on", "off"],
        default="on",
        help="include the title page (default on)",
    )
    build.add_argument(
        "--credits",
        choices=["on", "off"],
        default="on",
        help="include Credits (default on)",
    )
    build.add_argument(
        "--mid-word-chords",
        choices=["inline", "above"],
        default="inline",
        help="draw a chord inside a word inline (default), or above the word so "
        "search finds the whole word",
    )
    build.add_argument(
        "--pdf-tags",
        choices=["on", "off"],
        default="on",
        help="tag the PDF for screen readers (default on); off makes it smaller",
    )
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    # Imported here so that --help works without the renderer.
    from strumbook.render import render

    try:
        book = read_book(args.songs_dir, args.title)
        for warning in book.warnings:
            print(f"warning: {warning}", file=sys.stderr)
        render(
            book,
            args.output,
            mid_word=args.mid_word_chords,
            pdf_tags=args.pdf_tags == "on",
            edition=args.edition,
            built=built,
            source=args.source,
            title_page=args.title_page == "on",
            credits=args.credits == "on",
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
