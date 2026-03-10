# Pacman TUI Client

## Overview
- Build a terminal-based Pacman game client in Python using Textual + websockets
- Connects to the game server via WebSocket, renders the game state in a TUI with Unicode + color
- Single-screen architecture: swaps between lobby and game widgets based on connection phase
- Minimal viable scope: connect, join, render grid, play with arrow keys, show scores

## Context (from discovery)
- Specs in `docs/specs/`: protocol.md, game-rules.md, map-format.md, connection-guide.md
- Server endpoint: `ws://<host>/ws`, JSON over WebSocket, server-authoritative
- Client sends 2 message types: `join`, `input`
- Client receives 6 message types: `welcome`, `lobby`, `round_start`, `state`, `round_end`, `error`
- Map is 21x21 grid, cells indexed as `cells[y][x]`, 6 cell types
- Tick rate: 20/sec (50ms per tick), full state each tick (no deltas)
- No existing source code — greenfield project

## Development Approach
- **Testing approach**: Regular (code first, then tests)
- Complete each task fully before moving to the next
- Make small, focused changes
- **CRITICAL: every task MUST include new/updated tests** for code changes in that task
- **CRITICAL: all tests must pass before starting next task**
- **CRITICAL: update this plan file when scope changes during implementation**
- Run tests after each change

## Testing Strategy
- **Unit tests**: required for every task
- Focus on: message parsing, renderer output, client state transitions
- Mock WebSocket connections for client tests
- Use textual's testing utilities (pilot) for widget tests where practical

## Progress Tracking
- Mark completed items with `[x]` immediately when done
- Add newly discovered tasks with + prefix
- Document issues/blockers with warning prefix
- Update plan if implementation deviates from original scope

## Implementation Steps

### Task 1: Project scaffolding
- [x] Create `pyproject.toml` with dependencies (textual, websockets) and project metadata
- [x] Create `src/pacman/__init__.py` and `src/pacman/__main__.py` entry point (accepts `--host` arg)
- [x] Create `tests/` directory with `conftest.py`
- [x] Install project in dev mode, verify `python -m pacman --help` runs
- [x] Run tests (empty suite) — must pass before next task

### Task 2: Protocol models
- [x] Create `src/pacman/models.py` with dataclasses for all 6 server message types: `Welcome`, `Lobby`, `RoundStart`, `State`, `RoundEnd`, `Error`
- [x] Add nested dataclasses: `Player`, `RoundPlayer`, `StatePlayer`, `GameMap`, `GameConfig`, `Position`
- [x] Add `parse_message(data: dict) -> ServerMessage` function that dispatches on `type` field
- [x] Write tests for `parse_message` — all 6 message types with realistic payloads
- [x] Write tests for edge cases (unknown type, missing fields)
- [x] Run tests — must pass before next task

### Task 3: WebSocket client
- [x] Create `src/pacman/client.py` with `PacmanClient` class
- [x] Implement `connect(url)`, `close()`, `join(name)`, `send_direction(direction)`
- [x] Implement `messages()` async generator that yields parsed `ServerMessage` objects
- [x] Add direction dedup logic (don't send if same as last direction)
- [x] Write tests for client methods using mocked websocket (verify JSON sent, messages parsed)
- [x] Write tests for direction dedup behavior
- [x] Run tests — must pass before next task

### Task 4: Grid renderer
- [x] Create `src/pacman/renderer.py` with `render_grid(game_map, state, my_id) -> Text` function
- [x] Implement cell rendering: wall (blue `██`), dot (white `··`), power pellet (bright `●●`), empty (`  `)
- [x] Overlay remaining dots/pellets from state (not original map)
- [x] Overlay player positions: pacman (yellow `ᗧ`), ghost (colored `ᗣ`), dead (gray `✕`), vulnerable ghost (blue `ᗣ`), respawning (gray `··`)
- [x] Highlight own player with bold styling
- [x] Write tests for render_grid with a small test map (verify correct characters and styles at known positions)
- [x] Write tests for player overlay (active, dead, vulnerable, respawning states)
- [x] Run tests — must pass before next task

### Task 5: Lobby widget
- [x] Create `src/pacman/widgets/lobby.py` with `LobbyWidget(Static)` that displays player list and "Waiting for round..." status
- [x] Accept player list updates via a method (e.g., `update_players(players)`)
- [x] Write tests for lobby widget rendering (shows player names, correct count)
- [x] Run tests — must pass before next task

### Task 6: Game widget
- [x] Create `src/pacman/widgets/game.py` with `GameWidget(Static)` that displays the rendered grid
- [x] Add scoreboard sidebar: player names, scores, roles, sorted by score
- [x] Add status line: tick count, your role, time elapsed
- [x] Accept state updates via a method (e.g., `update_state(state)`)
- [x] Write tests for game widget (verify it calls renderer, shows scoreboard data)
- [x] Run tests — must pass before next task

### Task 7: Main app — wiring it all together
- [x] Create `src/pacman/app.py` with `PacmanApp(App)` class
- [x] Implement phase tracking: `connecting` → `lobby` → `playing` → `round_end` → `lobby`
- [x] Mount both lobby and game widgets; toggle visibility based on phase
- [x] Spawn WebSocket background worker on mount; dispatch messages to widgets
- [x] Bind arrow keys to `client.send_direction()`; bind `q` to quit
- [x] Handle `round_end`: show result briefly, then transition back to lobby
- [x] Write tests for app phase transitions using Textual's pilot testing
- [x] Run tests — must pass before next task

### Task 8: Error handling & reconnection
- [x] Add connection error handling: display "Cannot connect" status, retry with backoff (1s, 2s, 4s, max 10s)
- [x] Add disconnection handling: show "Disconnected", attempt reconnect + rejoin
- [x] Handle fatal server errors (server stopped, full, round in progress) — display message, enter reconnect loop
- [x] Handle non-fatal `error` messages — display in status bar briefly
- [x] Write tests for reconnection backoff logic
- [x] Write tests for error message handling
- [x] Run tests — must pass before next task

### Task 9: Verify acceptance criteria
- [x] Verify: connects via WebSocket and sends join
- [x] Verify: handles all 6 server message types
- [x] Verify: sends input direction changes on arrow keys
- [x] Verify: renders game state with Unicode + color
- [x] Verify: shows lobby between rounds
- [x] Run full test suite
- [x] Run linter (ruff) — all issues must be fixed

### Task 10: [Final] Update documentation
- [ ] Update README.md with: project description, install instructions, usage (`python -m pacman --host <host>`)
- [ ] Add screenshot or ASCII preview of the TUI if practical

## Technical Details

### Message Flow
```
App.mount() → spawn _ws_loop worker
  → client.connect(url)
  → client.join(name)
  → async for msg in client.messages():
      → post_message(GameEvent(msg))
        → LobbyWidget.on_game_event() or GameWidget.on_game_event()
```

### Key Data Structures
- `GameMap`: width, height, cells (list of list of str) — cached from round_start
- `StatePlayer`: id, name, role, position, status, score — from each state tick
- `Position`: x (column), y (row) — (0,0) is top-left

### Rendering
- Each cell = 2 characters wide for square aspect ratio
- Grid rendered as Rich `Text` object with styled spans
- Sidebar rendered as Rich `Table` or formatted text
- Players overlaid on grid at their position coordinates

## Post-Completion

**Manual verification:**
- Connect to a running game server and play a full round
- Verify rendering looks correct at different terminal sizes
- Test with multiple clients connected simultaneously
- Verify graceful behavior on server shutdown
