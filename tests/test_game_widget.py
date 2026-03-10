"""Tests for the game widget."""

from __future__ import annotations

import pytest
from rich.text import Text
from textual.app import App, ComposeResult

from pacman.models import GameMap, Position, State, StatePlayer
from pacman.widgets.game import (
    GameWidget,
    _merge_grid_and_sidebar,
    _split_text_lines,
)

# --- Test helpers ---


def _make_map(width: int = 3, height: int = 3) -> GameMap:
    """Create a small test map."""
    cells = [
        ["wall", "dot", "wall"],
        ["dot", "empty", "dot"],
        ["wall", "dot", "wall"],
    ]
    return GameMap(width=width, height=height, cells=cells)


def _make_player(
    name: str,
    player_id: str,
    role: str = "pacman",
    status: str = "active",
    score: int = 0,
    x: int = 1,
    y: int = 1,
) -> StatePlayer:
    """Create a StatePlayer for testing."""
    return StatePlayer(
        id=player_id,
        name=name,
        role=role,
        position=Position(x=x, y=y),
        status=status,
        score=score,
    )


def _make_state(
    players: list[StatePlayer] | None = None,
    tick: int = 42,
    time_elapsed: float = 15.5,
) -> State:
    """Create a State for testing."""
    if players is None:
        players = [_make_player("Alice", "p1", "pacman", score=100)]
    return State(
        tick=tick,
        players=players,
        dots=[Position(x=1, y=0), Position(x=1, y=2)],
        power_pellets=[],
        time_elapsed=time_elapsed,
    )


# --- _render_game tests (no Textual app needed) ---


class TestRenderGameDirect:
    """Test _render_game output directly without mounting the widget."""

    def test_no_data_shows_waiting_message(self) -> None:
        widget = GameWidget()
        text = widget._render_game()
        assert "Waiting for game data..." in text.plain

    def test_with_map_but_no_state_shows_waiting(self) -> None:
        widget = GameWidget()
        widget.set_map(_make_map(), "p1", "pacman")
        text = widget._render_game()
        assert "Waiting for game data..." in text.plain

    def test_with_state_but_no_map_shows_waiting(self) -> None:
        widget = GameWidget()
        widget._state = _make_state()
        text = widget._render_game()
        assert "Waiting for game data..." in text.plain

    def test_renders_grid_when_data_available(self) -> None:
        widget = GameWidget()
        widget.set_map(_make_map(), "p1", "pacman")
        widget._state = _make_state()
        text = widget._render_game()
        # Should contain wall characters from the grid
        assert "██" in text.plain

    def test_renders_scoreboard_when_data_available(self) -> None:
        widget = GameWidget()
        widget.set_map(_make_map(), "p1", "pacman")
        widget._state = _make_state()
        text = widget._render_game()
        assert "SCOREBOARD" in text.plain

    def test_renders_status_line_when_data_available(self) -> None:
        widget = GameWidget()
        widget.set_map(_make_map(), "p1", "pacman")
        widget._state = _make_state(tick=42, time_elapsed=15.5)
        text = widget._render_game()
        assert "Tick: 42" in text.plain

    def test_grid_contains_player_character(self) -> None:
        widget = GameWidget()
        widget.set_map(_make_map(), "p1", "pacman")
        widget._state = _make_state()
        text = widget._render_game()
        # Pacman character should appear in the grid
        assert "ᗧ" in text.plain


# --- Scoreboard tests ---


