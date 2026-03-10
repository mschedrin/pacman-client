"""Tests for the pacman entry point (__main__.py)."""

import pytest

from pacman.__main__ import normalize_url, parse_args


def test_parse_args_requires_host() -> None:
    """Verify --host is required."""
    with pytest.raises(SystemExit):
        parse_args([])


def test_parse_args_with_host() -> None:
    """Verify --host is parsed correctly."""
    args = parse_args(["--host", "localhost:8000"])
    assert args.host == "localhost:8000"


def test_parse_args_with_ws_url() -> None:
    """Verify --host accepts full ws:// URLs."""
    args = parse_args(["--host", "ws://example.com/ws"])
    assert args.host == "ws://example.com/ws"


def test_parse_args_with_name() -> None:
    """Verify --name is parsed correctly."""
    args = parse_args(["--host", "localhost:8000", "--name", "MyTeam"])
    assert args.name == "MyTeam"


def test_parse_args_name_default() -> None:
    """Verify --name defaults to 'Player'."""
    args = parse_args(["--host", "localhost:8000"])
    assert args.name == "Player"


# --- normalize_url tests ---


def test_normalize_url_plain_host() -> None:
    """Bare host:port gets ws:// prefix and /ws suffix."""
    assert normalize_url("localhost:8000") == "ws://localhost:8000/ws"


def test_normalize_url_ws_without_path() -> None:
    """ws:// URL without /ws is returned as-is (trust the user)."""
    assert normalize_url("ws://example.com") == "ws://example.com"


def test_normalize_url_ws_with_path() -> None:
    """ws:// URL already ending in /ws is returned as-is."""
    assert normalize_url("ws://example.com/ws") == "ws://example.com/ws"


def test_normalize_url_wss() -> None:
    """wss:// URLs are returned as-is."""
    assert normalize_url("wss://example.com") == "wss://example.com"
