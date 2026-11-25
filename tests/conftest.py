"""Reject accidental network use in the pytest process; this is not a sandbox."""

import socket
from collections.abc import Iterator
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
