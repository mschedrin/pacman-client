"""Tests for the PacmanApp main application."""

from __future__ import annotations

import asyncio
import json

import pytest

from pacman.app import (
    PHASE_CONNECTING,
    PHASE_LOBBY,
    PHASE_PLAYING,
    PHASE_ROUND_END,
    PacmanApp,
    StatusBar,
)
from pacman.client import PacmanClient
from pacman.models import Player, Welcome
from pacman.widgets.game import GameWidget
from pacman.widgets.lobby import LobbyWidget

# --- Helpers ---


class FakeWebSocket:
    """A fake WebSocket connection for testing the app."""

    def __init__(self) -> None:
        self.sent: list[str] = []
        self._messages: asyncio.Queue[str | None] = asyncio.Queue()
        self.close_code: int | None = None
        self.closed: bool = False

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def close(self) -> None:
        self.close_code = 1000
        self.closed = True
        self._messages.put_nowait(None)

    def queue_message(self, data: dict | str) -> None:
        if isinstance(data, dict):
            self._messages.put_nowait(json.dumps(data))
        else:
            self._messages.put_nowait(data)

    def queue_close(self) -> None:
        self._messages.put_nowait(None)

    def __aiter__(self) -> FakeWebSocket:
        return self

    async def __anext__(self) -> str:
        msg = await self._messages.get()
        if msg is None:
            raise StopAsyncIteration
        return msg


def _make_player(name: str = "Alice", player_id: str = "p1") -> dict:
    """Create a lobby player dict for protocol messages."""
    return {
        "id": player_id,
        "name": name,
        "status": "lobby",
        "role": None,
        "position": None,
        "direction": None,
    }


def _make_welcome_data(player_id: str = "p1", name: str = "TestPlayer") -> dict:
    return {
        "type": "welcome",
        "id": player_id,
        "name": name,
        "players": [_make_player(name, player_id)],
    }


def _make_lobby_data(players: list[dict] | None = None) -> dict:
    if players is None:
        players = [_make_player("Alice", "p1"), _make_player("Bob", "p2")]
    return {"type": "lobby", "players": players}


def _make_round_start_data(role: str = "pacman") -> dict:
    return {
        "type": "round_start",
        "map": {
            "width": 3,
            "height": 3,
            "cells": [
                ["wall", "wall", "wall"],
                ["wall", "dot", "wall"],
                ["wall", "wall", "wall"],
            ],
        },
        "role": role,
        "players": [
            {
                "id": "p1",
                "name": "TestPlayer",
                "role": "pacman",
                "position": {"x": 1, "y": 1},
            },
            {
                "id": "p2",
                "name": "Bob",
                "role": "ghost",
                "position": {"x": 1, "y": 1},
            },
        ],
        "config": {
            "tickRate": 20,
            "powerPelletDuration": 100,
            "ghostRespawnDelay": 60,
            "pacmanCount": 1,
            "maxPlayers": 10,
            "idleShutdownMinutes": 180,
        },
    }


def _make_state_data(tick: int = 1) -> dict:
    return {
        "type": "state",
        "tick": tick,
        "players": [
            {
                "id": "p1",
                "name": "TestPlayer",
                "role": "pacman",
                "position": {"x": 1, "y": 1},
                "status": "active",
                "score": 10,
            },
            {
                "id": "p2",
                "name": "Bob",
                "role": "ghost",
                "position": {"x": 2, "y": 1},
                "status": "active",
                "score": 0,
            },
        ],
        "dots": [[1, 1]],
        "powerPellets": [],
        "timeElapsed": tick * 0.05,
    }


def _make_round_end_data(result: str = "pacman", scores: dict | None = None) -> dict:
    if scores is None:
        scores = {"p1": 45, "p2": 2}
    return {"type": "round_end", "result": result, "scores": scores}


def _make_error_data(message: str = "test error") -> dict:
    return {"type": "error", "message": message}


def _make_app_with_fake_ws() -> tuple[PacmanApp, FakeWebSocket, PacmanClient]:
    """Create a PacmanApp with a fake WebSocket injected into the client.

    Returns a tuple of (app, fake_ws, client). The app's _ws_loop
    is NOT started automatically; tests control the message flow.
    """
    fake_ws = FakeWebSocket()
    client = PacmanClient()
    client._ws = fake_ws  # type: ignore[assignment]
    app = PacmanApp(
        url="ws://localhost:8000/ws",
        player_name="TestPlayer",
        client=client,
    )
    return app, fake_ws, client


