"""Main Textual application for the Pacman TUI client."""

import asyncio
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.timer import Timer
from textual.widgets import Footer, Header, Static

from pacman.client import PacmanClient
from pacman.models import (
    Error,
    Lobby,
    RoundEnd,
    RoundStart,
    State,
    Welcome,
)
from pacman.widgets.game import GameWidget
from pacman.widgets.lobby import LobbyWidget

# Game phases
PHASE_CONNECTING = "connecting"
PHASE_LOBBY = "lobby"
PHASE_PLAYING = "playing"
PHASE_ROUND_END = "round_end"

# Default player name
DEFAULT_PLAYER_NAME = "Player"

# Reconnection backoff settings
BACKOFF_INITIAL = 1.0
BACKOFF_MULTIPLIER = 2.0
BACKOFF_MAX = 10.0

# Fatal error messages from the server that close the connection
FATAL_ERROR_MESSAGES = frozenset(
    {
        "Server is stopped",
        "Round in progress",
        "Server is full",
        "Server stopped",
    }
)

# How long to display non-fatal error messages in status bar (seconds)
ERROR_DISPLAY_SECONDS = 5.0

# How long to show round-end results before transitioning to lobby (seconds)
ROUND_END_DISPLAY_SECONDS = 3.0


class ReconnectBackoff:
    """Computes exponential backoff delays for reconnection attempts.

    Starts at `initial` seconds, doubles each attempt, capped at `maximum`.
    Call `reset()` after a successful connection to start over.
    """

    def __init__(
        self,
        initial: float = BACKOFF_INITIAL,
        multiplier: float = BACKOFF_MULTIPLIER,
        maximum: float = BACKOFF_MAX,
    ) -> None:
        self.initial = initial
        self.multiplier = multiplier
        self.maximum = maximum
        self._current = initial
        self._attempt = 0

    @property
    def attempt(self) -> int:
        """Number of reconnection attempts made."""
        return self._attempt

    def next_delay(self) -> float:
        """Return the next backoff delay and advance the counter."""
        delay = self._current
        self._attempt += 1
        self._current = min(self._current * self.multiplier, self.maximum)
        return delay

    def reset(self) -> None:
        """Reset backoff to initial state after a successful connection."""
        self._current = self.initial
        self._attempt = 0


class StatusBar(Static):
    """Displays connection status at the bottom of the screen."""

    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $surface;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._status_text: str = ""

    @property
    def status_text(self) -> str:
        """The current status text."""
        return self._status_text

    def set_status(self, text: str) -> None:
        """Update the status text.

        Args:
            text: The status text to display.
        """
        self._status_text = text
        self.update(text)


