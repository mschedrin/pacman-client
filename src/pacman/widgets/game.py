"""Game widget displaying the rendered grid, scoreboard, and status line."""

from typing import Any

from rich.text import Text
from textual.widgets import Static

from pacman.models import GameMap, State, StatePlayer
from pacman.renderer import render_grid

# Role display labels
ROLE_LABELS = {
    "pacman": "PACMAN",
    "ghost": "GHOST",
}

# Role display styles
ROLE_STYLES = {
    "pacman": "bold yellow",
    "ghost": "bold red",
}

# Status display styles
STATUS_STYLES = {
    "active": "green",
    "dead": "bright_black",
    "vulnerable": "bright_blue",
    "respawning": "bright_black",
}


class GameWidget(Static):
    """Displays the game screen with grid, scoreboard sidebar, and status line.

    Shows the game grid rendered from the current state, a sidebar with
    player scores sorted by score descending, and a status line with
    tick count, player role, and elapsed time.
    """

    DEFAULT_CSS = """
    GameWidget {
        width: 100%;
        height: 100%;
        padding: 0 1;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._game_map: GameMap | None = None
        self._state: State | None = None
        self._my_id: str = ""
        self._my_role: str = ""

    def set_map(self, game_map: GameMap, my_id: str, my_role: str) -> None:
        """Set the game map and player identity for rendering.

        Args:
            game_map: The game map from round_start.
            my_id: The local player's ID.
            my_role: The local player's role (pacman or ghost).
        """
        self._game_map = game_map
        self._my_id = my_id
        self._my_role = my_role

    def update_state(self, state: State) -> None:
        """Update the game display with a new state tick.

        Args:
            state: The current game state from a state tick.
        """
        self._state = state
        self.update(self._render_game())

    def _render_game(self) -> Text:
        """Render the full game display: grid + sidebar + status line.

        Returns:
            A Rich Text object with the combined game display.
        """
        if self._game_map is None or self._state is None:
            return Text("Waiting for game data...", style="bright_black")

        grid = render_grid(self._game_map, self._state, self._my_id)
        scoreboard = self._render_scoreboard()
        status = self._render_status_line()

        # Combine grid and scoreboard side by side
        result = _merge_grid_and_sidebar(grid, scoreboard)
        result.append("\n")
        result.append(status)

        return result

    def _render_scoreboard(self) -> Text:
        """Render the scoreboard as a Rich Text object.

        Players are sorted by score descending. Shows name, role, and score.

        Returns:
            A Rich Text object with the scoreboard.
        """
        text = Text()

        text.append("SCOREBOARD", style="bold white")
        text.append("\n")
        text.append("──────────────────", style="bright_black")
        text.append("\n")

        if self._state is None:
            return text

        # Sort players by score descending
        sorted_players = sorted(
            self._state.players, key=lambda p: p.score, reverse=True
        )

        for player in sorted_players:
            self._render_player_score(text, player)
            text.append("\n")

        return text

    def _render_player_score(self, text: Text, player: StatePlayer) -> None:
        """Render a single player's score entry.

        Args:
            text: The Text object to append to.
            player: The player to render.
        """
        # Marker for the local player
        marker = "> " if player.id == self._my_id else "  "
        text.append(marker, style="bold yellow" if player.id == self._my_id else "")

        # Role icon
        role_label = ROLE_LABELS.get(player.role, player.role.upper())
        role_style = ROLE_STYLES.get(player.role, "white")
        text.append(f"[{role_label}]", style=role_style)
        text.append(" ")

        # Player name
        name_style = "bold bright_white" if player.id == self._my_id else "bright_white"
        text.append(player.name, style=name_style)

        # Score right-aligned with padding
        score_str = f" {player.score:>5}"
        text.append(score_str, style="bold white")

        # Status indicator for non-active players
        status_style = STATUS_STYLES.get(player.status, "")
        if player.status != "active":
            text.append(f" ({player.status})", style=status_style)

    def _render_status_line(self) -> Text:
        """Render the status line with tick count, role, and time elapsed.

        Returns:
            A Rich Text object with the status line.
        """
        text = Text()

        if self._state is None:
            return text

        # Tick count
        text.append(f"Tick: {self._state.tick}", style="bright_black")
        text.append("  |  ", style="bright_black")

        # Player role
        role_label = ROLE_LABELS.get(self._my_role, self._my_role.upper())
        role_style = ROLE_STYLES.get(self._my_role, "white")
        text.append("Role: ", style="bright_black")
        text.append(role_label, style=role_style)
        text.append("  |  ", style="bright_black")

        # Time elapsed
        elapsed = self._state.time_elapsed
        minutes = int(elapsed) // 60
        seconds = int(elapsed) % 60
        text.append(f"Time: {minutes}:{seconds:02d}", style="bright_black")

        return text


def _merge_grid_and_sidebar(grid: Text, sidebar: Text) -> Text:
    """Merge the grid and sidebar side-by-side.

    Places the sidebar to the right of the grid with a separator.

    Args:
        grid: The rendered game grid.
        sidebar: The rendered scoreboard sidebar.

    Returns:
        A Rich Text object with grid and sidebar combined.
    """
    grid_lines = grid.plain.split("\n")

    # Calculate grid width from the longest line
    grid_width = max((len(line) for line in grid_lines), default=0)

    # Separator
    separator = "  |  "

    # Split grid and sidebar into their styled Text lines
    grid_text_lines = _split_text_lines(grid)
    sidebar_text_lines = _split_text_lines(sidebar)

    max_lines = max(len(grid_text_lines), len(sidebar_text_lines))

    result = Text()

    for i in range(max_lines):
        if i > 0:
            result.append("\n")

        # Grid line (pad to grid_width)
        if i < len(grid_text_lines):
            line = grid_text_lines[i]
            result.append_text(line)
            padding = grid_width - len(line.plain)
            if padding > 0:
                result.append(" " * padding)
        else:
            result.append(" " * grid_width)

        # Separator
        result.append(separator, style="bright_black")

        # Sidebar line
        if i < len(sidebar_text_lines):
            result.append_text(sidebar_text_lines[i])

    return result


def _split_text_lines(text: Text) -> list[Text]:
    """Split a Rich Text object into a list of Text objects, one per line.

    Args:
        text: The Rich Text to split.

    Returns:
        A list of Text objects, one for each line.
    """
    return list(text.split("\n"))
