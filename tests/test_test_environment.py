"""Demonstrate that ordinary Python networking fails closed in these tests."""

import socket

import pytest


def test_network_connection_is_rejected() -> None:
    with pytest.raises(AssertionError, match="Network access is disabled"):
        socket.create_connection(("example.invalid", 443))


def test_direct_socket_connection_is_rejected() -> None:
    with (
        socket.socket() as connection,
        pytest.raises(AssertionError, match="Network access is disabled"),
    ):
        connection.connect(("127.0.0.1", 9))


def test_dns_lookup_is_rejected() -> None:
    with pytest.raises(AssertionError, match="Network access is disabled"):
        socket.getaddrinfo("example.invalid", 443)