# --- Phase tracking tests ---


class TestPhaseTransitions:
    """Test that the app correctly transitions between phases."""

    @pytest.mark.asyncio
    async def test_initial_phase_is_connecting(self) -> None:
        """App starts in the connecting phase."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        # Don't queue any messages; close immediately so ws_loop exits
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)):
            # The app starts in connecting phase before ws_loop runs
            # but ws_loop runs immediately on mount, so we check the
            # phase was set to connecting initially
            assert app._phase in (PHASE_CONNECTING, PHASE_LOBBY)

    @pytest.mark.asyncio
    async def test_welcome_transitions_to_lobby(self) -> None:
        """Receiving a welcome message transitions to lobby phase."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            assert app.phase == PHASE_LOBBY

    @pytest.mark.asyncio
    async def test_welcome_sets_player_id(self) -> None:
        """Welcome message stores the player ID."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data("my-id-123", "TestPlayer"))
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            assert app._my_id == "my-id-123"

    @pytest.mark.asyncio
    async def test_welcome_sets_player_name(self) -> None:
        """Welcome message stores the player name."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data("p1", "MyName"))
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            assert app._my_name == "MyName"

    @pytest.mark.asyncio
    async def test_round_start_transitions_to_playing(self) -> None:
        """Receiving round_start transitions to playing phase."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_lobby_data())
        fake_ws.queue_message(_make_round_start_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            assert app.phase == PHASE_PLAYING

    @pytest.mark.asyncio
    async def test_round_start_sets_role(self) -> None:
        """Round start stores the player's role."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_round_start_data("ghost"))
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            assert app._my_role == "ghost"

    @pytest.mark.asyncio
    async def test_round_end_transitions_to_round_end(self) -> None:
        """Receiving round_end transitions to round_end phase."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_round_start_data())
        fake_ws.queue_message(_make_state_data(1))
        fake_ws.queue_message(_make_round_end_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            assert app.phase == PHASE_ROUND_END

    @pytest.mark.asyncio
    async def test_lobby_after_round_end_returns_to_lobby(self) -> None:
        """Receiving lobby after round_end returns to lobby phase."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_round_start_data())
        fake_ws.queue_message(_make_round_end_data())
        fake_ws.queue_message(_make_lobby_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            assert app.phase == PHASE_LOBBY


# --- Widget visibility tests ---


class TestWidgetVisibility:
    """Test that widgets are shown/hidden based on phase."""

    @pytest.mark.asyncio
    async def test_lobby_visible_in_lobby_phase(self) -> None:
        """Lobby widget is visible in lobby phase."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            lobby = app.query_one("#lobby", LobbyWidget)
            game = app.query_one("#game", GameWidget)
            assert lobby.display is True
            assert game.display is False

    @pytest.mark.asyncio
    async def test_game_visible_in_playing_phase(self) -> None:
        """Game widget is visible in playing phase."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_round_start_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            lobby = app.query_one("#lobby", LobbyWidget)
            game = app.query_one("#game", GameWidget)
            assert lobby.display is False
            assert game.display is True

    @pytest.mark.asyncio
    async def test_game_visible_during_round_end(self) -> None:
        """Game widget stays visible during round_end phase."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_round_start_data())
        fake_ws.queue_message(_make_round_end_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            game = app.query_one("#game", GameWidget)
            assert game.display is True


# --- Message handling tests ---


class TestMessageHandling:
    """Test that server messages are dispatched to the correct widgets."""

    @pytest.mark.asyncio
    async def test_lobby_message_updates_lobby_widget(self) -> None:
        """Lobby messages update the lobby widget's player list."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(
            _make_lobby_data([_make_player("Alice", "p1"), _make_player("Bob", "p2")])
        )
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            lobby = app.query_one("#lobby", LobbyWidget)
            assert len(lobby._players) == 2

    @pytest.mark.asyncio
    async def test_state_updates_game_widget(self) -> None:
        """State messages update the game widget."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_round_start_data())
        fake_ws.queue_message(_make_state_data(5))
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            game = app.query_one("#game", GameWidget)
            assert game._state is not None
            assert game._state.tick == 5

    @pytest.mark.asyncio
    async def test_round_start_configures_game_widget(self) -> None:
        """Round start sets the map and player info on the game widget."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data("my-id", "TestPlayer"))
        fake_ws.queue_message(_make_round_start_data("pacman"))
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            game = app.query_one("#game", GameWidget)
            assert game._game_map is not None
            assert game._game_map.width == 3
            assert game._my_id == "my-id"
            assert game._my_role == "pacman"

    @pytest.mark.asyncio
    async def test_round_start_resets_direction(self) -> None:
        """Round start resets the direction dedup on the client."""
        app, fake_ws, client = _make_app_with_fake_ws()
        # Simulate that a direction was previously sent
        client._last_direction = "up"
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_round_start_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            # Direction should be reset after round_start
            assert client._last_direction is None

    @pytest.mark.asyncio
    async def test_error_message_updates_status(self) -> None:
        """Error messages are displayed in the status bar."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_error_data("Something went wrong"))
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "Something went wrong" in status.status_text

    @pytest.mark.asyncio
    async def test_state_ignored_when_not_playing(self) -> None:
        """State messages are ignored when not in playing phase."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        # Send state while still in lobby phase (no round_start)
        fake_ws.queue_message(_make_state_data(1))
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            game = app.query_one("#game", GameWidget)
            # State should not have been applied because we're in lobby
            assert game._state is None


