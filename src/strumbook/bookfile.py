"""StrumBook files: a TOML recipe for one book, naming its sources, songs and settings.

See docs/strumbook-files.md for the format.
"""

import json
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

from strumbook.book import Book, BuildError, Section, make_book, song_files
from strumbook.sources import SIGN_IN, fetch

# Each type's defaults for the [build] settings; the first layer of three.
# set-breaks None means: on when a set list has more than one set, or spares.
TYPES = {
    "song-library": {
        "title-page": True,
        "index": True,
        "navigation": True,
        "reference": True,
        "credits": True,
        "set-breaks": False,
        "mid-word-chords": "inline",
        "pdf-tags": True,
    },
    "set-list": {
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

_BOOK_KEYS = {"title", "type", "edition", "subtitle", "notes"}
_SOURCE_KEYS = {"path", "git", "pin", "folder", "link"}
_SONGS_KEYS = {"include", "pick", "exclude", "set", "spares"}
_SET_KEYS = {"name", "songs", "running-time", "notes"}
SPARES = "Spares and encores"
_NAME = re.compile(r"[a-z0-9-]+")
_DOCS = "https://github.com/sam-tmts/strumbook/blob/main/docs/strumbook-files.md"
# Where tomllib says it stopped: the end of its message on Python 3.12, which has no
# lineno attribute. No line or column means the end of the file.
_AT = re.compile(r"\s*\(at (?:line (\d+), column (\d+)|end of document)\)$")
# Likely slips on the line tomllib stopped at, each matching a key and a value.
_CHORDPRO = re.compile(r"\{\s*([\w-]+)\s*:\s*(.*?)\s*\}")  # {title: Carols}
_COLON = re.compile(r"([\w-]+)\s*:\s*(.*)")  # title: Carols
_UNQUOTED = re.compile(r"([\w-]+)\s*=\s*([^\s\"'\[{].*)")  # title = Carols
# [build] settings that are true or false, written on or off on the command line.
_ON_OFF = {k for k, v in TYPES["song-library"].items() if isinstance(v, bool)}


@dataclass(frozen=True)
class BookFile:
    book: Book
    type: str
    edition: str | None
    build: dict[str, object]  # the [build] settings, checked


def read_book_file(path: Path, kind: str | None = None) -> BookFile:
    """Read a StrumBook file; `kind`, a type from the command line, overrides its own."""
    try:
        text = path.read_text(encoding="utf-8-sig")
        data = tomllib.loads(text)
    except UnicodeDecodeError:
        raise BuildError(f"{path.name} isn't UTF-8 text") from None
    except OSError as e:
        raise BuildError(f"can't read {path}: {e.strerror}") from None
    except tomllib.TOMLDecodeError as e:
        raise BuildError(_toml_error(path.name, text, e)) from None

    warnings = _unknown(data, {"book", "sources", "songs", "build"}, "")
    book = _table(data, "book")
    warnings += _unknown(book, _BOOK_KEYS, "[book]")
    title = _text(book, "title", "[book]")
    if not title:
        raise BuildError(
            'the StrumBook file needs a title: add title = "…" under [book]'
        )
    kind = kind or _text(book, "type", "[book]") or "song-library"
    if kind not in TYPES:
        raise BuildError(f"unknown type {kind!r}: use {_either(TYPES)}")

    build = _table(data, "build")
    warnings += _unknown(build, set(TYPES["song-library"]), "[build]")
    build = {k: v for k, v in build.items() if k in TYPES["song-library"]}
    for key, value in build.items():
        expected = CHOICES.get(key)
        if expected is None and not isinstance(value, bool):
            raise BuildError(f"[build] {key} must be true or false")
        if expected is not None and value not in expected:
            raise BuildError(f"[build] {key} must be {_either(expected)}")

    sources = _table(data, "sources")
    if not sources:
        raise BuildError("the StrumBook file has no [sources.<name>] tables")
    folders, credits, pins = {}, [], {}
    for name, source in sources.items():
        if not _NAME.fullmatch(name) or not isinstance(source, dict):
            raise BuildError(
                f"[sources.{name}] needs a name of lower case letters, digits and "
                "hyphens, and a table of settings"
            )
        folder, link, more = _source(name, source, path.parent)
        folders[name] = folder
        warnings += more
        credits.append((name, link))
        # Sources sharing an address share one checkout, so they must agree on its pin.
        url, pin = source.get("git"), source.get("pin")
        if url and pins.setdefault(url, pin) != pin:
            raise BuildError(f"git address {url} has different pins: use one pin")

    songs = _table(data, "songs")
    warnings += _unknown(songs, _SONGS_KEYS, "[songs]")
    if kind == "set-list":
        chosen, sections = _set_list(songs, folders, warnings)
    else:
        chosen, sections = _song_library(songs, folders, warnings), ()
    return BookFile(
        book=make_book(
            title,
            chosen,
            subtitle=_text(book, "subtitle", "[book]"),
            notes=_text(book, "notes", "[book]"),
            sources=tuple(credits),
            sections=sections,
            warnings=tuple(warnings),
        ),
        type=kind,
        edition=_text(book, "edition", "[book]") or None,
        build=build,
    )


def _song_library(
    songs: dict, folders: dict[str, Path], warnings: list[str]
) -> list[Path]:
    """The songs `include`, `pick` and `exclude` choose."""
    for key in ("set", "spares"):
        if key in songs:
            raise BuildError(
                f"[songs] {key} is for set lists, but this book is building as a "
                'song library: use type = "set-list"'
            )
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
            "the StrumBook file chooses no songs: add include or pick under [songs]"
        )
    return chosen


def _set_list(
    songs: dict, folders: dict[str, Path], warnings: list[str]
) -> tuple[list[Path], tuple[Section, ...]]:
    """The songs in running order, from [[songs.set]] or `pick`, then `spares`."""
    for key in ("include", "exclude"):
        if key in songs:
            raise BuildError(
                f"[songs] {key} isn't for set lists: choose songs with [[songs.set]] "
                "or pick"
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
    """The songs folder for one source, its link for Credits (or ""), and warnings."""
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
    return folder, link, warnings


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


def _toml_error(name: str, text: str, error: tomllib.TOMLDecodeError) -> str:
    """What went wrong in a StrumBook file that isn't valid TOML, where, and how to
    write it, with help for the likeliest slips from ChordPro."""
    at = _AT.search(str(error))
    if at is None:  # not expected, but never hide what tomllib said
        return f"{name} isn't valid TOML: {error}"
    problem = str(error)[: at.start()]
    problem = f"this isn't valid TOML ({problem[:1].lower() + problem[1:]})"
    docs = f"see how to write a StrumBook file at {_DOCS}"
    if at[1] is None:
        return (
            f"{name}, at the end of the file: {problem}; look for a missing ] or "
            f"closing quotes, and {docs}"
        )
    number, column = int(at[1]), int(at[2])
    lines = text.split("\n")  # as tomllib counts them
    found = lines[number - 1].strip() if number <= len(lines) else ""
    if SIGN_IN.search(found):  # don't print it: it may hold a password or token
        return (
            f"{name}, line {number}: a git address can't hold sign-in details: leave "
            "them to git's own sign-in"
        )
    if advice := _slip_advice(found):
        return f"{name}, line {number}: {advice}"
    return f"{name}, line {number}, column {column}: {problem}; {docs}"


def _slip_advice(found: str) -> str | None:
    """How to write `found` in TOML, if it's one of the likeliest slips."""
    if match := _CHORDPRO.fullmatch(found):
        key, value = match.groups()
        under = " under [book]" if key in _BOOK_KEYS else ""
        return (
            f"{found!r} is how a ChordPro song writes it; in a StrumBook file, "
            f"write {_toml_form(key, value)}{under}"
        )
    if match := _COLON.fullmatch(found):
        return f"{found!r} needs an equals sign: write {_toml_form(*match.groups())}"
    if match := _UNQUOTED.fullmatch(found):
        key, value = match.groups()
        form = _toml_form(key, value)
        if form.endswith('"'):
            return f"{found!r} needs quotes around the text: write {form}"
        if form != f"{key} = {value.strip()}":
            return f"{found!r} needs true or false, not on or off: write {form}"
    return None  # a value TOML can read, so the slip is elsewhere: a repeated key


def _toml_form(key: str, value: str) -> str:
    """`key = value` in TOML: on and off for a [build] setting become true and
    false, a value TOML can already read stays as written, and anything else is text
    in quotes."""
    value = value.strip()
    if key in _ON_OFF and value.lower() in ("on", "off"):
        return f"{key} = {str(value.lower() == 'on').lower()}"
    try:
        tomllib.loads(f"v = {value}")
    except tomllib.TOMLDecodeError:
        value = json.dumps(value, ensure_ascii=False)
    return f"{key} = {value}"


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
