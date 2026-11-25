"""The initial command-line interface; songbook generation is not implemented."""

import argparse
from collections.abc import Sequence
from importlib.metadata import version


def main(argv: Sequence[str] | None = None) -> int:
    """Show help or the installed version; reject unsupported commands."""
    parser = argparse.ArgumentParser(
        prog="strumbook",
        description="Build songbooks for ukulele groups from ChordPro collections.",
        epilog="Development scaffold only: songbook generation is not implemented yet.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {version('strumbook')}"
    )
    parser.parse_args(argv)
    parser.print_help()
    return 0