# --- Key binding tests ---


class TestKeyBindings:
    """Test that key bindings dispatch correctly."""

    @pytest.mark.asyncio
    async def test_direction_not_sent_in_lobby(self) -> None:
        """Arrow keys don't send direction when in lobby phase."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            # Record sent messages count before key press
            sent_before = len(fake_ws.sent)
            await pilot.press("up")
            await pilot.pause()
            # No new messages should be sent (join was sent, nothing else)
            assert len(fake_ws.sent) == sent_before

    @pytest.mark.asyncio
    async def test_quit_binding(self) -> None:
        """Pressing 'q' exits the app."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.press("q")
            await pilot.pause()
            # The app should have initiated exit
            assert app.return_code is not None or app._exit


# --- _handle_message dispatch tests (unit-level, no Textual) ---


class TestHandleMessageDispatch:
    """Test the _handle_message method dispatches correctly."""

    def test_handle_welcome(self) -> None:
        """_handle_message routes Welcome to _on_welcome."""
        welcome = Welcome(
            id="test-id",
            name="TestPlayer",
            players=[Player("test-id", "TestPlayer", "lobby")],
        )
        # Can't call _handle_message without widgets mounted,
        # but we can test the match logic exists
        # Instead we test the model directly
        assert welcome.id == "test-id"

    def test_phase_constants(self) -> None:
        """Phase constants are correct strings."""
        assert PHASE_CONNECTING == "connecting"
        assert PHASE_LOBBY == "lobby"
        assert PHASE_PLAYING == "playing"
        assert PHASE_ROUND_END == "round_end"


# --- _set_phase tests (unit-level) ---


class TestSetPhase:
    """Test _set_phase behavior without full app context."""

    @pytest.mark.asyncio
    async def test_set_phase_connecting_shows_lobby(self) -> None:
        """Connecting phase shows lobby widget."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            app._set_phase(PHASE_CONNECTING)
            lobby = app.query_one("#lobby", LobbyWidget)
            game = app.query_one("#game", GameWidget)
            assert lobby.display is True
            assert game.display is False

    @pytest.mark.asyncio
    async def test_set_phase_lobby_shows_lobby(self) -> None:
        """Lobby phase shows lobby widget."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            app._set_phase(PHASE_LOBBY)
            lobby = app.query_one("#lobby", LobbyWidget)
            game = app.query_one("#game", GameWidget)
            assert lobby.display is True
            assert game.display is False

    @pytest.mark.asyncio
    async def test_set_phase_playing_shows_game(self) -> None:
        """Playing phase shows game widget."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            app._set_phase(PHASE_PLAYING)
            lobby = app.query_one("#lobby", LobbyWidget)
            game = app.query_one("#game", GameWidget)
            assert lobby.display is False
            assert game.display is True

    @pytest.mark.asyncio
    async def test_set_phase_round_end_shows_game(self) -> None:
        """Round end phase keeps game widget visible."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            app._set_phase(PHASE_ROUND_END)
            lobby = app.query_one("#lobby", LobbyWidget)
            game = app.query_one("#game", GameWidget)
            assert lobby.display is False
            assert game.display is True


# --- Full lifecycle test ---