class TestRenderScoreboard:
    """Test the scoreboard rendering."""

    def test_scoreboard_header(self) -> None:
        widget = GameWidget()
        widget._state = _make_state()
        text = widget._render_scoreboard()
        assert "SCOREBOARD" in text.plain

    def test_scoreboard_separator(self) -> None:
        widget = GameWidget()
        widget._state = _make_state()
        text = widget._render_scoreboard()
        assert "──────────────────" in text.plain

    def test_shows_player_name(self) -> None:
        widget = GameWidget()
        widget._my_id = "p1"
        widget._state = _make_state()
        text = widget._render_scoreboard()
        assert "Alice" in text.plain

    def test_shows_player_score(self) -> None:
        widget = GameWidget()
        widget._my_id = "p1"
        widget._state = _make_state(players=[_make_player("Alice", "p1", score=150)])
        text = widget._render_scoreboard()
        assert "150" in text.plain

    def test_shows_role_label(self) -> None:
        widget = GameWidget()
        widget._my_id = "p1"
        widget._state = _make_state()
        text = widget._render_scoreboard()
        assert "[PACMAN]" in text.plain

    def test_ghost_role_label(self) -> None:
        widget = GameWidget()
        widget._my_id = "p1"
        widget._state = _make_state(
            players=[_make_player("Bob", "p2", role="ghost", score=50)]
        )
        text = widget._render_scoreboard()
        assert "[GHOST]" in text.plain

    def test_sorted_by_score_descending(self) -> None:
        widget = GameWidget()
        widget._my_id = "p1"
        players = [
            _make_player("Low", "p1", score=10),
            _make_player("High", "p2", role="ghost", score=200),
            _make_player("Mid", "p3", role="ghost", score=50),
        ]
        widget._state = _make_state(players=players)
        text = widget._render_scoreboard()
        plain = text.plain
        # High should appear before Mid, Mid before Low
        high_pos = plain.index("High")
        mid_pos = plain.index("Mid")
        low_pos = plain.index("Low")
        assert high_pos < mid_pos < low_pos

    def test_current_player_marker(self) -> None:
        widget = GameWidget()
        widget._my_id = "p1"
        widget._state = _make_state()
        text = widget._render_scoreboard()
        assert "> " in text.plain

    def test_non_active_status_shown(self) -> None:
        widget = GameWidget()
        widget._my_id = "p1"
        widget._state = _make_state(
            players=[_make_player("Ghost1", "p2", role="ghost", status="dead", score=0)]
        )
        text = widget._render_scoreboard()
        assert "(dead)" in text.plain

    def test_active_status_not_shown(self) -> None:
        widget = GameWidget()
        widget._my_id = "p1"
        widget._state = _make_state(players=[_make_player("Alice", "p1", score=100)])
        text = widget._render_scoreboard()
        assert "(active)" not in text.plain

    def test_no_state_returns_header_only(self) -> None:
        widget = GameWidget()
        text = widget._render_scoreboard()
        plain = text.plain
        assert "SCOREBOARD" in plain
        # Should not contain any player names
        assert "Alice" not in plain


# --- Status line tests ---


class TestRenderStatusLine:
    """Test the status line rendering."""

    def test_shows_tick_count(self) -> None:
        widget = GameWidget()
        widget._my_role = "pacman"
        widget._state = _make_state(tick=99)
        text = widget._render_status_line()
        assert "Tick: 99" in text.plain

    def test_shows_role(self) -> None:
        widget = GameWidget()
        widget._my_role = "pacman"
        widget._state = _make_state()
        text = widget._render_status_line()
        assert "PACMAN" in text.plain

    def test_shows_ghost_role(self) -> None:
        widget = GameWidget()
        widget._my_role = "ghost"
        widget._state = _make_state()
        text = widget._render_status_line()
        assert "GHOST" in text.plain

    def test_shows_time_elapsed(self) -> None:
        widget = GameWidget()
        widget._my_role = "pacman"
        widget._state = _make_state(time_elapsed=65.0)
        text = widget._render_status_line()
        # 65 seconds = 1:05
        assert "Time: 1:05" in text.plain

    def test_shows_zero_time(self) -> None:
        widget = GameWidget()
        widget._my_role = "pacman"
        widget._state = _make_state(time_elapsed=0.0)
        text = widget._render_status_line()
        assert "Time: 0:00" in text.plain

    def test_no_state_returns_empty(self) -> None:
        widget = GameWidget()
        text = widget._render_status_line()
        assert text.plain == ""

    def test_separators_present(self) -> None:
        widget = GameWidget()
        widget._my_role = "pacman"
        widget._state = _make_state()
        text = widget._render_status_line()
        assert "|" in text.plain


# --- set_map tests ---


class TestSetMap:
    """Test the set_map method."""

    def test_stores_game_map(self) -> None:
        widget = GameWidget()
        game_map = _make_map()
        widget.set_map(game_map, "p1", "pacman")
        assert widget._game_map is game_map

    def test_stores_my_id(self) -> None:
        widget = GameWidget()
        widget.set_map(_make_map(), "my-id", "pacman")
        assert widget._my_id == "my-id"

    def test_stores_my_role(self) -> None:
        widget = GameWidget()
        widget.set_map(_make_map(), "p1", "ghost")
        assert widget._my_role == "ghost"


# --- _merge_grid_and_sidebar tests ---


