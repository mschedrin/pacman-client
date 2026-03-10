"""Dataclasses for all server message types and the parse_message dispatcher."""

from dataclasses import dataclass
from typing import Any

# --- Shared / nested types ---


@dataclass
class Position:
    """Grid position with x (column) and y (row)."""

    x: int
    y: int


@dataclass
class Player:
    """Player in the lobby (welcome/lobby messages)."""

    id: str
    name: str
    status: str
    role: str | None = None
    position: Position | None = None
    direction: str | None = None


@dataclass
class RoundPlayer:
    """Player at round start with role and starting position."""

    id: str
    name: str
    role: str
    position: Position


@dataclass
class StatePlayer:
    """Player during gameplay with current position, status, and score."""

    id: str
    name: str
    role: str
    position: Position
    status: str
    score: int


@dataclass
class GameMap:
    """The game grid sent in round_start."""

    width: int
    height: int
    cells: list[list[str]]


@dataclass
class GameConfig:
    """Server configuration for a round."""

    tick_rate: int
    power_pellet_duration: int
    ghost_respawn_delay: int
    pacman_count: int
    max_players: int
    idle_shutdown_minutes: int


# --- Server message types ---


@dataclass
class Welcome:
    """Sent after a successful join."""

    id: str
    name: str
    players: list[Player]


@dataclass
class Lobby:
    """Broadcast when someone joins or leaves the lobby."""

    players: list[Player]


@dataclass
class RoundStart:
    """Sent when a round begins."""

    map: GameMap
    role: str
    players: list[RoundPlayer]
    config: GameConfig


@dataclass
class State:
    """Broadcast every tick during a round."""

    tick: int
    players: list[StatePlayer]
    dots: list[Position]
    power_pellets: list[Position]
    time_elapsed: float


@dataclass
class RoundEnd:
    """Broadcast when a round finishes."""

    result: str
    scores: dict[str, int]


@dataclass
class Error:
    """Sent when something goes wrong."""

    message: str


ServerMessage = Welcome | Lobby | RoundStart | State | RoundEnd | Error


def _parse_position(data: dict[str, Any]) -> Position:
    """Parse a position dict into a Position dataclass."""
    return Position(x=data["x"], y=data["y"])


def _parse_player(data: dict[str, Any]) -> Player:
    """Parse a lobby player dict into a Player dataclass."""
    pos = _parse_position(data["position"]) if data.get("position") else None
    return Player(
        id=data["id"],
        name=data["name"],
        status=data["status"],
        role=data.get("role"),
        position=pos,
        direction=data.get("direction"),
    )


def _parse_round_player(data: dict[str, Any]) -> RoundPlayer:
    """Parse a round player dict into a RoundPlayer dataclass."""
    return RoundPlayer(
        id=data["id"],
        name=data["name"],
        role=data["role"],
        position=_parse_position(data["position"]),
    )


def _parse_state_player(data: dict[str, Any]) -> StatePlayer:
    """Parse a state player dict into a StatePlayer dataclass."""
    return StatePlayer(
        id=data["id"],
        name=data["name"],
        role=data["role"],
        position=_parse_position(data["position"]),
        status=data["status"],
        score=data["score"],
    )


def _parse_game_map(data: dict[str, Any]) -> GameMap:
    """Parse a map dict into a GameMap dataclass."""
    return GameMap(
        width=data["width"],
        height=data["height"],
        cells=data["cells"],
    )


def _parse_game_config(data: dict[str, Any]) -> GameConfig:
    """Parse a config dict into a GameConfig dataclass."""
    return GameConfig(
        tick_rate=data["tickRate"],
        power_pellet_duration=data["powerPelletDuration"],
        ghost_respawn_delay=data["ghostRespawnDelay"],
        pacman_count=data["pacmanCount"],
        max_players=data["maxPlayers"],
        idle_shutdown_minutes=data["idleShutdownMinutes"],
    )


def parse_message(data: dict[str, Any]) -> ServerMessage:
    """Dispatch a raw JSON dict to the appropriate server message dataclass.

    Args:
        data: Parsed JSON dict with a "type" field.

    Returns:
        A typed ServerMessage dataclass instance.

    Raises:
        ValueError: If the message type is unknown.
        KeyError: If required fields are missing.
    """
    msg_type = data.get("type")

    match msg_type:
        case "welcome":
            return Welcome(
                id=data["id"],
                name=data["name"],
                players=[_parse_player(p) for p in data["players"]],
            )

        case "lobby":
            return Lobby(
                players=[_parse_player(p) for p in data["players"]],
            )

        case "round_start":
            return RoundStart(
                map=_parse_game_map(data["map"]),
                role=data["role"],
                players=[_parse_round_player(p) for p in data["players"]],
                config=_parse_game_config(data["config"]),
            )

        case "state":
            return State(
                tick=data["tick"],
                players=[_parse_state_player(p) for p in data["players"]],
                dots=[Position(x=d[0], y=d[1]) for d in data["dots"]],
                power_pellets=[Position(x=p[0], y=p[1]) for p in data["powerPellets"]],
                time_elapsed=data["timeElapsed"],
            )

        case "round_end":
            return RoundEnd(
                result=data["result"],
                scores=data["scores"],
            )

        case "error":
            return Error(message=data["message"])

        case _:
            raise ValueError(f"Unknown message type: {msg_type!r}")
