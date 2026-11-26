"""Book files: a TOML recipe for one book, naming its sources, songs and settings.

See docs/book-files.md for the format.
"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from strumbook.book import Book, BuildError, Section, make_book, song_files
from strumbook.sources import fetch

# Each style's defaults for the [build] settings; the first layer of three.
# set-breaks None means: on when a set list has more than one set, or spares.
STYLES = {
    "songbook": {
        "title-page": True,
        "index": True,
        "navigation": True,
        "reference": True,
        "credits": True,
        "set-breaks": False,
        "mid-word-chords": "inline",
        "pdf-tags": True,
    },
    "setlist": {
        "title-page": True,
        "index": False,
        "navigation": False,
        "reference": False,
        "credits": False,
        "set-breaks": None,
        "mid-word-chords": "inline",
        "pdf-tags": True,
    },
}
CHOICES = {"mid-word-chords": ("inline", "above")}

_BOOK_KEYS = {"title", "style", "edition", "subtitle", "notes"}
_SOURCE_KEYS = {"path", "git", "pin", "folder", "link"}
_SONGS_KEYS = {"include", "pick", "exclude", "order", "set", "spares"}
_SET_KEYS = {"name", "songs", "running-time", "notes"}
SPARES = "Spares and encores"
_NAME = re.compile(r"[a-z0-9-]+")


@dataclass(frozen=True)
class BookFile:
    book: Book
    style: str
    edition: str | None
    build: dict[str, object]  # the [build] settings, checked


def read_book_file(path: Path, style: str | None = None) -> BookFile:
    """Read a book file; `style`, from the command line, overrides the file's."""
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
    style = style or _text(book, "style", "[book]") or "songbook"
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
    folders, links, pins = {}, [], {}
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
        # Sources sharing an address share one checkout, so they must agree on its pin.
        url, pin = source.get("git"), source.get("pin")
        if url and pins.setdefault(url, pin) != pin:
            raise BuildError(f"git address {url} has different pins: use one pin")

    songs = _table(data, "songs")
    warnings += _unknown(songs, _SONGS_KEYS, "[songs]")
    if style == "setlist":
        chosen, sections = _setlist(songs, folders, warnings)
    else:
        chosen, sections = _songbook(songs, folders, warnings), ()
    return BookFile(
        book=make_book(
            title,
            chosen,
            a_to_z=_text(songs, "order", "[songs]") in ("", "a-z") and not sections,
            subtitle=_text(book, "subtitle", "[book]"),
            notes=_text(book, "notes", "[book]"),
            sources=tuple(dict.fromkeys(links)),
            sections=sections,
            warnings=tuple(warnings),
        ),
        style=style,
        edition=_text(book, "edition", "[book]") or None,
        build=build,
    )


def _songbook(songs: dict, folders: dict[str, Path], warnings: list[str]) -> list[Path]:
    """The songs `include`, `pick` and `exclude` choose."""
    for key in ("set", "spares"):
        if key in songs:
            raise BuildError(
                f"[songs] {key} is for set lists, but this book is building as a "
                'songbook: use style = "setlist"'
            )
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
    picked = []
    for ref in _list(songs.get("pick", []), "pick"):
        song, missing = _song(ref, folders, "pick")
        if missing:
            raise BuildError(missing)
        picked.append(song)
    excluded = set()
    for ref in _list(songs.get("exclude", []), "exclude"):
        # A warning, not an error: a collection that tracks the latest may drop it.
        song, missing = _song(ref, folders, "exclude")
        if missing:
            warnings.append(missing)
        excluded.add(song)

    included = [p for name in include for p in song_files(folders[name])]
    chosen = list(dict.fromkeys(p for p in picked + included if p not in excluded))
    if not chosen:
        raise BuildError(
            "the book file chooses no songs: add include or pick under [songs]"
        )
    return chosen


