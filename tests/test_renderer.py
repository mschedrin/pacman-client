"""Tests for the grid renderer."""

from rich.text import Text

from pacman.models import GameMap, Position, State, StatePlayer
from pacman.renderer import (
    DEAD_CHAR,
    DEAD_STYLE,
    DOT,
    DOT_STYLE,
    EMPTY,
    GHOST_CHAR,
    GHOST_COLORS,
    PACMAN_CHAR,
    POWER_PELLET,
    POWER_PELLET_STYLE,
    RESPAWNING_CHAR,
    RESPAWNING_STYLE,
    VULNERABLE_GHOST_STYLE,
    WALL,
    WALL_STYLE,
    _cell_text,
    _pick_display_player,
    render_grid,
)

# --- Helper factories ---


def make_map(cells: list[list[str]]) -> GameMap:
    """Create a GameMap from a cells grid."""
    return GameMap(
        width=len(cells[0]) if cells else 0,
        height=len(cells),
        cells=cells,
    )


def make_state(
    players: list[StatePlayer] | None = None,
    dots: list[Position] | None = None,
    power_pellets: list[Position] | None = None,
    tick: int = 1,
) -> State:
    """Create a State with sensible defaults."""
    return State(
        tick=tick,
        players=players or [],
        dots=dots or [],
        power_pellets=power_pellets or [],
        time_elapsed=tick / 20.0,
    )


def make_player(
    id: str = "p1",
    name: str = "Player1",
    role: str = "pacman",
    x: int = 0,
    y: int = 0,
    status: str = "active",
    score: int = 0,
) -> StatePlayer:
    """Create a StatePlayer with sensible defaults."""
    return StatePlayer(
        id=id,
        name=name,
        role=role,
        position=Position(x=x, y=y),
        status=status,
        score=score,
    )


# --- _cell_text tests ---


class TestCellText:
    def test_wall(self) -> None:
        chars, style = _cell_text("wall")
        assert chars == WALL
        assert style == WALL_STYLE

    def test_dot(self) -> None:
        chars, style = _cell_text("dot")
        assert chars == DOT
        assert style == DOT_STYLE

    def test_power_pellet(self) -> None:
        chars, style = _cell_text("power_pellet")
        assert chars == POWER_PELLET
        assert style == POWER_PELLET_STYLE

    def test_empty(self) -> None:
        chars, style = _cell_text("empty")
        assert chars == EMPTY
        assert style == ""

    def test_pacman_spawn(self) -> None:
        chars, style = _cell_text("pacman_spawn")
        assert chars == EMPTY
        assert style == ""

    def test_ghost_spawn(self) -> None:
        chars, style = _cell_text("ghost_spawn")
        assert chars == EMPTY
        assert style == ""

    def test_unknown_cell(self) -> None:
        chars, style = _cell_text("unknown_type")
        assert chars == EMPTY
        assert style == ""


# --- render_grid basic cell tests ---


class TestRenderGridCells:
    def test_single_wall(self) -> None:
        game_map = make_map([["wall"]])
        state = make_state()
        result = render_grid(game_map, state, "me")
        assert result.plain == WALL

    def test_single_empty(self) -> None:
        game_map = make_map([["empty"]])
        state = make_state()
        result = render_grid(game_map, state, "me")
        assert result.plain == EMPTY

    def test_dot_in_state(self) -> None:
        """Dot is rendered when it appears in state.dots."""
        game_map = make_map([["dot"]])
        state = make_state(dots=[Position(x=0, y=0)])
        result = render_grid(game_map, state, "me")
        assert result.plain == DOT

    def test_dot_consumed(self) -> None:
        """Dot cell renders as empty when not in state.dots (consumed)."""
        game_map = make_map([["dot"]])
        state = make_state(dots=[])
        result = render_grid(game_map, state, "me")
        assert result.plain == EMPTY

    def test_power_pellet_in_state(self) -> None:
        """Power pellet renders when in state.power_pellets."""
        game_map = make_map([["power_pellet"]])
        state = make_state(power_pellets=[Position(x=0, y=0)])
        result = render_grid(game_map, state, "me")
        assert result.plain == POWER_PELLET

    def test_power_pellet_consumed(self) -> None:
        """Power pellet cell renders as empty when consumed."""
        game_map = make_map([["power_pellet"]])
        state = make_state(power_pellets=[])
        result = render_grid(game_map, state, "me")
        assert result.plain == EMPTY

    def test_spawn_cells_render_as_empty(self) -> None:
        """Spawn cells render as empty space."""
        game_map = make_map([["pacman_spawn", "ghost_spawn"]])
        state = make_state()
        result = render_grid(game_map, state, "me")
        assert result.plain == EMPTY + EMPTY

    def test_multirow_grid(self) -> None:
        """Multi-row grid has newlines between rows."""
        game_map = make_map([["wall", "empty"], ["empty", "wall"]])
        state = make_state()
        result = render_grid(game_map, state, "me")
        lines = result.plain.split("\n")
        assert len(lines) == 2
        assert lines[0] == WALL + EMPTY
        assert lines[1] == EMPTY + WALL

    def test_no_trailing_newline(self) -> None:
        """Grid does not end with a trailing newline."""
        game_map = make_map([["wall"], ["wall"]])
        state = make_state()
        result = render_grid(game_map, state, "me")
        assert not result.plain.endswith("\n")


