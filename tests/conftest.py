"""Reject accidental network use in the pytest process; this is not a sandbox."""

import socket
from collections.abc import Iterator
from pathlib import Path
from typing import NoReturn

import pytest


def _blocked(*args: object, **kwargs: object) -> NoReturn:
    raise AssertionError(
        "Network access is disabled in unit tests; use a fake transport."
    )


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    # Covers ordinary Python DNS and outgoing socket APIs, not subprocesses or
    # native libraries. Future external-renderer tests must be offline by design.
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)
    monkeypatch.setattr(socket.socket, "sendto", _blocked)
    yield


@pytest.fixture
def isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point every platform's user-cache location at a temporary folder.

    Returns that folder, so a test can look for what a build left in it. Use it for
    any build that might clone a git source, so the real cache is never touched.
    """
    home = tmp_path / "home"
    home.mkdir()
    for name in ("HOME", "USERPROFILE", "XDG_CACHE_HOME", "LOCALAPPDATA"):
        monkeypatch.setenv(name, str(home))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "0")
    return home
