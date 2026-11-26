"""Book files: a TOML recipe for one book, naming its sources, songs and settings.

See docs/book-files.md for the format.
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from strumbook.book import Book, BuildError, make_book, song_files
from strumbook.sources import fetch

# Each style's defaults for the [build] settings; the first layer of three.
STYLES = {
    "songbook": {
        "title-page": True,
        "credits": True,
        "mid-word-chords": "inline",
        "pdf-tags": True,
    },
}
CHOICES = {"mid-word-chords": ("inline", "above")}

_BOOK_KEYS = {"title", "style", "edition", "subtitle", "notes"}
_SOURCE_KEYS = {"path", "git", "pin", "folder", "link"}
_SONGS_KEYS = {"include", "pick", "exclude", "order"}
_NAME = re.compile(r"[a-z0-9-]+")


@dataclass(frozen=True)
class BookFile:
    book: Book
    style: str
    edition: str | None
    build: dict[str, object]  # the [build] settings, checked


def read_book_file(path: Path) -> BookFile:
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        raise BuildError(f"{path.name} isn't UTF-8 text") from None
    except OSError as e:
        raise BuildError(f"can't read {path}: {e.strerror}") from None
    except tomllib.TOMLDecodeError as e:
        raise BuildError(f"{path.name} isn't valid TOML: {e}") from None

    warnings = _unknown(data, {"book", "sources", "songs", "build"}, "")
    book = _table(data, "book")
    warnings += _unknown(book, _BOOK_KEYS, "[book]")
    title = _text(book, "title", "[book]")
    if not title:
        raise BuildError('the book file needs a title: add title = "…" under [book]')
    style = _text(book, "style", "[book]") or "songbook"
    if style not in STYLES:
        raise BuildError(f"unknown style {style!r}: use {_either(STYLES)}")

    build = _table(data, "build")
    warnings += _unknown(build, set(STYLES["songbook"]), "[build]")
    build = {k: v for k, v in build.items() if k in STYLES["songbook"]}
    for key, value in build.items():
        expected = CHOICES.get(key)
        if expected is None and not isinstance(value, bool):
            raise BuildError(f"[build] {key} must be true or false")
        if expected is not None and value not in expected:
            raise BuildError(f"[build] {key} must be {_either(expected)}")

    sources = _table(data, "sources")
    if not sources:
        raise BuildError("the book file has no [sources.<name>] tables")
    folders, links = {}, []
    for name, source in sources.items():
        if not _NAME.fullmatch(name) or not isinstance(source, dict):
            raise BuildError(
                f"[sources.{name}] needs a name of lower case letters, digits and "
                "hyphens, and a table of settings"
            )
        folder, link, more = _source(name, source, path.parent)
        folders[name] = folder
        warnings += more
        if link:
            links.append(link)

    songs = _table(data, "songs")
    warnings += _unknown(songs, _SONGS_KEYS, "[songs]")
    order = _text(songs, "order", "[songs]") or "a-z"
    if order not in ("a-z", "listed"):
        raise BuildError('[songs] order must be "a-z" or "listed"')
    include = songs.get("include", [])
    if include == "all":
        include = list(folders)
    include = _list(include, "include")
    for name in include:
        if name not in folders:
            raise BuildError(f"[songs] include names unknown source {name!r}")
    picked = [
        _song(ref, folders, "pick") for ref in _list(songs.get("pick", []), "pick")
    ]
    excluded = {
        _song(ref, folders, "exclude")
        for ref in _list(songs.get("exclude", []), "exclude")
    }

    included = [p for name in include for p in song_files(folders[name])]
    chosen = list(dict.fromkeys(p for p in picked + included if p not in excluded))
    if not chosen:
        raise BuildError(
            "the book file chooses no songs: add include or pick under [songs]"
        )
    return BookFile(
        book=make_book(
            title,
            chosen,
            a_to_z=order == "a-z",
            subtitle=_text(book, "subtitle", "[book]"),
            notes=_text(book, "notes", "[book]"),
            sources=tuple(links),
            warnings=tuple(warnings),
        ),
        style=style,
        edition=_text(book, "edition", "[book]") or None,
        build=build,
    )


def _source(name: str, source: dict, base: Path) -> tuple[Path, str, list[str]]:
    """The songs folder for one source, the link for Credits, and warnings."""
    where = f"[sources.{name}]"
    warnings = _unknown(source, _SOURCE_KEYS, where)
    local, url = _text(source, "path", where), _text(source, "git", where)
    pin, link = _text(source, "pin", where), _text(source, "link", where)
    if bool(local) == bool(url):
        raise BuildError(f"{where} needs either path or git")
    if pin and not url:
        raise BuildError(f"{where} has a pin, but pins are for git sources")
    if "link" in source and not link.startswith(("https://", "http://")):
        raise BuildError(f"{where} link {link!r} isn't a web address")
    if url:
        root, more = fetch(name, url, pin or None)
        warnings += more
    else:
        root = (base / Path(local).expanduser()).resolve()
        if not root.is_dir():
            raise BuildError(f"{where} path: no such folder: {root}")
    sub = _text(source, "folder", where)
    folder = (
        root / sub if sub else root / "songs" if (root / "songs").is_dir() else root
    )
    if not song_files(folder):
        raise BuildError(f"source {name!r} has no songs: no .cho files in {folder}")
    return folder, link or url, warnings


def _song(ref: object, folders: dict[str, Path], key: str) -> Path:
    if not isinstance(ref, str) or ":" not in ref:
        raise BuildError(f'[songs] {key}: {ref!r} isn\'t "source:file name"')
    name, stem = ref.split(":", 1)
    if name not in folders:
        raise BuildError(f"[songs] {key}: {ref!r} names unknown source {name!r}")
    path = folders[name] / f"{stem}.cho"
    if not path.is_file():
        raise BuildError(f"[songs] {key}: no song {stem!r} in source {name!r}")
    return path


def _table(data: dict, key: str) -> dict:
    value = data.get(key, {})
    if not isinstance(value, dict):
        raise BuildError(f"{key} must be a table: [{key}]")
    return value


def _text(table: dict, key: str, where: str) -> str:
    value = table.get(key, "")
    if not isinstance(value, str):
        raise BuildError(f'{where} {key} must be text in quotes: {key} = "…"')
    return value.strip()


def _list(value: object, key: str) -> list:
    if not isinstance(value, list):
        raise BuildError(f'[songs] {key} must be a list: {key} = ["…"]')
    return value


def _unknown(table: dict, known: set[str], where: str) -> list[str]:
    return [
        f"unknown key {where + ' ' if where else ''}{key} ignored"
        for key in table
        if key not in known
    ]


def _either(options) -> str:
    return " or ".join(f'"{o}"' for o in options)