class TestMergeGridAndSidebar:
    """Test the grid/sidebar merge utility."""

    def test_combines_grid_and_sidebar(self) -> None:
        grid = Text("AB\nCD")
        sidebar = Text("12\n34")
        result = _merge_grid_and_sidebar(grid, sidebar)
        plain = result.plain
        # Each line should have grid, separator, sidebar
        lines = plain.split("\n")
        assert len(lines) == 2
        assert "AB" in lines[0]
        assert "12" in lines[0]
        assert "CD" in lines[1]
        assert "34" in lines[1]

    def test_grid_lines_padded_to_same_width(self) -> None:
        grid = Text("ABCD\nEF")
        sidebar = Text("1\n2")
        result = _merge_grid_and_sidebar(grid, sidebar)
        lines = result.plain.split("\n")
        # Both lines should have the same format
        # First line: ABCD  |  1
        # Second line: EF    |  2 (EF padded to 4 chars)
        sep_pos_0 = lines[0].index("|")
        sep_pos_1 = lines[1].index("|")
        assert sep_pos_0 == sep_pos_1

    def test_handles_more_sidebar_lines(self) -> None:
        grid = Text("AB")
        sidebar = Text("1\n2\n3")
        result = _merge_grid_and_sidebar(grid, sidebar)
        lines = result.plain.split("\n")
        assert len(lines) == 3

    def test_handles_more_grid_lines(self) -> None:
        grid = Text("AB\nCD\nEF")
        sidebar = Text("1")
        result = _merge_grid_and_sidebar(grid, sidebar)
        lines = result.plain.split("\n")
        assert len(lines) == 3

    def test_separator_present(self) -> None:
        grid = Text("AB")
        sidebar = Text("12")
        result = _merge_grid_and_sidebar(grid, sidebar)
        assert "|" in result.plain


# --- _split_text_lines tests ---


class TestSplitTextLines:
    """Test the text line splitting utility."""

    def test_single_line(self) -> None:
        text = Text("hello")
        lines = _split_text_lines(text)
        assert len(lines) == 1
        assert lines[0].plain == "hello"

    def test_multiple_lines(self) -> None:
        text = Text("a\nb\nc")
        lines = _split_text_lines(text)
        assert len(lines) == 3
        assert lines[0].plain == "a"
        assert lines[1].plain == "b"
        assert lines[2].plain == "c"

    def test_preserves_styles(self) -> None:
        text = Text()
        text.append("red", style="red")
        text.append("\n")
        text.append("blue", style="blue")
        lines = _split_text_lines(text)
        assert len(lines) == 2
        assert lines[0].plain == "red"
        assert lines[1].plain == "blue"


# --- Textual integration tests ---


def _make_test_app() -> App[None]:
    """Create a minimal Textual app with a GameWidget for testing."""

    class TestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield GameWidget()

    return TestApp()


@pytest.mark.asyncio
async def test_game_widget_mounts() -> None:
    """Test that the widget mounts successfully."""
    async with _make_test_app().run_test() as pilot:
        widget = pilot.app.query_one(GameWidget)
        assert widget is not None


@pytest.mark.asyncio
async def test_game_widget_update_state_in_app() -> None:
    """Test that update_state works within a running Textual app."""
    async with _make_test_app().run_test() as pilot:
        widget = pilot.app.query_one(GameWidget)
        widget.set_map(_make_map(), "p1", "pacman")
        widget.update_state(_make_state())
        await pilot.pause()
        # Verify state was stored
        assert widget._state is not None
        assert widget._state.tick == 42


@pytest.mark.asyncio
async def test_game_widget_renders_after_update() -> None:
    """Test that the widget renders correctly after update_state."""
    async with _make_test_app().run_test() as pilot:
        widget = pilot.app.query_one(GameWidget)
        widget.set_map(_make_map(), "p1", "pacman")
        widget.update_state(_make_state())
        await pilot.pause()
        # Render should now contain game data
        text = widget._render_game()
        assert "SCOREBOARD" in text.plain
        assert "Tick: 42" in text.plain


@pytest.mark.asyncio
async def test_game_widget_multiple_state_updates() -> None:
    """Test that multiple state updates work correctly."""
    async with _make_test_app().run_test() as pilot:
        widget = pilot.app.query_one(GameWidget)
        widget.set_map(_make_map(), "p1", "pacman")
        widget.update_state(_make_state(tick=1))
        await pilot.pause()
        widget.update_state(_make_state(tick=2))
        await pilot.pause()
        assert widget._state is not None
        assert widget._state.tick == 2
