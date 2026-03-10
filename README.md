# Pacman TUI Client

Multiplayer Pacman client that runs in the terminal. Connects to a game server
via WebSocket, renders the game grid with Unicode characters and color, and
handles lobby/round lifecycle automatically.

Built with [Textual](https://textual.textualize.io/) and
[websockets](https://websockets.readthedocs.io/).

## Preview

```
 ████████████████████████████████████████
 ██· · · · ██          ██· · · · · · · ██
 ██· ████· ██· ██████· ██· ████· ████· ██
 ██· · · · · · · · · · · · · · · · · · ██
 ██· ████· ██████████████████· ██████· ██
 ██· · · · · · · ██· · · · · · · · · · ██
 ████████· ████· ██· ████████· ██████████
          · ██·         · ██·
 ████████· ██· ██ ᗣ ᗣ ██· ██· ██████████
 ██· · · · · · ██ ᗣ ᗣ ██· · · · · · · ██
 ██· ████· ██████████████████· ██████· ██
 ██· · ██· · · · ᗧ · · · · · · ██· · · ██
 ████· ██· ██████████████████· ██· ██████
 ██· · · · · · · ██· · · · · · · · · · ██
 ██· ████████████████████████████████· ██
 ██· · · · · · · · · · · · · · · · · · ██
 ████████████████████████████████████████

 Score: 120   Lives: 3   Tick: 42/200
```

- `██` walls
- `· ` dots
- `● ` power pellets
- `ᗧ ` your Pacman
- `ᗣ ` ghosts (color-coded)

## Requirements

- Python 3.12+
- A running Pacman game server

## Install

```bash
# Clone the repository
git clone <repo-url>
cd pacman-client

# Install in development mode
pip install -e ".[dev]"
```

## Usage

```bash
# Connect to a game server
python -m pacman --host localhost:8000

# Specify a player name
python -m pacman --host localhost:8000 --name MyTeam

# The host can also be a full WebSocket URL
python -m pacman --host ws://example.com/ws
```

### Controls

| Key              | Action          |
|------------------|-----------------|
| Arrow keys       | Change direction|
| `w a s d`        | Change direction|
| `q`              | Quit            |

## Architecture

The client is **server-authoritative** — it only sends direction input, and the
server decides everything else. The game phases cycle through:

```
connecting -> lobby -> playing -> round_end -> lobby -> ...
```

Each `state` tick from the server contains the complete game state (no deltas).
The client renders the full grid every tick.

## Project Structure

```
src/pacman/
  __main__.py        Entry point, --host/--name args
  app.py             Textual App, key bindings, WebSocket lifecycle
  client.py          WebSocket client (connect, send, receive, parse)
  models.py          Dataclasses for the 6 server message types
  renderer.py        Game state -> Rich Text for grid widget
  widgets/
    lobby.py         Lobby: player list, waiting status
    game.py          Game: grid + scoreboard sidebar
```

## Development

```bash
# Run all tests
pytest

# Run a single test file
pytest tests/test_models.py

# Lint
ruff check .

# Format
ruff format .

# Type check
mypy src/pacman/
```
