# AGENTS.md

## Project Overview

Multiplayer Pacman TUI client. Python + Textual + websockets. Connects to a
game server via WebSocket, renders the game in a terminal with Unicode + color.

Server specs are in `docs/specs/` (protocol, game rules, map format, connection
guide). Implementation plan is in `docs/plans/pacman-tui-client.md`.

## Project Structure

```
src/pacman/
├── __init__.py
├── __main__.py        # Entry point, --host/--name args
├── app.py             # Textual App, key bindings, WebSocket lifecycle
├── client.py          # WebSocket client (connect, send, receive, parse)
├── models.py          # Dataclasses for protocol messages
├── renderer.py        # Game state → Rich Text for grid widget
└── widgets/
    ├── __init__.py
    ├── lobby.py       # Lobby: player list, waiting status
    └── game.py        # Game: grid + scoreboard sidebar
tests/
├── conftest.py
└── ...
```

## Build & Run Commands

```bash
# Install (dev mode)
pip install -e ".[dev]"

# Run the client
python -m pacman --host localhost:8000

# Run all tests
pytest

# Run a single test file
pytest tests/test_models.py

# Run a single test function
pytest tests/test_models.py::test_parse_welcome -v

# Run tests matching a keyword
pytest -k "parse_message" -v

# Lint
ruff check .

# Format
ruff format .

# Lint + fix auto-fixable issues
ruff check --fix .

# Type check (if mypy is added)
mypy src/pacman/
```

## Code Style

### Python Version
- Python 3.12+. Use modern syntax (match statements, `X | Y` union types, etc.)

### Formatting & Linting
- **Formatter**: ruff format (88 char line length, default config)
- **Linter**: ruff check
- Fix all lint issues before committing. No `# noqa` without justification.

### Imports
- stdlib → third-party → local, separated by blank lines
- Use absolute imports: `from pacman.models import State`, not relative
- One import per line for `from` imports when there are more than 3 names

```python
import asyncio
import json
from dataclasses import dataclass

import websockets
from rich.text import Text
from textual.app import App

from pacman.models import ServerMessage, State
```

### Type Annotations
- All function signatures must have type annotations (params and return)
- Use `str | None` not `Optional[str]`
- Use `list[str]` not `List[str]` (lowercase generics)
- Dataclass fields must be typed

```python
def parse_message(data: dict[str, Any]) -> ServerMessage: ...
async def connect(self, url: str) -> None: ...
def render_grid(game_map: GameMap, state: State, my_id: str) -> Text: ...
```

### Naming Conventions
- `snake_case` for functions, methods, variables, modules
- `PascalCase` for classes and dataclasses
- `UPPER_SNAKE` for module-level constants
- Private methods/attrs prefixed with `_`

### Data Models
- Use `@dataclass` for protocol message types (not Pydantic, not TypedDict)
- Group related models: `Player`, `Position`, `GameMap`, `GameConfig`
- Union type `ServerMessage` for the 6 server message types
- Dispatcher function `parse_message()` for JSON → dataclass

### Async Patterns
- WebSocket client uses `async`/`await` throughout
- Background work via Textual `run_worker()`, not raw `asyncio.create_task()`
- `messages()` is an `AsyncIterator` yielding parsed dataclasses
- Direction dedup: only send if direction changed from last sent

### Error Handling
- WebSocket errors: catch, display status in UI, retry with backoff
- Protocol errors (server `error` messages): display briefly, don't crash
- Fatal disconnects: reconnect loop with exponential backoff (1s, 2s, 4s, max 10s)
- Never let exceptions propagate to crash the TUI — catch at the worker level

### Docstrings
- Required for public classes and functions
- Use Google-style docstrings (short summary, then Args/Returns if non-obvious)
- Skip docstrings for trivial/obvious methods (property getters, `__init__` with clear fields)

```python
def render_grid(game_map: GameMap, state: State, my_id: str) -> Text:
    """Render the game grid as a Rich Text object.

    Overlays remaining dots, pellets, and player positions onto the cached
    map. The player matching my_id is rendered with bold styling.
    """
```

## Testing

- **Framework**: pytest (with pytest-asyncio for async tests)
- **Location**: `tests/` directory, files named `test_*.py`
- **Approach**: code first, then tests. Every task must include tests.
- Tests must pass before moving to the next task.
- Mock WebSocket connections — don't require a running server.
- Use Textual's pilot (`async with app.run_test() as pilot`) for widget/app tests.
- Test both success and error/edge cases.

## Architecture Notes

- **Server-authoritative**: client only sends direction, server decides everything
- **Single-screen app**: one Textual `Screen`, widgets toggled by phase
- **Phases**: connecting → lobby → playing → round_end → lobby (cycle)
- **No deltas**: each `state` tick is the complete game state
- **Map caching**: parse map from `round_start`, reuse until next round
- **Rendering**: use `state.dots` and `state.powerPellets` for collectibles, not original map cells
- **Coordinates**: `cells[y][x]`, (0,0) is top-left, y increases downward
- **Cell width**: 2 characters per cell for square aspect ratio in terminal

## Key Specs Reference

- **Protocol** (`docs/specs/protocol.md`): 2 client messages (`join`, `input`), 6 server messages
- **Game rules** (`docs/specs/game-rules.md`): tick pipeline, collisions, win conditions
- **Map format** (`docs/specs/map-format.md`): 21×21 grid, 6 cell types, `cells[y][x]`
- **Connection** (`docs/specs/connection-guide.md`): lifecycle, errors, reconnection
