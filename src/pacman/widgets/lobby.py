"""Lobby widget displaying player list and waiting status."""

from typing import Any

from rich.text import Text
from textual.widgets import Static

from pacman.models import Player


class LobbyWidget(Static):
    """Displays the lobby screen with player list and waiting status.

    Shows connected players and a "Waiting for round to start..." message
    between game rounds.
    """

    DEFAULT_CSS = """
    LobbyWidget {
        width: 100%;
        height: 100%;
        content-align: center middle;
        padding: 2 4;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._players: list[Player] = []

    def update_players(self, players: list[Player]) -> None:
        """Update the displayed player list.

        Args:
            players: Current list of players in the lobby.
        """
        self._players = list(players)
        self.update(self._render_lobby())

    def _render_lobby(self) -> Text:
        """Render the lobby display as a Rich Text object.

        Returns:
            A Rich Text object with the lobby header, player list, and status.
        """
        text = Text()

        # Header
        text.append("PACMAN", style="bold yellow")
        text.append("\n\n")

        # Player count
        count = len(self._players)
        text.append(f"Players ({count}):", style="bold white")
        text.append("\n")

        # Player list
        if self._players:
            for i, player in enumerate(self._players):
                text.append(f"  {i + 1}. {player.name}", style="bright_white")
                text.append("\n")
        else:
            text.append("  No players yet", style="bright_black")
            text.append("\n")

        text.append("\n")
        text.append("Waiting for round to start...", style="bright_black")

        return text

    def set_status(self, message: str) -> None:
        """Display a status message in place of the player list.

        Used during connecting/reconnecting to show connection status
        prominently instead of the misleading lobby view.

        Args:
            message: The status message to display.
        """
        text = Text()
        text.append("PACMAN", style="bold yellow")
        text.append("\n\n")
        text.append(message, style="bright_black")
        self.update(text)

    def on_mount(self) -> None:
        """Render initial empty lobby on mount."""
        self.update(self._render_lobby())
