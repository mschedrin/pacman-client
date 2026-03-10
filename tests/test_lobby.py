"""Tests for the lobby widget."""

from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from pacman.models import Player
from pacman.widgets.lobby import LobbyWidget


def _make_player(name: str, player_id: str = "id-1") -> Player:
    """Create a lobby Player for testing."""
    return Player(
        id=player_id,
        name=name,
        status="lobby",
        role=None,
        position=None,
        direction=None,
    )


# --- _render_lobby unit tests (no Textual app needed) ---


class TestRenderLobbyDirect:
    """Test _render_lobby output directly without mounting the widget."""

    def test_empty_lobby_shows_no_players_message(self) -> None:
        widget = LobbyWidget()
        text = widget._render_lobby()
        plain = text.plain
        assert "No players yet" in plain

    def test_empty_lobby_shows_header(self) -> None:
        widget = LobbyWidget()
        text = widget._render_lobby()
        plain = text.plain
        assert "PACMAN" in plain

    def test_empty_lobby_shows_waiting_status(self) -> None:
        widget = LobbyWidget()
        text = widget._render_lobby()
        plain = text.plain
        assert "Waiting for round to start..." in plain

    def test_empty_lobby_shows_zero_count(self) -> None:
        widget = LobbyWidget()
        text = widget._render_lobby()
        plain = text.plain
        assert "Players (0):" in plain

    def test_single_player_shown(self) -> None:
        widget = LobbyWidget()
        widget._players = [_make_player("Alice")]
        text = widget._render_lobby()
        plain = text.plain
        assert "Alice" in plain
        assert "Players (1):" in plain

    def test_multiple_players_shown(self) -> None:
        widget = LobbyWidget()
        widget._players = [
            _make_player("Alice", "id-1"),
            _make_player("Bob", "id-2"),
            _make_player("Charlie", "id-3"),
        ]
        text = widget._render_lobby()
        plain = text.plain
        assert "Alice" in plain
        assert "Bob" in plain
        assert "Charlie" in plain
        assert "Players (3):" in plain

    def test_players_numbered_sequentially(self) -> None:
        widget = LobbyWidget()
        widget._players = [
            _make_player("Alice", "id-1"),
            _make_player("Bob", "id-2"),
        ]
        text = widget._render_lobby()
        plain = text.plain
        assert "1. Alice" in plain
        assert "2. Bob" in plain

    def test_no_players_message_hidden_when_players_exist(self) -> None:
        widget = LobbyWidget()
        widget._players = [_make_player("Alice")]
        text = widget._render_lobby()
        plain = text.plain
        assert "No players yet" not in plain

    def test_header_styled_bold_yellow(self) -> None:
        widget = LobbyWidget()
        text = widget._render_lobby()
        # Find the style for "PACMAN" text
        spans = text._spans
        # The first span should be "PACMAN" with bold yellow style
        assert any("bold" in str(s.style) and "yellow" in str(s.style) for s in spans)

    def test_waiting_status_always_shown(self) -> None:
        widget = LobbyWidget()
        widget._players = [_make_player("Alice")]
        text = widget._render_lobby()
        plain = text.plain
        assert "Waiting for round to start..." in plain


# --- update_players integration tests (need Textual app context) ---


def _make_test_app() -> App[None]:
    """Create a minimal Textual app with a LobbyWidget for testing."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield LobbyWidget()

    return TestApp()


@pytest.mark.asyncio
async def test_update_players_stores_players() -> None:
    """Test that update_players stores the player list."""
    async with _make_test_app().run_test() as pilot:
        widget = pilot.app.query_one(LobbyWidget)
        players = [_make_player("Alice"), _make_player("Bob", "id-2")]
        widget.update_players(players)
        await pilot.pause()
        assert len(widget._players) == 2
        assert widget._players[0].name == "Alice"
        assert widget._players[1].name == "Bob"


@pytest.mark.asyncio
async def test_update_players_replaces_previous() -> None:
    """Test that update_players replaces the previous player list."""
    async with _make_test_app().run_test() as pilot:
        widget = pilot.app.query_one(LobbyWidget)
        widget.update_players([_make_player("Alice")])
        await pilot.pause()
        widget.update_players([_make_player("Bob", "id-2")])
        await pilot.pause()
        assert len(widget._players) == 1
        assert widget._players[0].name == "Bob"


@pytest.mark.asyncio
async def test_update_players_makes_copy() -> None:
    """Test that update_players copies the list so mutations don't affect widget."""
    async with _make_test_app().run_test() as pilot:
        widget = pilot.app.query_one(LobbyWidget)
        players = [_make_player("Alice")]
        widget.update_players(players)
        await pilot.pause()
        # Modifying the original list should not affect the widget
        players.append(_make_player("Bob", "id-2"))
        assert len(widget._players) == 1


@pytest.mark.asyncio
async def test_update_players_empty_list() -> None:
    """Test that update_players works with an empty list."""
    async with _make_test_app().run_test() as pilot:
        widget = pilot.app.query_one(LobbyWidget)
        widget.update_players([_make_player("Alice")])
        await pilot.pause()
        widget.update_players([])
        await pilot.pause()
        assert len(widget._players) == 0


# --- Textual app integration tests ---


@pytest.mark.asyncio
async def test_lobby_widget_mounts_with_empty_state() -> None:
    """Test that the widget renders correctly when mounted."""
    async with _make_test_app().run_test() as pilot:
        widget = pilot.app.query_one(LobbyWidget)
        assert widget is not None
        text = widget._render_lobby()
        assert "PACMAN" in text.plain


@pytest.mark.asyncio
async def test_lobby_widget_update_players_in_app() -> None:
    """Test that update_players renders player info within a running app."""
    async with _make_test_app().run_test() as pilot:
        widget = pilot.app.query_one(LobbyWidget)
        players = [
            _make_player("Alice", "id-1"),
            _make_player("Bob", "id-2"),
        ]
        widget.update_players(players)
        await pilot.pause()
        text = widget._render_lobby()
        assert "Alice" in text.plain
        assert "Bob" in text.plain
        assert "Players (2):" in text.plain
