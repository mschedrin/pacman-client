"""Render the game grid as a Rich Text object with styled spans."""

from rich.text import Text

from pacman.models import GameMap, State, StatePlayer

# Cell rendering constants (2 chars per cell for square aspect ratio)
WALL = "██"
DOT = "· "
POWER_PELLET = "● "
EMPTY = "  "

# Player character constants
PACMAN_CHAR = "ᗧ "
GHOST_CHAR = "ᗣ "
DEAD_CHAR = "✕ "
RESPAWNING_CHAR = "··"

# Style constants
WALL_STYLE = "blue"
DOT_STYLE = "white"
POWER_PELLET_STYLE = "bright_white"
VULNERABLE_GHOST_STYLE = "bright_blue"
DEAD_STYLE = "bright_black"
RESPAWNING_STYLE = "bright_black"

# Ghost colors by index for distinguishing multiple ghosts
GHOST_COLORS = ["red", "magenta", "cyan", "green"]


def _player_style(player: StatePlayer, my_id: str, ghost_index: int) -> tuple[str, str]:
    """Return (characters, style) for a player based on role and status.

    Args:
        player: The player to render.
        my_id: The local player's ID for bold highlighting.
        ghost_index: Index among ghosts, for color assignment.

    Returns:
        Tuple of (display characters, Rich style string).
    """
    is_me = player.id == my_id
    bold_prefix = "bold " if is_me else ""

    match player.role, player.status:
        case "pacman", "dead":
            return DEAD_CHAR, f"{bold_prefix}{DEAD_STYLE}"
        case "pacman", _:
            return PACMAN_CHAR, f"{bold_prefix}yellow"
        case "ghost", "vulnerable":
            return GHOST_CHAR, f"{bold_prefix}{VULNERABLE_GHOST_STYLE}"
        case "ghost", "respawning":
            return RESPAWNING_CHAR, f"{bold_prefix}{RESPAWNING_STYLE}"
        case "ghost", "dead":
            return DEAD_CHAR, f"{bold_prefix}{DEAD_STYLE}"
        case "ghost", _:
            color = GHOST_COLORS[ghost_index % len(GHOST_COLORS)]
            return GHOST_CHAR, f"{bold_prefix}{color}"
        case _:
            return EMPTY, ""


def render_grid(game_map: GameMap, state: State, my_id: str) -> Text:
    """Render the game grid as a Rich Text object.

    Overlays remaining dots, pellets, and player positions onto the cached
    map. The player matching my_id is rendered with bold styling.

    Args:
        game_map: The game map from round_start.
        state: The current game state from a state tick.
        my_id: The local player's ID for bold highlighting.

    Returns:
        A Rich Text object representing the full game grid.
    """
    # Build lookup sets for remaining collectibles from state
    remaining_dots: set[tuple[int, int]] = {(p.x, p.y) for p in state.dots}
    remaining_pellets: set[tuple[int, int]] = {(p.x, p.y) for p in state.power_pellets}

    # Build player position lookup: (x, y) -> list of players at that position
    player_positions: dict[tuple[int, int], list[StatePlayer]] = {}
    for player in state.players:
        key = (player.position.x, player.position.y)
        player_positions.setdefault(key, [])
        player_positions[key].append(player)

    # Assign ghost indices for color differentiation
    ghost_indices: dict[str, int] = {}
    ghost_counter = 0
    for player in state.players:
        if player.role == "ghost":
            ghost_indices[player.id] = ghost_counter
            ghost_counter += 1

    result = Text()

    for y in range(game_map.height):
        for x in range(game_map.width):
            pos_key = (x, y)

            # Check for players at this position first (players overlay everything)
            if pos_key in player_positions:
                # Render the first (highest priority) player at this position
                # Priority: pacman > ghost active > ghost vulnerable > respawning > dead
                players_here = player_positions[pos_key]
                player = _pick_display_player(players_here)
                ghost_idx = ghost_indices.get(player.id, 0)
                chars, style = _player_style(player, my_id, ghost_idx)
                result.append(chars, style=style)
                continue

            # Check collectibles from state (not from original map)
            cell = game_map.cells[y][x]

            if pos_key in remaining_dots:
                result.append(DOT, style=DOT_STYLE)
            elif pos_key in remaining_pellets:
                result.append(POWER_PELLET, style=POWER_PELLET_STYLE)
            elif cell == "wall":
                result.append(WALL, style=WALL_STYLE)
            else:
                # Empty, spawn cells, or consumed collectibles
                result.append(EMPTY)

        # Add newline after each row (except the last)
        if y < game_map.height - 1:
            result.append("\n")

    return result


def _pick_display_player(players: list[StatePlayer]) -> StatePlayer:
    """Pick which player to display when multiple occupy the same cell.

    Priority order: active pacman > active ghost > vulnerable ghost >
    respawning > dead.

    Args:
        players: List of players at the same position.

    Returns:
        The player that should be displayed.
    """
    priority = {"active": 0, "vulnerable": 1, "respawning": 2, "dead": 3}

    def sort_key(p: StatePlayer) -> tuple[int, int]:
        # Pacman has higher display priority than ghost
        role_priority = 0 if p.role == "pacman" else 1
        status_priority = priority.get(p.status, 4)
        return (status_priority, role_priority)

    return sorted(players, key=sort_key)[0]
