"""Tests for the pacman entry point (__main__.py)."""

import pytest

from pacman.__main__ import parse_args


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