class TestRenderGridStyles:
    def test_wall_has_blue_style(self) -> None:
        game_map = make_map([["wall"]])
        state = make_state()
        result = render_grid(game_map, state, "me")
        # Check that the wall text has the blue style
        spans = result._spans
        assert len(spans) == 1
        assert WALL_STYLE in str(spans[0].style)

    def test_dot_has_white_style(self) -> None:
        game_map = make_map([["dot"]])
        state = make_state(dots=[Position(x=0, y=0)])
        result = render_grid(game_map, state, "me")
        spans = result._spans
        assert len(spans) == 1
        assert DOT_STYLE in str(spans[0].style)

    def test_power_pellet_has_bright_style(self) -> None:
        game_map = make_map([["power_pellet"]])
        state = make_state(power_pellets=[Position(x=0, y=0)])
        result = render_grid(game_map, state, "me")
        spans = result._spans
        assert len(spans) == 1
        assert POWER_PELLET_STYLE in str(spans[0].style)


# --- Player overlay tests ---


class TestPlayerOverlay:
    def test_active_pacman(self) -> None:
        """Active pacman renders with pacman character and yellow style."""
        game_map = make_map([["empty"]])
        player = make_player(id="p1", role="pacman", status="active", x=0, y=0)
        state = make_state(players=[player])
        result = render_grid(game_map, state, "other")
        assert PACMAN_CHAR in result.plain
        spans = result._spans
        assert any("yellow" in str(s.style) for s in spans)

    def test_active_ghost(self) -> None:
        """Active ghost renders with ghost character and a color."""
        game_map = make_map([["empty"]])
        player = make_player(id="g1", role="ghost", status="active", x=0, y=0)
        state = make_state(players=[player])
        result = render_grid(game_map, state, "other")
        assert GHOST_CHAR in result.plain
        spans = result._spans
        # First ghost should get first color
        assert any(GHOST_COLORS[0] in str(s.style) for s in spans)

    def test_vulnerable_ghost(self) -> None:
        """Vulnerable ghost renders with ghost character and blue style."""
        game_map = make_map([["empty"]])
        player = make_player(id="g1", role="ghost", status="vulnerable", x=0, y=0)
        state = make_state(players=[player])
        result = render_grid(game_map, state, "other")
        assert GHOST_CHAR in result.plain
        spans = result._spans
        assert any(VULNERABLE_GHOST_STYLE in str(s.style) for s in spans)

    def test_dead_pacman(self) -> None:
        """Dead pacman renders with dead character and gray style."""
        game_map = make_map([["empty"]])
        player = make_player(id="p1", role="pacman", status="dead", x=0, y=0)
        state = make_state(players=[player])
        result = render_grid(game_map, state, "other")
        assert DEAD_CHAR in result.plain
        spans = result._spans
        assert any(DEAD_STYLE in str(s.style) for s in spans)

    def test_respawning_ghost(self) -> None:
        """Respawning ghost renders with respawning character and gray style."""
        game_map = make_map([["empty"]])
        player = make_player(id="g1", role="ghost", status="respawning", x=0, y=0)
        state = make_state(players=[player])
        result = render_grid(game_map, state, "other")
        assert RESPAWNING_CHAR in result.plain
        spans = result._spans
        assert any(RESPAWNING_STYLE in str(s.style) for s in spans)

    def test_own_player_bold(self) -> None:
        """Own player (my_id) gets bold styling."""
        game_map = make_map([["empty"]])
        player = make_player(id="me", role="pacman", status="active", x=0, y=0)
        state = make_state(players=[player])
        result = render_grid(game_map, state, "me")
        spans = result._spans
        assert any("bold" in str(s.style) for s in spans)

    def test_other_player_not_bold(self) -> None:
        """Other players do not get bold styling (unless inherent in style)."""
        game_map = make_map([["empty"]])
        player = make_player(id="other", role="pacman", status="active", x=0, y=0)
        state = make_state(players=[player])
        result = render_grid(game_map, state, "not-other")
        spans = result._spans
        # The yellow style itself doesn't contain "bold"
        assert not any("bold" in str(s.style) for s in spans)

    def test_player_overlays_dot(self) -> None:
        """Player at a dot position renders the player, not the dot."""
        game_map = make_map([["dot"]])
        player = make_player(id="p1", role="pacman", status="active", x=0, y=0)
        state = make_state(players=[player], dots=[Position(x=0, y=0)])
        result = render_grid(game_map, state, "other")
        assert PACMAN_CHAR in result.plain
        assert result.plain.count(DOT) == 0

    def test_player_overlays_wall(self) -> None:
        """Player at a wall position renders the player, not the wall."""
        # This shouldn't happen in practice but test overlay precedence
        game_map = make_map([["wall"]])
        player = make_player(id="p1", role="pacman", status="active", x=0, y=0)
        state = make_state(players=[player])
        result = render_grid(game_map, state, "other")
        assert PACMAN_CHAR in result.plain


