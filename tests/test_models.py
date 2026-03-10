"""Tests for protocol message parsing."""

import pytest

from pacman.models import (
    Error,
    GameConfig,
    GameMap,
    Lobby,
    Player,
    Position,
    RoundEnd,
    RoundPlayer,
    RoundStart,
    State,
    StatePlayer,
    Welcome,
    parse_message,
)

# --- Fixtures: realistic payloads matching the protocol spec ---

PLAYER_LOBBY = {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "TeamAwesome",
    "status": "lobby",
    "role": None,
    "position": None,
    "direction": None,
}

PLAYER_LOBBY_2 = {
    "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
    "name": "OtherTeam",
    "status": "lobby",
    "role": None,
    "position": None,
    "direction": None,
}


def make_welcome_data() -> dict:
    return {
        "type": "welcome",
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "TeamAwesome",
        "players": [PLAYER_LOBBY_2, PLAYER_LOBBY],
    }


def make_lobby_data() -> dict:
    return {
        "type": "lobby",
        "players": [PLAYER_LOBBY, PLAYER_LOBBY_2],
    }


def make_round_start_data() -> dict:
    return {
        "type": "round_start",
        "map": {
            "width": 21,
            "height": 21,
            "cells": [
                ["wall", "wall", "wall"],
                ["wall", "dot", "wall"],
                ["wall", "wall", "wall"],
            ],
        },
        "role": "pacman",
        "players": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "TeamAwesome",
                "role": "pacman",
                "position": {"x": 9, "y": 17},
            },
            {
                "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "name": "OtherTeam",
                "role": "ghost",
                "position": {"x": 8, "y": 6},
            },
        ],
        "config": {
            "tickRate": 20,
            "powerPelletDuration": 100,
            "ghostRespawnDelay": 60,
            "pacmanCount": 1,
            "maxPlayers": 10,
            "idleShutdownMinutes": 180,
        },
    }


def make_state_data() -> dict:
    return {
        "type": "state",
        "tick": 42,
        "players": [
            {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "name": "TeamAwesome",
                "role": "pacman",
                "position": {"x": 5, "y": 3},
                "status": "active",
                "score": 12,
            },
            {
                "id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
                "name": "OtherTeam",
                "role": "ghost",
                "position": {"x": 10, "y": 7},
                "status": "vulnerable",
                "score": 0,
            },
        ],
        "dots": [[1, 1], [1, 2], [2, 3]],
        "powerPellets": [[1, 19], [19, 1]],
        "timeElapsed": 2.1,
    }


def make_round_end_data() -> dict:
    return {
        "type": "round_end",
        "result": "pacman",
        "scores": {
            "550e8400-e29b-41d4-a716-446655440000": 45,
            "7c9e6679-7425-40de-944b-e07fc1f90ae7": 2,
        },
    }


def make_error_data() -> dict:
    return {
        "type": "error",
        "message": "Name is required",
    }


# --- Tests for all 6 message types ---


class TestParseWelcome:
    def test_parse_welcome(self) -> None:
        msg = parse_message(make_welcome_data())
        assert isinstance(msg, Welcome)
        assert msg.id == "550e8400-e29b-41d4-a716-446655440000"
        assert msg.name == "TeamAwesome"
        assert len(msg.players) == 2

    def test_welcome_players(self) -> None:
        msg = parse_message(make_welcome_data())
        assert isinstance(msg, Welcome)
        player = msg.players[1]
        assert isinstance(player, Player)
        assert player.id == "550e8400-e29b-41d4-a716-446655440000"
        assert player.name == "TeamAwesome"
        assert player.status == "lobby"
        assert player.role is None
        assert player.position is None
        assert player.direction is None


class TestParseLobby:
    def test_parse_lobby(self) -> None:
        msg = parse_message(make_lobby_data())
        assert isinstance(msg, Lobby)
        assert len(msg.players) == 2

    def test_lobby_players(self) -> None:
        msg = parse_message(make_lobby_data())
        assert isinstance(msg, Lobby)
        player = msg.players[0]
        assert player.id == "550e8400-e29b-41d4-a716-446655440000"
        assert player.name == "TeamAwesome"
        assert player.status == "lobby"


