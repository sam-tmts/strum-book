"""Helpers for building from StrumBook files, and a local bare git repo standing in for
GitHub. Songs are the public-domain fixture carols or synthetic."""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from pdf_helpers import FIXTURES, split_links
from pypdf import PdfReader

from strumbook.cli import main

CAROLS = [
    "Away In A Manger",
    "O Come, O Come, Emmanuel",
    "O Little Town Of Bethlehem",
]
AWAY = "carols:Away In A Manger"
EMMANUEL = "carols:O Come O Come Emmanuel"
BETHLEHEM = "carols:O Little Town Of Bethlehem"
CAROLS_SOURCE = f"[sources.carols]\npath = '{FIXTURES}'\n"
FULL_BOOK = ["Title", "Index", *CAROLS, "Reference", "Credits"]
ADDRESS = "https://example.test/carols.git"


def write_book(
    tmp_path: Path,
    *,
    sources: str = CAROLS_SOURCE,
    songs: str = 'include = "all"',
    book: str = "",
    build: str = "",
    title: str = "Test Book",
    name: str = "test.strumbook.toml",
) -> Path:
    """Write a StrumBook file into <tmp_path>/books/ and return its path."""
    folder = tmp_path / "books"
    folder.mkdir(exist_ok=True)
    text = f'[book]\ntitle = "{title}"\n{book}\n{sources}\n[songs]\n{songs}\n'
    if build:
        text += f"\n[build]\n{build}\n"
    path = folder / name
    path.write_text(text, encoding="utf-8")
    return path


def write_songs(folder: Path, songs: dict[str, str]) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    for name, body in songs.items():
        (folder / f"{name}.cho").write_text(body, encoding="utf-8")
    return folder


def run(
    target: Path, out: Path, *options: str, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str]:
    """Run `strumbook build TARGET -o OUT` and return (exit code, stderr)."""
    code = main(["build", str(target), "-o", str(out), *options])
    return code, capsys.readouterr().err


def built(
    target: Path, out: Path, *options: str, capsys: pytest.CaptureFixture[str]
) -> PdfReader:
    code, err = run(target, out, *options, capsys=capsys)
    assert code == 0, err
    return PdfReader(out)


def error_lines(err: str) -> list[str]:
    return [line for line in err.splitlines() if line.startswith("error: ")]


def assert_clean_error(code: int, err: str, out: Path, *needles: str) -> None:
    """One `error: ` line naming the problem, exit 1, no traceback, no PDF."""
    assert code == 1, err
    errors = error_lines(err)
    assert len(errors) == 1, err
    assert "Traceback" not in err
    assert not out.exists()
    for needle in needles:
        assert needle in errors[0], err


def warning_lines(err: str) -> list[str]:
    return [line for line in err.splitlines() if line.startswith("warning: ")]


def page_text(reader: PdfReader, pages: range) -> str:
    return re.sub(r"\s+", " ", " ".join(reader.pages[n].extract_text() for n in pages))


def index_targets(reader: PdfReader, index_page: int) -> list[int]:
    """Where the index entries on a page go, top to bottom."""
    _, entries = split_links(reader, index_page)
    entries.sort(key=lambda link: -link.rect[3])
    return [link.target for link in entries]


def uris(reader: PdfReader) -> set[str]:
    found = set()
    for page in reader.pages:
        for ref in page.get("/Annots", []):
            action = ref.get_object().get("/A")
            if action is not None and "/URI" in action.get_object():
                found.add(str(action.get_object()["/URI"]))
    return found


def annotation_count(reader: PdfReader, uri: str) -> int:
    """How many link annotations in the book go to this web address."""
    count = 0
    for page in reader.pages:
        for ref in page.get("/Annots", []):
            action = ref.get_object().get("/A")
            if action is not None and str(action.get_object().get("/URI")) == uri:
                count += 1
    return count


# A local bare repo that stands in for GitHub.

_IDENTITY = {
    "GIT_AUTHOR_NAME": "Test Author",
    "GIT_AUTHOR_EMAIL": "author@example.test",
    "GIT_COMMITTER_NAME": "Test Author",
    "GIT_COMMITTER_EMAIL": "author@example.test",
}


def _git(cwd: Path, *args: str) -> str:
    env = {**os.environ, **_IDENTITY, "GIT_CONFIG_NOSYSTEM": "1"}
    result = subprocess.run(
        ["git", "-C", str(cwd), *args],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


@dataclass
class Remote:
    root: Path

    @property
    def bare(self) -> Path:
        return self.root / "remote.git"

    @property
    def work(self) -> Path:
        return self.root / "work"

    @classmethod
    def create(cls, root: Path) -> "Remote":
        remote = cls(root)
        root.mkdir(parents=True, exist_ok=True)
        _git(root, "init", "--quiet", "--bare", "-b", "main", str(remote.bare))
        _git(root, "init", "--quiet", "-b", "main", str(remote.work))
        _git(remote.work, "remote", "add", "origin", str(remote.bare))
        return remote

    def commit(self, files: dict[str, str | Path], folder: str = "") -> str:
        """Add files (text, or a path to copy) and push. Returns the commit hash."""
        target = self.work / folder
        target.mkdir(parents=True, exist_ok=True)
        for name, content in files.items():
            if isinstance(content, Path):
                shutil.copy(content, target / name)
            else:
                (target / name).write_text(content, encoding="utf-8")
        _git(self.work, "add", "--all")
        _git(self.work, "commit", "--quiet", "-m", f"add {', '.join(files)}")
        _git(self.work, "push", "--quiet", "origin", "HEAD:refs/heads/main")
        return _git(self.work, "rev-parse", "HEAD")

    def commit_symlinks(self, links: dict[str, Path], folder: str = "") -> str:
        """Add symlinks (name -> target outside the repo) and push."""
        target = self.work / folder
        target.mkdir(parents=True, exist_ok=True)
        for name, destination in links.items():
            (target / name).symlink_to(destination)
        _git(self.work, "add", "--all")
        _git(self.work, "commit", "--quiet", "-m", f"link {', '.join(links)}")
        _git(self.work, "push", "--quiet", "origin", "HEAD:refs/heads/main")
        return _git(self.work, "rev-parse", "HEAD")

    def commit_carols(self) -> str:
        return self.commit({p.name: p for p in sorted(FIXTURES.glob("*.cho"))})

    def tag(self, name: str) -> None:
        _git(self.work, "tag", name)
        _git(self.work, "push", "--quiet", "origin", name)

    def disappear(self) -> None:
        """Make the repo unreachable, as if the network were down."""
        shutil.rmtree(self.bare)


def redirect(monkeypatch: pytest.MonkeyPatch, addresses: dict[str, Path]) -> None:
    """Have git itself fetch each address from a local repo instead."""
    monkeypatch.setenv("GIT_CONFIG_COUNT", str(len(addresses)))
    for i, (address, repo) in enumerate(addresses.items()):
        monkeypatch.setenv(f"GIT_CONFIG_KEY_{i}", f"url.{repo}.insteadOf")
        monkeypatch.setenv(f"GIT_CONFIG_VALUE_{i}", address)


def git_source(address: str = ADDRESS, extra: str = "") -> str:
    return f'[sources.carols]\ngit = "{address}"\n{extra}'