def _setlist(
    songs: dict, folders: dict[str, Path], warnings: list[str]
) -> tuple[list[Path], tuple[Section, ...]]:
    """The songs in running order, from [[songs.set]] or `pick`, then `spares`."""
    for key in ("include", "exclude"):
        if key in songs:
            raise BuildError(
                f"[songs] {key} isn't for set lists: choose songs with [[songs.set]] "
                "or pick"
            )
    if _text(songs, "order", "[songs]") not in ("", "listed"):
        raise BuildError(
            '[songs] order in a set list can only be "listed" (or left out): '
            'set lists keep their running order, so not "a-z"'
        )
    sets = songs.get("set", [])
    if not isinstance(sets, list) or not all(isinstance(s, dict) for s in sets):
        raise BuildError("[songs] set must be [[songs.set]] tables")
    if sets and "pick" in songs:
        raise BuildError("use [[songs.set]] or [songs] pick in a set list, not both")
    groups = []
    for n, table in enumerate(sets, 1):
        where = f"[[songs.set]] number {n}"
        warnings += _unknown(table, _SET_KEYS, where)
        name = _text(table, "name", where)
        if not name:
            raise BuildError(f'{where} needs a name: name = "…"')
        refs = _list(table.get("songs", []), f"set {name!r} songs")
        if not refs:
            raise BuildError(f'set {name!r} has no songs: songs = ["…"]')
        time = _text(table, "running-time", where)
        notes = _text(table, "notes", where)
        groups.append((Section(name, len(refs), time, notes), refs, f"set {name!r}"))
    if picked := _list(songs.get("pick", []), "pick"):
        groups.append((Section("", len(picked)), picked, "pick"))
    if spares := _list(songs.get("spares", []), "spares"):
        groups.append((Section(SPARES, len(spares)), spares, "spares"))
    chosen: list[Path] = []
    for _, refs, key in groups:
        for ref in refs:
            song, missing = _song(ref, folders, key)
            if missing:
                raise BuildError(missing)
            if song in chosen:
                raise BuildError(
                    f"{ref!r} is in the set list twice: a song can be in only one "
                    "set or in spares"
                )
            chosen.append(song)
    if not chosen:
        raise BuildError("the set list has no songs: add [[songs.set]] tables")
    return chosen, tuple(section for section, _, _ in groups)


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
        root = base / Path(local).expanduser()
        if not root.is_dir():
            raise BuildError(f"{where} path: no such folder: {root.resolve()}")
    root = root.resolve()
    sub = _text(source, "folder", where)
    folder = (root / sub).resolve() if sub else root / "songs"
    if not sub and not folder.is_dir():
        folder = root
    if not folder.is_relative_to(root):
        raise BuildError(f"{where} folder {sub!r} is outside the source")
    if not song_files(folder):
        raise BuildError(f"source {name!r} has no songs: no .cho files in {folder}")
    return folder, link or url, warnings


def _song(ref: object, folders: dict[str, Path], key: str) -> tuple[Path | None, str]:
    """The song file `ref` names, matched exactly, or None and why not."""
    if not isinstance(ref, str) or ":" not in ref:
        raise BuildError(f'[songs] {key}: {ref!r} isn\'t "source:file name"')
    name, stem = ref.split(":", 1)
    if name not in folders:
        raise BuildError(f"[songs] {key}: {ref!r} names unknown source {name!r}")
    songs = {p.stem: p for p in song_files(folders[name])}
    if stem in songs:
        return songs[stem], ""
    near = [s for s in songs if s.casefold() == stem.casefold()]
    hint = f" (did you mean {near[0]!r}?)" if near else ""
    return None, f"[songs] {key}: no song {stem!r} in source {name!r}{hint}"


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
        raise BuildError(f'[songs] {key} must be a list, in square brackets: ["…"]')
    return value


def _unknown(table: dict, known: set[str], where: str) -> list[str]:
    return [
        f"unknown key {where + ' ' if where else ''}{key} ignored"
        for key in table
        if key not in known
    ]


def _either(options) -> str:
    return " or ".join(f'"{o}"' for o in options)