class TestParseRoundStart:
    def test_parse_round_start(self) -> None:
        msg = parse_message(make_round_start_data())
        assert isinstance(msg, RoundStart)
        assert msg.role == "pacman"
        assert len(msg.players) == 2

    def test_round_start_map(self) -> None:
        msg = parse_message(make_round_start_data())
        assert isinstance(msg, RoundStart)
        assert isinstance(msg.map, GameMap)
        assert msg.map.width == 21
        assert msg.map.height == 21
        assert msg.map.cells[0][0] == "wall"
        assert msg.map.cells[1][1] == "dot"

    def test_round_start_players(self) -> None:
        msg = parse_message(make_round_start_data())
        assert isinstance(msg, RoundStart)
        pacman = msg.players[0]
        assert isinstance(pacman, RoundPlayer)
        assert pacman.role == "pacman"
        assert isinstance(pacman.position, Position)
        assert pacman.position.x == 9
        assert pacman.position.y == 17

        ghost = msg.players[1]
        assert ghost.role == "ghost"
        assert ghost.position.x == 8
        assert ghost.position.y == 6

    def test_round_start_config(self) -> None:
        msg = parse_message(make_round_start_data())
        assert isinstance(msg, RoundStart)
        assert isinstance(msg.config, GameConfig)
        assert msg.config.tick_rate == 20
        assert msg.config.power_pellet_duration == 100
        assert msg.config.ghost_respawn_delay == 60
        assert msg.config.pacman_count == 1
        assert msg.config.max_players == 10
        assert msg.config.idle_shutdown_minutes == 180


class TestParseState:
    def test_parse_state(self) -> None:
        msg = parse_message(make_state_data())
        assert isinstance(msg, State)
        assert msg.tick == 42
        assert msg.time_elapsed == 2.1

    def test_state_players(self) -> None:
        msg = parse_message(make_state_data())
        assert isinstance(msg, State)
        assert len(msg.players) == 2

        pacman = msg.players[0]
        assert isinstance(pacman, StatePlayer)
        assert pacman.role == "pacman"
        assert pacman.status == "active"
        assert pacman.score == 12
        assert pacman.position.x == 5
        assert pacman.position.y == 3

        ghost = msg.players[1]
        assert ghost.role == "ghost"
        assert ghost.status == "vulnerable"
        assert ghost.score == 0

    def test_state_dots(self) -> None:
        msg = parse_message(make_state_data())
        assert isinstance(msg, State)
        assert len(msg.dots) == 3
        assert msg.dots[0] == Position(x=1, y=1)
        assert msg.dots[1] == Position(x=1, y=2)
        assert msg.dots[2] == Position(x=2, y=3)

    def test_state_power_pellets(self) -> None:
        msg = parse_message(make_state_data())
        assert isinstance(msg, State)
        assert len(msg.power_pellets) == 2
        assert msg.power_pellets[0] == Position(x=1, y=19)
        assert msg.power_pellets[1] == Position(x=19, y=1)

    def test_state_empty_dots(self) -> None:
        data = make_state_data()
        data["dots"] = []
        data["powerPellets"] = []
        msg = parse_message(data)
        assert isinstance(msg, State)
        assert msg.dots == []
        assert msg.power_pellets == []


class TestParseRoundEnd:
    def test_parse_round_end(self) -> None:
        msg = parse_message(make_round_end_data())
        assert isinstance(msg, RoundEnd)
        assert msg.result == "pacman"
        assert msg.scores["550e8400-e29b-41d4-a716-446655440000"] == 45
        assert msg.scores["7c9e6679-7425-40de-944b-e07fc1f90ae7"] == 2

    def test_round_end_ghosts_win(self) -> None:
        data = make_round_end_data()
        data["result"] = "ghosts"
        msg = parse_message(data)
        assert isinstance(msg, RoundEnd)
        assert msg.result == "ghosts"

    def test_round_end_cancelled(self) -> None:
        data = make_round_end_data()
        data["result"] = "cancelled"
        msg = parse_message(data)
        assert isinstance(msg, RoundEnd)
        assert msg.result == "cancelled"


class TestParseError:
    def test_parse_error(self) -> None:
        msg = parse_message(make_error_data())
        assert isinstance(msg, Error)
        assert msg.message == "Name is required"

    def test_parse_various_errors(self) -> None:
        for error_msg in [
            "Server is stopped",
            "Round in progress",
            "Name too long",
            "Already joined",
            "Server is full",
            "Must join first",
            "Invalid direction",
            "Unknown message type",
        ]:
            msg = parse_message({"type": "error", "message": error_msg})
            assert isinstance(msg, Error)
            assert msg.message == error_msg


# --- Edge case tests ---


class TestParseMessageEdgeCases:
    def test_unknown_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown message type: 'bogus'"):
            parse_message({"type": "bogus"})

    def test_missing_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown message type: None"):
            parse_message({"foo": "bar"})

    def test_missing_fields_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            parse_message({"type": "welcome"})

    def test_missing_nested_fields_raises_key_error(self) -> None:
        data = make_state_data()
        data["players"][0].pop("score")
        with pytest.raises(KeyError, match="score"):
            parse_message(data)

    def test_welcome_missing_players_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="players"):
            parse_message({"type": "welcome", "id": "abc", "name": "test"})

    def test_round_start_missing_config_raises_key_error(self) -> None:
        data = make_round_start_data()
        del data["config"]
        with pytest.raises(KeyError, match="config"):
            parse_message(data)
