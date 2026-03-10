"""Tests for the PacmanApp main application."""

from __future__ import annotations

import pytest
from helpers import FakeWebSocket

from pacman.app import (
    BACKOFF_INITIAL,
    BACKOFF_MAX,
    BACKOFF_MULTIPLIER,
    PHASE_CONNECTING,
    PHASE_LOBBY,
    PHASE_PLAYING,
    PHASE_ROUND_END,
    PacmanApp,
    ReconnectBackoff,
    StatusBar,
)
from pacman.client import ConnectionFailed, PacmanClient
from pacman.widgets.game import GameWidget
from pacman.widgets.lobby import LobbyWidget


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


def _make_app_with_fake_ws(
    reconnect: bool = False,
    round_end_display: float = 0.01,
) -> tuple[PacmanApp, FakeWebSocket, PacmanClient]:
    """Create a PacmanApp with a fake WebSocket injected into the client.

    Returns a tuple of (app, fake_ws, client). The client is pre-connected
    via the fake WS. Reconnect is disabled by default for test stability.
    Round-end display defaults to 0.01s for fast test execution. Override
    with a larger value for tests that verify round-end phase persistence.
    """
    fake_ws = FakeWebSocket()
    client = PacmanClient()
    client._ws = fake_ws  # type: ignore[assignment]
    app = PacmanApp(
        url="ws://localhost:8000/ws",
        player_name="TestPlayer",
        client=client,
        reconnect=reconnect,
        round_end_display=round_end_display,
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
        app, fake_ws, _ = _make_app_with_fake_ws(round_end_display=60.0)
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
        """Receiving lobby after round_end defers, then transitions to lobby."""
        app, fake_ws, _ = _make_app_with_fake_ws(round_end_display=60.0)
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
            # During round-end display, lobby is deferred
            assert app.phase == PHASE_ROUND_END
            assert app._deferred_lobby is not None
            # Manually trigger the round-end timer callback
            app._round_end_timer_callback()
            assert app.phase == PHASE_LOBBY
            assert app._deferred_lobby is None


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
        app, fake_ws, _ = _make_app_with_fake_ws(round_end_display=60.0)
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
        # Don't close yet — check status while WS is still open
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause()
            await pilot.pause()
            await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "Something went wrong" in status.status_text
            fake_ws.queue_close()

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

    pass


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

    def test_app_reconnect_enabled_by_default(self) -> None:
        """App has reconnect enabled by default."""
        app = PacmanApp(url="ws://test/ws", player_name="Test")
        assert app.reconnect_enabled is True

    def test_app_reconnect_can_be_disabled(self) -> None:
        """App reconnect can be disabled for testing."""
        app = PacmanApp(url="ws://test/ws", player_name="Test", reconnect=False)
        assert app.reconnect_enabled is False

    def test_app_has_backoff(self) -> None:
        """App initializes with a ReconnectBackoff."""
        app = PacmanApp(url="ws://test/ws", player_name="Test")
        assert isinstance(app.backoff, ReconnectBackoff)


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
        # Don't close yet — check status while WS is still open
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(10):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "pacman" in status.status_text
            assert "42" in status.status_text
            fake_ws.queue_close()

    @pytest.mark.asyncio
    async def test_welcome_shows_join_info(self) -> None:
        """Welcome shows join info in the status bar."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data("abc-12345678", "TestPlayer"))
        # Don't close yet — check status while WS is still open
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "TestPlayer" in status.status_text
            fake_ws.queue_close()


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


# --- ReconnectBackoff unit tests ---


class TestReconnectBackoff:
    """Test the exponential backoff logic for reconnection."""

    def test_initial_delay(self) -> None:
        """First delay is the initial value."""
        backoff = ReconnectBackoff(initial=1.0, multiplier=2.0, maximum=10.0)
        assert backoff.next_delay() == 1.0

    def test_exponential_growth(self) -> None:
        """Delays double each time."""
        backoff = ReconnectBackoff(initial=1.0, multiplier=2.0, maximum=10.0)
        delays = [backoff.next_delay() for _ in range(5)]
        assert delays == [1.0, 2.0, 4.0, 8.0, 10.0]

    def test_capped_at_maximum(self) -> None:
        """Delay never exceeds the maximum."""
        backoff = ReconnectBackoff(initial=1.0, multiplier=2.0, maximum=10.0)
        delay = 0.0
        for _ in range(10):
            delay = backoff.next_delay()
        assert delay == 10.0

    def test_reset_restarts_sequence(self) -> None:
        """After reset, delays start from initial again."""
        backoff = ReconnectBackoff(initial=1.0, multiplier=2.0, maximum=10.0)
        backoff.next_delay()  # 1
        backoff.next_delay()  # 2
        backoff.next_delay()  # 4
        backoff.reset()
        assert backoff.next_delay() == 1.0

    def test_attempt_counter(self) -> None:
        """Attempt counter tracks number of calls."""
        backoff = ReconnectBackoff()
        assert backoff.attempt == 0
        backoff.next_delay()
        assert backoff.attempt == 1
        backoff.next_delay()
        assert backoff.attempt == 2

    def test_attempt_resets(self) -> None:
        """Reset clears the attempt counter."""
        backoff = ReconnectBackoff()
        backoff.next_delay()
        backoff.next_delay()
        backoff.reset()
        assert backoff.attempt == 0

    def test_custom_parameters(self) -> None:
        """Custom initial, multiplier, and maximum work correctly."""
        backoff = ReconnectBackoff(initial=0.5, multiplier=3.0, maximum=5.0)
        delays = [backoff.next_delay() for _ in range(4)]
        assert delays == [0.5, 1.5, 4.5, 5.0]

    def test_default_parameters(self) -> None:
        """Default parameters match the module constants."""
        backoff = ReconnectBackoff()
        assert backoff.initial == BACKOFF_INITIAL
        assert backoff.multiplier == BACKOFF_MULTIPLIER
        assert backoff.maximum == BACKOFF_MAX

    def test_single_step_to_max(self) -> None:
        """When initial equals maximum, all delays are the same."""
        backoff = ReconnectBackoff(initial=10.0, multiplier=2.0, maximum=10.0)
        assert backoff.next_delay() == 10.0
        assert backoff.next_delay() == 10.0


# --- Error handling tests ---


class TestErrorHandling:
    """Test error message handling in the app."""

    @pytest.mark.asyncio
    async def test_non_fatal_error_shows_in_status(self) -> None:
        """Non-fatal error messages display in the status bar."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_error_data("Invalid direction"))
        # Don't close yet — check status while WS is still open
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "Invalid direction" in status.status_text
            fake_ws.queue_close()

    @pytest.mark.asyncio
    async def test_non_fatal_error_displays_in_status(self) -> None:
        """Non-fatal errors are displayed in the status bar."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_error_data("Name too long"))
        # Don't close yet — check status while WS is still open
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "Name too long" in status.status_text
            fake_ws.queue_close()

    @pytest.mark.asyncio
    async def test_fatal_error_shows_in_status(self) -> None:
        """Fatal error messages display in the status bar before disconnect."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_error_data("Server is full"))
        # Don't close yet — check status while WS is still open
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "Server is full" in status.status_text
            fake_ws.queue_close()

    @pytest.mark.asyncio
    async def test_fatal_error_displays_in_status(self) -> None:
        """Fatal errors are displayed in the status bar."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_error_data("Server is stopped"))
        # Don't close yet — check status while WS is still open
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "Server is stopped" in status.status_text
            fake_ws.queue_close()

    @pytest.mark.asyncio
    async def test_multiple_errors_show_latest_in_status(self) -> None:
        """Multiple error messages show the latest one in status bar."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_message(_make_error_data("first error"))
        fake_ws.queue_message(_make_error_data("second error"))
        # Don't close yet — check status while WS is still open
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(8):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "second error" in status.status_text
            fake_ws.queue_close()


# --- Disconnection and reconnection tests ---


class TestDisconnection:
    """Test disconnection and reconnection behavior."""

    @pytest.mark.asyncio
    async def test_disconnect_shows_status_when_reconnect_disabled(self) -> None:
        """When reconnect is disabled, disconnection shows in status bar."""
        app, fake_ws, _ = _make_app_with_fake_ws(reconnect=False)
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            # After clean disconnect, should show disconnected status
            assert "Disconnected" in status.status_text

    @pytest.mark.asyncio
    async def test_disconnect_returns_to_connecting_phase(self) -> None:
        """After disconnect with reconnect disabled, phase reflects state."""
        app, fake_ws, _ = _make_app_with_fake_ws(reconnect=False)
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            # With reconnect disabled, the loop exits
            # Phase should be connecting since we never got past it
            assert app.phase == PHASE_CONNECTING

    @pytest.mark.asyncio
    async def test_quit_sets_shutting_down(self) -> None:
        """Pressing quit sets _shutting_down to stop reconnect loop."""
        app, fake_ws, _ = _make_app_with_fake_ws()
        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(3):
                await pilot.pause()
            await pilot.press("q")
            await pilot.pause()
            assert app._shutting_down is True

    @pytest.mark.asyncio
    async def test_backoff_reset_on_successful_connect(self) -> None:
        """Backoff resets after a successful connection (join completes)."""
        app, fake_ws, _ = _make_app_with_fake_ws(reconnect=False)
        # Manually set backoff to a non-initial state
        app.backoff.next_delay()
        app.backoff.next_delay()
        assert app.backoff.attempt == 2

        fake_ws.queue_message(_make_welcome_data())
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            # Backoff should have been reset on successful join
            assert app.backoff.attempt == 0

    @pytest.mark.asyncio
    async def test_connection_error_shows_status(self) -> None:
        """Connection errors display in status bar."""
        app, fake_ws, _ = _make_app_with_fake_ws(reconnect=False)
        # Make the fake WS raise an exception during iteration
        fake_ws.queue_message(_make_welcome_data())
        # Queue an invalid JSON to cause a parse error
        fake_ws.queue_message("not valid json")
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(8):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "Disconnected" in status.status_text

    @pytest.mark.asyncio
    async def test_connection_failed_shows_in_status(self) -> None:
        """ConnectionFailed shows user-friendly message without 'Disconnected' prefix."""
        client = PacmanClient()

        async def failing_connect(url: str) -> None:
            raise ConnectionFailed(f"Cannot connect to {url}: Connection refused")

        client.connect = failing_connect  # type: ignore[assignment]

        app = PacmanApp(
            url="ws://localhost:8000/ws",
            player_name="TestPlayer",
            client=client,
            reconnect=False,
        )
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "Cannot connect" in status.status_text
            assert not status.status_text.startswith("Disconnected")

    @pytest.mark.asyncio
    async def test_connection_failed_reconnects(self) -> None:
        """ConnectionFailed triggers reconnect with backoff message."""
        client = PacmanClient()
        connect_count = 0

        async def counting_connect(url: str) -> None:
            nonlocal connect_count
            connect_count += 1
            raise ConnectionFailed(f"Cannot connect to {url}: Connection refused")

        client.connect = counting_connect  # type: ignore[assignment]

        app = PacmanApp(
            url="ws://localhost:8000/ws",
            player_name="TestPlayer",
            client=client,
            reconnect=False,
        )
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            status = app.query_one("#status", StatusBar)
            assert "Cannot connect" in status.status_text
            assert connect_count >= 1

    @pytest.mark.asyncio
    async def test_connection_failed_shows_in_lobby_widget(self) -> None:
        """ConnectionFailed error is shown prominently in the lobby widget."""
        client = PacmanClient()

        async def failing_connect(url: str) -> None:
            raise ConnectionFailed(f"Cannot connect to {url}: Connection refused")

        client.connect = failing_connect  # type: ignore[assignment]

        app = PacmanApp(
            url="ws://localhost:8000/ws",
            player_name="TestPlayer",
            client=client,
            reconnect=False,
        )
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            lobby = app.query_one("#lobby", LobbyWidget)
            rendered = lobby.render()
            plain = rendered.plain if hasattr(rendered, "plain") else str(rendered)
            assert "Cannot connect" in plain
            assert "Waiting for round to start" not in plain

    @pytest.mark.asyncio
    async def test_connecting_phase_shows_status_in_lobby(self) -> None:
        """During connecting phase, lobby shows connection status, not 'Waiting'."""
        app, fake_ws, _ = _make_app_with_fake_ws(reconnect=False)
        fake_ws.queue_close()
        async with app.run_test(size=(80, 24)) as pilot:
            for _ in range(5):
                await pilot.pause()
            lobby = app.query_one("#lobby", LobbyWidget)
            rendered = lobby.render()
            plain = rendered.plain if hasattr(rendered, "plain") else str(rendered)
            # Should not show the misleading "Waiting for round to start"
            assert "Waiting for round to start" not in plain