class TestMultipleGhostColors:
    def test_ghosts_get_different_colors(self) -> None:
        """Multiple ghosts get different colors from the palette."""
        game_map = make_map([["empty", "empty", "empty"]])
        g1 = make_player(id="g1", role="ghost", status="active", x=0, y=0)
        g2 = make_player(id="g2", role="ghost", status="active", x=1, y=0)
        g3 = make_player(id="g3", role="ghost", status="active", x=2, y=0)
        state = make_state(players=[g1, g2, g3])
        result = render_grid(game_map, state, "other")

        # All three ghosts should be rendered
        assert result.plain.count("ᗣ") == 3

        # Check they have different color styles
        spans = result._spans
        styles = [str(s.style) for s in spans]
        # First three ghost colors should all appear
        assert any(GHOST_COLORS[0] in s for s in styles)
        assert any(GHOST_COLORS[1] in s for s in styles)
        assert any(GHOST_COLORS[2] in s for s in styles)


# --- _pick_display_player tests ---


class TestPickDisplayPlayer:
    def test_active_pacman_over_active_ghost(self) -> None:
        """Active pacman has priority over active ghost."""
        pacman = make_player(id="p1", role="pacman", status="active")
        ghost = make_player(id="g1", role="ghost", status="active")
        result = _pick_display_player([ghost, pacman])
        assert result.id == "p1"

    def test_active_over_dead(self) -> None:
        """Active player has priority over dead player."""
        alive = make_player(id="p1", role="ghost", status="active")
        dead = make_player(id="p2", role="pacman", status="dead")
        result = _pick_display_player([dead, alive])
        assert result.id == "p1"

    def test_active_over_vulnerable(self) -> None:
        """Active has priority over vulnerable."""
        active = make_player(id="p1", role="pacman", status="active")
        vuln = make_player(id="g1", role="ghost", status="vulnerable")
        result = _pick_display_player([vuln, active])
        assert result.id == "p1"

    def test_vulnerable_over_respawning(self) -> None:
        """Vulnerable has priority over respawning."""
        vuln = make_player(id="g1", role="ghost", status="vulnerable")
        resp = make_player(id="g2", role="ghost", status="respawning")
        result = _pick_display_player([resp, vuln])
        assert result.id == "g1"

    def test_single_player(self) -> None:
        """Single player is returned as-is."""
        player = make_player(id="p1")
        result = _pick_display_player([player])
        assert result.id == "p1"


# --- Integration test with realistic map ---


class TestRenderGridIntegration:
    def test_small_map_with_all_features(self) -> None:
        """Render a 5x3 map with walls, dots, pellets, and players."""
        cells = [
            ["wall", "wall", "wall", "wall", "wall"],
            ["wall", "dot", "empty", "power_pellet", "wall"],
            ["wall", "wall", "wall", "wall", "wall"],
        ]
        game_map = make_map(cells)
        pacman = make_player(id="me", role="pacman", status="active", x=2, y=1)
        ghost = make_player(id="g1", role="ghost", status="active", x=3, y=1)
        state = make_state(
            players=[pacman, ghost],
            dots=[Position(x=1, y=1)],
            power_pellets=[],  # pellet at (3,1) is consumed
        )
        result = render_grid(game_map, state, "me")
        lines = result.plain.split("\n")
        assert len(lines) == 3

        # Row 0: all walls
        assert lines[0] == WALL * 5

        # Row 1: wall, dot, pacman, ghost, wall
        assert lines[1] == WALL + DOT + PACMAN_CHAR + GHOST_CHAR + WALL

        # Row 2: all walls
        assert lines[2] == WALL * 5

    def test_returns_rich_text(self) -> None:
        """render_grid returns a Rich Text object."""
        game_map = make_map([["wall"]])
        state = make_state()
        result = render_grid(game_map, state, "me")
        assert isinstance(result, Text)

    def test_empty_map(self) -> None:
        """Empty map (0x0) produces empty text."""
        game_map = GameMap(width=0, height=0, cells=[])
        state = make_state()
        result = render_grid(game_map, state, "me")
        assert result.plain == ""

    def test_collectibles_from_state_not_map(self) -> None:
        """Only dots/pellets listed in state are rendered, not original map cells."""
        # Map has dots at (0,0) and (1,0), but state only has (0,0)
        cells = [["dot", "dot"]]
        game_map = make_map(cells)
        state = make_state(dots=[Position(x=0, y=0)])
        result = render_grid(game_map, state, "me")
        # First cell: dot, second cell: empty (consumed)
        assert result.plain == DOT + EMPTY

    def test_dead_ghost(self) -> None:
        """Dead ghost renders with dead character."""
        game_map = make_map([["empty"]])
        player = make_player(id="g1", role="ghost", status="dead", x=0, y=0)
        state = make_state(players=[player])
        result = render_grid(game_map, state, "other")
        assert DEAD_CHAR in result.plain
