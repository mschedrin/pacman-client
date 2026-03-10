"""Main Textual application for the Pacman TUI client."""

from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
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

# How long to show round_end results before returning to lobby (seconds)
ROUND_END_DISPLAY_SECONDS = 3.0

# Default player name
DEFAULT_PLAYER_NAME = "Player"


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
    with Unicode and color. Supports lobby and playing phases.
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
        **kwargs: Any,
    ) -> None:
        """Initialize the Pacman app.

        Args:
            url: WebSocket URL to connect to (e.g. ws://localhost:8000/ws).
            player_name: Display name for this player.
            client: Optional PacmanClient instance (for testing).
        """
        super().__init__(**kwargs)
        self.url = url
        self.player_name = player_name
        self.client = client or PacmanClient()
        self._phase: str = PHASE_CONNECTING
        self._my_id: str = ""
        self._my_name: str = ""
        self._my_role: str = ""

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

        If the client is already connected (e.g. injected for testing),
        skips the connect step and proceeds directly to join + listen.
        """
        try:
            if not self.client.connected:
                await self.client.connect(self.url)
            await self.client.join(self.player_name)
            self._update_status(f"Connected to {self.url}")

            async for msg in self.client.messages():
                self._handle_message(msg)
        except Exception as exc:
            self._update_status(f"Connection error: {exc}")
        finally:
            await self.client.close()

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
        self._my_name = msg.name
        self._set_phase(PHASE_LOBBY)
        lobby = self.query_one("#lobby", LobbyWidget)
        lobby.update_players(msg.players)
        self._update_status(f"Joined as {msg.name} (id: {msg.id[:8]}...)")

    def _on_lobby(self, msg: Lobby) -> None:
        """Handle lobby message: update player list."""
        self._set_phase(PHASE_LOBBY)
        lobby = self.query_one("#lobby", LobbyWidget)
        lobby.update_players(msg.players)

    def _on_round_start(self, msg: RoundStart) -> None:
        """Handle round_start: configure game widget and enter playing phase."""
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
        """Handle round_end: show results briefly, then return to lobby."""
        self._set_phase(PHASE_ROUND_END)

        # Build result message
        my_score = msg.scores.get(self._my_id, 0)
        result_text = f"Round over! Result: {msg.result} | Your score: {my_score}"
        self._update_status(result_text)

    def _on_error(self, msg: Error) -> None:
        """Handle error message: display in status bar."""
        self._update_status(f"Error: {msg.message}")

    def _set_phase(self, phase: str) -> None:
        """Update the current phase and toggle widget visibility."""
        self._phase = phase

        try:
            lobby = self.query_one("#lobby", LobbyWidget)
            game = self.query_one("#game", GameWidget)
        except Exception:
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
        except Exception:
            pass

    async def action_direction(self, direction: str) -> None:
        """Handle arrow key input: send direction to server."""
        if self._phase != PHASE_PLAYING:
            return
        if not self.client.connected:
            return
        try:
            await self.client.send_direction(direction)
        except Exception:
            pass

    async def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
