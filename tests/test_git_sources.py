"""Issue #12: `git` sources, against a local bare repo standing in for GitHub.

The book file names https://example.test/carols.git; git itself is told (through its
environment) to fetch that address from the bare repo. The user cache is a temporary
folder, so nothing here touches the real one or the network."""

import os
import stat
from pathlib import Path

import pytest
from book_helpers import (
    ADDRESS,
    CAROLS,
    FULL_BOOK,
    Remote,
    annotation_count,
    assert_clean_error,
    built,
    git_source,
    redirect,
    run,
    uris,
    warning_lines,
    write_book,
)
from pdf_helpers import book_map, text_of
from pypdf import PdfReader

NEW_SONG = "{title:Brand New Tune}\n[G]La la\n"
pytestmark = pytest.mark.usefixtures("isolated_home")


@pytest.fixture
def remote(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Remote:
    repo = Remote.create(tmp_path / "github")
    repo.commit_carols()
    redirect(monkeypatch, {ADDRESS: repo.bare})
    return repo


@pytest.fixture(autouse=True)
def working_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    return cwd


def titles(reader: PdfReader) -> list[str]:
    return book_map(reader).titles


def with_new_song(*names: str) -> list[str]:
    return ["Title", "Index", *sorted([*CAROLS, *names]), "Reference", "Credits"]


def test_a_git_source_is_cloned_into_the_user_cache(
    remote: Remote,
    tmp_path: Path,
    isolated_home: Path,
    working_folder: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    book = write_book(tmp_path, sources=git_source())
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == FULL_BOOK
    assert list(isolated_home.rglob("strumbook")), "nothing cached under strumbook/"
    assert list(working_folder.iterdir()) == []  # no collections/ folder here
    assert [p.name for p in (tmp_path / "books").iterdir()] == ["test.book.toml"]


def test_each_build_fetches_the_latest_songs(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, sources=git_source())
    assert titles(built(book, tmp_path / "one.pdf", capsys=capsys)) == FULL_BOOK
    remote.commit({"Brand New Tune.cho": NEW_SONG})
    second = built(book, tmp_path / "two.pdf", capsys=capsys)
    assert titles(second) == with_new_song("Brand New Tune")


def test_an_edited_song_shows_up_on_the_next_build(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, sources=git_source())
    built(book, tmp_path / "one.pdf", capsys=capsys)
    remote.commit({"Away In A Manger.cho": "{title:Away In A Manger}\n[G]Edited la\n"})
    second = built(book, tmp_path / "two.pdf", capsys=capsys)
    assert (
        "Edited la"
        in second.pages[book_map(second).first_page(CAROLS[0])].extract_text()
    )


def test_a_second_build_reuses_the_cache_when_the_network_is_down(
    remote: Remote,
    tmp_path: Path,
    isolated_home: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    book = write_book(tmp_path, sources=git_source())
    built(book, tmp_path / "one.pdf", capsys=capsys)
    remote.disappear()
    out = tmp_path / "two.pdf"
    code, err = run(book, out, capsys=capsys)
    assert code == 0, err
    assert titles(PdfReader(out)) == FULL_BOOK
    warnings = warning_lines(err)
    assert len(warnings) == 1, err
    assert "out of date" in warnings[0]
    assert "Traceback" not in err


def test_no_cache_and_no_network_is_an_error_naming_the_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    redirect(monkeypatch, {ADDRESS: tmp_path / "nowhere.git"})
    book = write_book(tmp_path, sources=git_source())
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out, "carols")


def test_a_failed_first_clone_leaves_nothing_that_fakes_a_cache(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    remote.disappear()
    book = write_book(tmp_path, sources=git_source())
    code, err = run(book, tmp_path / "one.pdf", capsys=capsys)
    assert code == 1, err
    code, err = run(book, tmp_path / "two.pdf", capsys=capsys)
    assert_clean_error(code, err, tmp_path / "two.pdf", "carols")  # still an error


# Pins.


@pytest.mark.parametrize("how", ["full-hash", "short-hash", "tag"])
def test_a_pin_checks_out_that_commit_and_ignores_later_ones(
    how: str,
    remote: Remote,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = remote.commit({"Pinned Tune.cho": "{title:Pinned Tune}\n[G]La\n"})
    remote.tag("v1")
    remote.commit({"Brand New Tune.cho": NEW_SONG})
    pin = {"full-hash": first, "short-hash": first[:7], "tag": "v1"}[how]
    book = write_book(tmp_path, sources=git_source(extra=f'pin = "{pin}"\n'))
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == with_new_song("Pinned Tune")
    assert "Brand New Tune" not in titles(reader)


def test_switching_the_pin_reuses_the_same_cache(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first = remote.commit({"Pinned Tune.cho": "{title:Pinned Tune}\n[G]La\n"})
    remote.commit({"Brand New Tune.cho": NEW_SONG})
    pinned = write_book(
        tmp_path, sources=git_source(extra=f'pin = "{first}"\n'), name="a.book.toml"
    )
    latest = write_book(tmp_path, sources=git_source(), name="b.book.toml")
    one = built(pinned, tmp_path / "one.pdf", capsys=capsys)
    assert "Brand New Tune" not in titles(one)
    two = built(latest, tmp_path / "two.pdf", capsys=capsys)
    assert "Brand New Tune" in titles(two)
    remote.disappear()  # the third build can only be served from the same cache
    three = built(pinned, tmp_path / "three.pdf", capsys=capsys)
    assert "Brand New Tune" not in titles(three)
    assert "Pinned Tune" in titles(three)


def test_a_pinned_book_builds_from_the_cache_when_the_network_is_down(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    first = remote.commit({"Pinned Tune.cho": "{title:Pinned Tune}\n[G]La\n"})
    book = write_book(tmp_path, sources=git_source(extra=f'pin = "{first}"\n'))
    built(book, tmp_path / "one.pdf", capsys=capsys)
    remote.disappear()
    assert titles(built(book, tmp_path / "two.pdf", capsys=capsys)) == with_new_song(
        "Pinned Tune"
    )


def test_a_pin_that_does_not_exist_is_an_error_naming_it(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, sources=git_source(extra='pin = "no-such-tag"\n'))
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out, "no-such-tag")


def test_a_pin_cannot_smuggle_in_a_git_option(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    marker = tmp_path / "pwned"
    pin = f"--output={marker}"
    book = write_book(tmp_path, sources=git_source(extra=f"pin = '{pin}'\n"))
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out)
    assert not marker.exists()


# Credits.


def test_a_git_sources_address_is_credited(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, sources=git_source())
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert ADDRESS in uris(reader)


def test_a_link_replaces_the_git_address_in_credits(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    link = "https://example.org/our-songs"
    book = write_book(tmp_path, sources=git_source(extra=f"link = '{link}'\n"))
    found = uris(built(book, tmp_path / "book.pdf", capsys=capsys))
    assert link in found
    assert ADDRESS not in found


# Which addresses git is allowed to see.


def fake_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put a `git` first on PATH that only records that it was run."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    ran = tmp_path / "git-ran"
    script = bin_dir / "git"
    script.write_text(f'#!/bin/sh\ntouch "{ran}"\nexit 1\n', encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return ran


@pytest.mark.parametrize(
    "address",
    [
        "file:///srv/git/carols.git",
        "/srv/git/carols.git",
        "../carols.git",
        "carols.git",
        "ext::sh -c 'touch pwned' %S",
        "--upload-pack=touch pwned",
        "-ccore.sshCommand=touch pwned",
        "http://example.test/carols.git",
        "git://example.test/carols.git",
        "ftp://example.test/carols.git",
        "ssh://-oProxyCommand=touch pwned/x",
        "ssh://git@-oProxyCommand=x/y",
        "git@-oProxyCommand=x:y",
    ],
)
def test_other_addresses_are_refused_before_git_runs(
    address: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ran = fake_git(tmp_path, monkeypatch)
    book = write_book(tmp_path, sources=f"[sources.carols]\ngit = {address!r}\n")
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out, address)
    assert not ran.exists(), "git was run for a refused address"


def test_a_file_url_to_a_real_repo_is_still_refused(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    address = f"file://{remote.bare}"
    book = write_book(tmp_path, sources=git_source(address))
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out, address)


def test_a_plain_local_path_to_a_real_repo_is_refused_as_a_git_address(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, sources=git_source(str(remote.bare)))
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out, str(remote.bare))


@pytest.mark.parametrize(
    "address",
    ["git@example.test:carols.git", "ssh://git@example.test/carols.git"],
)
def test_ssh_addresses_are_accepted(
    address: str,
    remote: Remote,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    redirect(monkeypatch, {address: remote.bare})
    book = write_book(tmp_path, sources=git_source(address))
    assert titles(built(book, tmp_path / "book.pdf", capsys=capsys)) == FULL_BOOK


# git as a program.


def no_git(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    empty = tmp_path / "empty-path"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))


def test_a_git_source_without_git_installed_is_a_clear_error(
    remote: Remote,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    no_git(tmp_path, monkeypatch)
    book = write_book(tmp_path, sources=git_source())
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err.replace(str(book), "BOOK"), out, "git")


def test_path_sources_do_not_need_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    no_git(tmp_path, monkeypatch)
    reader = built(write_book(tmp_path), tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader) == FULL_BOOK


# Follow-up from review.

SECRET = "TOPSECRET-MARKER-TEXT"


def secret_file(tmp_path: Path) -> Path:
    outside = tmp_path / "outside"
    outside.mkdir()
    secret = outside / "secret.cho"
    secret.write_text(f"{{title:Hidden Inner Title}}\n[G]{SECRET}\n", encoding="utf-8")
    return secret


def build_allowing_failure(
    book: Path, out: Path, capsys: pytest.CaptureFixture[str]
) -> str:
    """Build; return all the PDF's text, or "" if the build refused."""
    code, err = run(book, out, capsys=capsys)
    assert code in (0, 1), err
    assert "Traceback" not in err
    assert SECRET not in err
    return text_of(PdfReader(out)) if code == 0 else ""


def test_a_song_symlink_in_a_git_source_is_never_followed(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = secret_file(tmp_path)
    remote.commit_symlinks({"Leaked Tune.cho": secret})
    book = write_book(tmp_path, sources=git_source())
    text = build_allowing_failure(book, tmp_path / "book.pdf", capsys)
    assert SECRET not in text
    assert "Hidden Inner Title" not in text  # the file's own title


def test_a_symlinked_songs_folder_in_a_git_source_is_never_followed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    secret = secret_file(tmp_path)
    repo = Remote.create(tmp_path / "linked")
    repo.commit({"README.md": "no songs here\n"})
    repo.commit_symlinks({"songs": secret.parent})
    redirect(monkeypatch, {ADDRESS: repo.bare})
    book = write_book(tmp_path, sources=git_source())
    text = build_allowing_failure(book, tmp_path / "book.pdf", capsys)
    assert SECRET not in text
    assert "Hidden Inner Title" not in text  # the file's own title


@pytest.mark.parametrize("folder", ["..", "../..", "songs/../.."])
def test_folder_cannot_leave_a_git_source(
    folder: str, remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book = write_book(tmp_path, sources=git_source(extra=f"folder = '{folder}'\n"))
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err.replace(str(book), "BOOK"), out, "carols")


def test_a_cache_folder_that_cannot_be_created_is_a_clean_error(
    remote: Remote,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    not_a_folder = tmp_path / "plain-file"
    not_a_folder.write_text("I am a file\n", encoding="utf-8")
    for name in ("HOME", "USERPROFILE", "XDG_CACHE_HOME", "LOCALAPPDATA"):
        monkeypatch.setenv(name, str(not_a_folder))
    book = write_book(tmp_path, sources=git_source())
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out)


@pytest.mark.parametrize(
    "address",
    [
        "https://user:ghp_secret123@example.test/carols.git",
        "https://user@example.test/carols.git",
    ],
)
def test_sign_in_details_in_an_address_are_refused_and_never_printed(
    address: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ran = fake_git(tmp_path, monkeypatch)
    book = write_book(tmp_path, sources=git_source(address))
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out)
    assert "ghp_secret123" not in err
    assert not ran.exists(), "git was run for a refused address"


def commit_two_pins(remote: Remote) -> tuple[str, str]:
    one = remote.commit({"One Tune.cho": "{title:One Tune}\n[G]La\n"})
    two = remote.commit({"Two Tune.cho": "{title:Two Tune}\n[G]La\n"})
    return one, two


@pytest.mark.parametrize("kind", ["different-pins", "pinned-and-not"])
def test_one_address_with_different_pins_is_an_error_naming_the_address(
    kind: str, remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    one, two = commit_two_pins(remote)
    second = f'pin = "{two}"\n' if kind == "different-pins" else ""
    sources = (
        f'[sources.one]\ngit = "{ADDRESS}"\npin = "{one}"\n'
        f'[sources.two]\ngit = "{ADDRESS}"\n{second}'
    )
    book = write_book(tmp_path, sources=sources)
    out = tmp_path / "book.pdf"
    code, err = run(book, out, capsys=capsys)
    assert_clean_error(code, err, out, ADDRESS)


def test_one_address_and_pin_with_different_folders_builds_and_is_credited_once(
    remote: Remote, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    remote.commit({"Left Tune.cho": "{title:Left Tune}\n[G]La\n"}, folder="left")
    first = remote.commit(
        {"Right Tune.cho": "{title:Right Tune}\n[G]La\n"}, folder="right"
    )
    sources = "".join(
        f'[sources.{name}]\ngit = "{ADDRESS}"\npin = "{first}"\nfolder = "{name}"\n'
        for name in ("left", "right")
    )
    book = write_book(tmp_path, sources=sources)
    reader = built(book, tmp_path / "book.pdf", capsys=capsys)
    assert titles(reader)[2:4] == ["Left Tune", "Right Tune"]
    single = write_book(
        tmp_path,
        sources=git_source(extra=f'pin = "{first}"\nfolder = "left"\n'),
        name="single.book.toml",
    )
    one = built(single, tmp_path / "single.pdf", capsys=capsys)
    assert annotation_count(one, ADDRESS) >= 1
    assert annotation_count(reader, ADDRESS) == annotation_count(one, ADDRESS)