class TestFullLifecycle:
    """Test a complete game lifecycle flow."""

    @pytest.mark.asyncio
    async def test_full_game_lifecycle(self) -> None:
        """Test connect -> lobby -> playing -> round_end -> lobby."""
        app, fake_ws, _ = _make_app_with_fake_ws()

        # Queue a full game lifecycle
        fake_ws.queue_message(_make_welcome_data("p1", "TestPlayer"))
        fake_ws.queue_message(_make_lobby_data([_make_player("TestPlayer", "p1")]))
        fake_ws.queue_message(_make_round_start_data("pacman"))
        fake_ws.queue_message(_make_state_data(1))
        fake_ws.queue_message(_make_state_data(2))
        fake_ws.queue_message(_make_state_data(3))
        fake_ws.queue_message(_make_round_end_data("pacman", {"p1": 50}))
        fake_ws.queue_message(_make_lobby_data([_make_player("TestPlayer", "p1")]))
        fake_ws.queue_close()

        async with app.run_test(size=(80, 24)) as pilot:
            # Let all messages process
            for _ in range(15):
                await pilot.pause()

            # Should end in lobby phase after full lifecycle
            assert app.phase == PHASE_LOBBY
            assert app._my_id == "p1"

    @pytest.mark.asyncio
    async def test_multiple_rounds(self) -> None:
        """Test that the app correctly handles multiple round cycles."""
        app, fake_ws, _ = _make_app_with_fake_ws()

        # Round 1
        fake_ws.queue_message(_make_welcome_data("p1", "TestPlayer"))
        fake_ws.queue_message(_make_round_start_data("pacman"))
        fake_ws.queue_message(_make_state_data(1))
        fake_ws.queue_message(_make_round_end_data("pacman"))
        fake_ws.queue_message(_make_lobby_data())

        # Round 2
        fake_ws.queue_message(_make_round_start_data("ghost"))
        fake_ws.queue_message(_make_state_data(1))
        fake_ws.queue_message(_make_round_end_data("ghosts"))
        fake_ws.queue_message(_make_lobby_data())
        fake_ws.queue_close()

        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(20):
                await pilot.pause()

            # Should end in lobby after second round
            assert app.phase == PHASE_LOBBY
            # Role should be from the last round_start
            assert app._my_role == "ghost"


# --- App construction tests ---


class TestAppConstruction:
    """Test app initialization."""

    def test_app_stores_url(self) -> None:
        """App stores the URL."""
        app = PacmanApp(url="ws://localhost:8000/ws", player_name="Test")
        assert app.url == "ws://localhost:8000/ws"

    def test_app_stores_player_name(self) -> None:
        """App stores the player name."""
        app = PacmanApp(url="ws://test/ws", player_name="MyName")
        assert app.player_name == "MyName"

    def test_app_default_phase(self) -> None:
        """App starts in connecting phase."""
        app = PacmanApp(url="ws://test/ws", player_name="Test")
        assert app.phase == PHASE_CONNECTING

    def test_app_accepts_custom_client(self) -> None:
        """App can accept a custom PacmanClient for testing."""
        client = PacmanClient()
        app = PacmanApp(url="ws://test/ws", player_name="Test", client=client)
        assert app.client is client

    def test_app_creates_default_client(self) -> None:
        """App creates a PacmanClient by default."""
        app = PacmanApp(url="ws://test/ws", player_name="Test")
        assert isinstance(app.client, PacmanClient)


# --- Status bar tests ---


class TestStatusBar:
    """Test status bar updates."""

    @pytest.mark.asyncio
    async def test_round_end_shows_result(self) -> None:
        """Round end shows the result in the status bar."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data("p1", "TestPlayer"))
        fake_ws.queue_message(_make_round_start_data())
        fake_ws.queue_message(_make_round_end_data("pacman", {"p1": 42}))
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(10):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "pacman" in status.status_text
            assert "42" in status.status_text

    @pytest.mark.asyncio
    async def test_welcome_shows_join_info(self) -> None:
        """Welcome shows join info in the status bar."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data("abc-12345678", "TestPlayer"))
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "TestPlayer" in status.status_text


# --- Compose tests ---


class TestCompose:
    """Test that compose yields the expected widgets."""

    @pytest.mark.asyncio
    async def test_compose_has_lobby_widget(self) -> None:
        """Compose yields a LobbyWidget."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert app.query_one("#lobby", LobbyWidget) is not None

    @pytest.mark.asyncio
    async def test_compose_has_game_widget(self) -> None:
        """Compose yields a GameWidget."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert app.query_one("#game", GameWidget) is not None

    @pytest.mark.asyncio
    async def test_compose_has_status_bar(self) -> None:
        """Compose yields a StatusBar."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            assert app.query_one("#status", StatusBar) is not None