class PacmanApp(App[None]):
    """Multiplayer Pacman TUI client application.

    Connects to a game server via WebSocket, renders the game in a terminal
    with Unicode and color. Supports lobby and playing phases with automatic
    reconnection on disconnect.
    """

    TITLE = "Pacman"

    CSS = """
    Screen {
        layout: vertical;
    }
    """

    BINDINGS = [
        Binding("up", "direction('up')", "Up", show=False),
        Binding("down", "direction('down')", "Down", show=False),
        Binding("left", "direction('left')", "Left", show=False),
        Binding("right", "direction('right')", "Right", show=False),
        Binding("w", "direction('up')", "Up (W)", show=False),
        Binding("s", "direction('down')", "Down (S)", show=False),
        Binding("a", "direction('left')", "Left (A)", show=False),
        Binding("d", "direction('right')", "Right (D)", show=False),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        url: str,
        player_name: str = DEFAULT_PLAYER_NAME,
        client: PacmanClient | None = None,
        reconnect: bool = True,
        round_end_display: float = ROUND_END_DISPLAY_SECONDS,
        **kwargs: Any,
    ) -> None:
        """Initialize the Pacman app.

        Args:
            url: WebSocket URL to connect to (e.g. ws://localhost:8000/ws).
            player_name: Display name for this player.
            client: Optional PacmanClient instance (for testing).
            reconnect: Whether to auto-reconnect on disconnect. Disable for tests.
            round_end_display: Seconds to show round-end results before lobby.
        """
        super().__init__(**kwargs)
        self.url = url
        self.player_name = player_name
        self.client = client or PacmanClient()
        self.reconnect_enabled = reconnect
        self.backoff = ReconnectBackoff()
        self._phase: str = PHASE_CONNECTING
        self._my_id: str = ""
        self._my_role: str = ""
        self._error_clear_task: Timer | None = None
        self._round_end_timer: Timer | None = None
        self._deferred_lobby: Lobby | None = None
        self._round_end_display = round_end_display
        self._shutting_down: bool = False
        self._last_fatal_error: str | None = None

    @property
    def phase(self) -> str:
        """Current game phase."""
        return self._phase

    def compose(self) -> ComposeResult:
        """Create the app layout with lobby and game widgets."""
        yield Header()
        yield LobbyWidget(id="lobby")
        yield GameWidget(id="game")
        yield StatusBar(id="status")
        yield Footer()

    def on_mount(self) -> None:
        """Start the WebSocket connection loop when the app mounts."""
        self._set_phase(PHASE_CONNECTING)
        self._update_status("Connecting...")
        self.run_worker(self._ws_loop(), exclusive=True, name="ws_loop")

    async def _ws_loop(self) -> None:
        """Background worker: connect, join, and process messages.

        Implements an outer reconnect loop with exponential backoff.
        If the client is already connected (e.g. injected for testing),
        skips the connect step and proceeds directly to join + listen.
        """
        while not self._shutting_down:
            try:
                if not self.client.connected:
                    self._set_phase(PHASE_CONNECTING)
                    attempt = self.backoff.attempt
                    if attempt == 0:
                        status_msg = f"Connecting to {self.url}..."
                    else:
                        status_msg = (
                            f"Reconnecting to {self.url} (attempt {attempt + 1})..."
                        )
                    self._update_status(status_msg)
                    await self.client.connect(self.url)

                await self.client.join(self.player_name)
                self._update_status(f"Connected to {self.url}")

                async for msg in self.client.messages():
                    self._handle_message(msg)

                # messages() ended normally (server closed connection cleanly)
                await self.client.close()

            except Exception as exc:
                error_str = str(exc)
                try:
                    await self.client.close()
                except Exception:
                    pass

                if not self.reconnect_enabled:
                    self._update_status(f"Disconnected: {error_str}")
                    return

                # Show disconnect status, including fatal error reason if known
                self._set_phase(PHASE_CONNECTING)
                delay = self.backoff.next_delay()
                reason = self._last_fatal_error or error_str
                self._last_fatal_error = None
                self._update_status(
                    f"Disconnected: {reason} — reconnecting in {delay:.0f}s..."
                )
                await asyncio.sleep(delay)
                continue

            # Reached here if messages() ended without exception (clean close)
            if not self.reconnect_enabled:
                self._update_status("Disconnected")
                return

            self._set_phase(PHASE_CONNECTING)
            delay = self.backoff.next_delay()
            reason = self._last_fatal_error or "server closed connection"
            self._last_fatal_error = None
            self._update_status(
                f"Disconnected: {reason} — reconnecting in {delay:.0f}s..."
            )
            await asyncio.sleep(delay)

    def _handle_message(
        self,
        msg: Welcome | Lobby | RoundStart | State | RoundEnd | Error,
    ) -> None:
        """Dispatch a server message to the appropriate handler."""
        match msg:
            case Welcome():
                self._on_welcome(msg)
            case Lobby():
                self._on_lobby(msg)
            case RoundStart():
                self._on_round_start(msg)
            case State():
                self._on_state(msg)
            case RoundEnd():
                self._on_round_end(msg)
            case Error():
                self._on_error(msg)

    def _on_welcome(self, msg: Welcome) -> None:
        """Handle welcome message: save player ID and enter lobby."""
        self._my_id = msg.id
        self.backoff.reset()
        self._set_phase(PHASE_LOBBY)
        lobby = self.query_one("#lobby", LobbyWidget)
        lobby.update_players(msg.players)
        self._update_status(f"Joined as {msg.name} (id: {msg.id[:8]}...)")

    def _on_lobby(self, msg: Lobby) -> None:
        """Handle lobby message: update player list.

        If currently showing round-end results, defers the lobby transition
        until the display timer fires so the user can read the results.
        """
        if self._phase == PHASE_ROUND_END:
            # Defer the lobby transition until round-end display timer fires
            self._deferred_lobby = msg
            return
        self._set_phase(PHASE_LOBBY)
        lobby = self.query_one("#lobby", LobbyWidget)
        lobby.update_players(msg.players)

    def _on_round_start(self, msg: RoundStart) -> None:
        """Handle round_start: configure game widget and enter playing phase."""
        # Cancel any pending round-end timer and stale deferred lobby data
        if self._round_end_timer is not None:
            self._round_end_timer.stop()
            self._round_end_timer = None
        self._deferred_lobby = None

        self._my_role = msg.role
        self.client.reset_direction()

        game = self.query_one("#game", GameWidget)
        game.set_map(msg.map, self._my_id, self._my_role)

        self._set_phase(PHASE_PLAYING)
        self._update_status(
            f"Round started! You are {msg.role.upper()} | {len(msg.players)} players"
        )

    def _on_state(self, msg: State) -> None:
        """Handle state tick: update game widget."""
        if self._phase != PHASE_PLAYING:
            return
        game = self.query_one("#game", GameWidget)
        game.update_state(msg)

    def _on_round_end(self, msg: RoundEnd) -> None:
        """Handle round_end: show result briefly, then transition to lobby.

        Displays round results for ROUND_END_DISPLAY_SECONDS before
        transitioning to the lobby phase. If a lobby message arrives
        during this period, it is deferred and applied when the timer fires.
        """
        self._set_phase(PHASE_ROUND_END)
        self._deferred_lobby = None

        # Build result message
        my_score = msg.scores.get(self._my_id, 0)
        result_text = f"Round over! Result: {msg.result} | Your score: {my_score}"
        self._update_status(result_text)

        # Cancel any previous round-end timer
        if self._round_end_timer is not None:
            self._round_end_timer.stop()

        # Schedule transition to lobby after display period
        self._round_end_timer = self.set_timer(
            self._round_end_display, self._round_end_timer_callback
        )

    def _on_error(self, msg: Error) -> None:
        """Handle error message: display in status bar.

        Fatal errors (server stopped, full, round in progress) are noted
        in the status bar and stored so the reason is preserved in the
        subsequent reconnect status. Non-fatal errors are shown briefly
        and then cleared after ERROR_DISPLAY_SECONDS.
        """
        self._update_status(f"Error: {msg.message}")

        if msg.message in FATAL_ERROR_MESSAGES:
            self._last_fatal_error = msg.message
        else:
            # For non-fatal errors, schedule clearing the error display
            self._schedule_error_clear()

    def _schedule_error_clear(self) -> None:
        """Schedule clearing the error from the status bar after a delay."""
        # Cancel any pending clear
        if self._error_clear_task is not None:
            self._error_clear_task.stop()

        self._error_clear_task = self.set_timer(
            ERROR_DISPLAY_SECONDS, self._clear_error_callback
        )

    def _round_end_timer_callback(self) -> None:
        """Transition to lobby after round-end display period.

        Applies any deferred lobby message that arrived while the
        round-end results were being displayed.
        """
        if self._phase != PHASE_ROUND_END:
            return

        self._set_phase(PHASE_LOBBY)
        if self._deferred_lobby is not None:
            try:
                lobby = self.query_one("#lobby", LobbyWidget)
                lobby.update_players(self._deferred_lobby.players)
            except NoMatches:
                pass
            self._deferred_lobby = None

    def _clear_error_callback(self) -> None:
        """Clear the error status if it's still showing an error.

        Only restores 'Connected' status if the app is in a connected phase
        (lobby, playing, or round_end). If disconnected/reconnecting, the
        error is left visible so it's not replaced with a misleading status.
        """
        try:
            status = self.query_one("#status", StatusBar)
            if status.status_text.startswith("Error:") and self._phase in (
                PHASE_LOBBY,
                PHASE_PLAYING,
                PHASE_ROUND_END,
            ):
                self._update_status(f"Connected to {self.url}")
        except NoMatches:
            pass

    def _set_phase(self, phase: str) -> None:
        """Update the current phase and toggle widget visibility."""
        self._phase = phase

        try:
            lobby = self.query_one("#lobby", LobbyWidget)
            game = self.query_one("#game", GameWidget)
        except NoMatches:
            # Widgets not yet mounted
            return

        if phase in (PHASE_CONNECTING, PHASE_LOBBY):
            lobby.display = True
            game.display = False
        elif phase == PHASE_PLAYING:
            lobby.display = False
            game.display = True
        elif phase == PHASE_ROUND_END:
            # Keep game visible to show final state
            lobby.display = False
            game.display = True

    def _update_status(self, text: str) -> None:
        """Update the status bar text."""
        try:
            status = self.query_one("#status", StatusBar)
            status.set_status(text)
        except NoMatches:
            pass

    async def action_direction(self, direction: str) -> None:
        """Handle arrow key input: send direction to server."""
        if self._phase != PHASE_PLAYING:
            return
        try:
            await self.client.send_direction(direction)
        except (RuntimeError, OSError):
            # Connection lost — the reconnect loop will handle it
            pass

    async def action_quit(self) -> None:
        """Quit the application, closing the WebSocket connection."""
        self._shutting_down = True
        try:
            await self.client.close()
        except Exception:
            pass
        self.exit()
