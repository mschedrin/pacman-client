"""Tests for the PacmanClient WebSocket client."""

import asyncio
import json
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest

from pacman.client import PacmanClient
from pacman.models import Error, Lobby, RoundEnd, RoundStart, State, Welcome

# --- Helpers ---


class FakeWebSocket:
    """A fake WebSocket connection for testing.

    Supports send(), close(), and async iteration over queued messages.
    """

    def __init__(self) -> None:
        self.sent: list[str] = []
        self._messages: asyncio.Queue[str | None] = asyncio.Queue()
        self.close_code: int | None = None
        self.closed: bool = False

    async def send(self, data: str) -> None:
        """Record sent messages."""
        self.sent.append(data)

    async def close(self) -> None:
        """Mark the connection as closed."""
        self.close_code = 1000
        self.closed = True
        # Signal the iterator to stop
        self._messages.put_nowait(None)

    def queue_message(self, data: dict | str) -> None:
        """Queue a message to be yielded by the async iterator."""
        if isinstance(data, dict):
            self._messages.put_nowait(json.dumps(data))
        else:
            self._messages.put_nowait(data)

    def queue_close(self) -> None:
        """Signal end of messages (simulates connection close)."""
        self._messages.put_nowait(None)

    def __aiter__(self) -> AsyncIterator[str]:
        return self

    async def __anext__(self) -> str:
        msg = await self._messages.get()
        if msg is None:
            raise StopAsyncIteration
        return msg


# --- Fixtures ---


@pytest.fixture
def fake_ws() -> FakeWebSocket:
    """Create a fresh FakeWebSocket instance."""
    return FakeWebSocket()


@pytest.fixture
def client(fake_ws: FakeWebSocket) -> PacmanClient:
    """Create a PacmanClient with a pre-injected fake WebSocket."""
    c = PacmanClient()
    c._ws = fake_ws
    return c


# --- Connection tests ---


class TestConnect:
    """Tests for connect() and close()."""

    @pytest.mark.asyncio
    async def test_connect_sets_websocket(self) -> None:
        """connect() opens a websocket connection."""
        fake = FakeWebSocket()
        with patch(
            "pacman.client.websockets.connect", new_callable=AsyncMock
        ) as mock_connect:
            mock_connect.return_value = fake
            client = PacmanClient()
            await client.connect("ws://localhost:8000/ws")
            mock_connect.assert_called_once_with("ws://localhost:8000/ws")
            assert client.connected

    @pytest.mark.asyncio
    async def test_close_clears_websocket(self, client: PacmanClient) -> None:
        """close() closes the connection and clears state."""
        await client.close()
        assert not client.connected
        assert client._ws is None
        assert client._last_direction is None

    @pytest.mark.asyncio
    async def test_close_when_not_connected(self) -> None:
        """close() does nothing when not connected."""
        client = PacmanClient()
        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_connected_property_false_initially(self) -> None:
        """connected is False before connect() is called."""
        client = PacmanClient()
        assert not client.connected

    @pytest.mark.asyncio
    async def test_connected_property_false_after_close(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """connected is False after the connection has been closed."""
        fake_ws.close_code = 1000
        assert not client.connected


# --- Join tests ---


class TestJoin:
    """Tests for join()."""

    @pytest.mark.asyncio
    async def test_join_sends_correct_json(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """join() sends a JSON join message with the given name."""
        await client.join("TestPlayer")
        assert len(fake_ws.sent) == 1
        msg = json.loads(fake_ws.sent[0])
        assert msg == {"type": "join", "name": "TestPlayer"}

    @pytest.mark.asyncio
    async def test_join_raises_when_not_connected(self) -> None:
        """join() raises RuntimeError if not connected."""
        client = PacmanClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.join("Test")


# --- Direction / input tests ---


class TestSendDirection:
    """Tests for send_direction() and direction dedup."""

    @pytest.mark.asyncio
    async def test_send_direction_sends_input_message(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """send_direction() sends a JSON input message."""
        await client.send_direction("up")
        assert len(fake_ws.sent) == 1
        msg = json.loads(fake_ws.sent[0])
        assert msg == {"type": "input", "direction": "up"}

    @pytest.mark.asyncio
    async def test_send_direction_dedup_same(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """send_direction() doesn't resend the same direction."""
        await client.send_direction("left")
        await client.send_direction("left")
        await client.send_direction("left")
        assert len(fake_ws.sent) == 1

    @pytest.mark.asyncio
    async def test_send_direction_dedup_different(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """send_direction() sends when direction changes."""
        await client.send_direction("up")
        await client.send_direction("down")
        await client.send_direction("left")
        await client.send_direction("right")
        assert len(fake_ws.sent) == 4
        directions = [json.loads(s)["direction"] for s in fake_ws.sent]
        assert directions == ["up", "down", "left", "right"]

    @pytest.mark.asyncio
    async def test_send_direction_dedup_after_change(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """Sending same direction after a change is suppressed."""
        await client.send_direction("up")
        await client.send_direction("down")
        await client.send_direction("down")
        assert len(fake_ws.sent) == 2

    @pytest.mark.asyncio
    async def test_send_direction_raises_when_not_connected(self) -> None:
        """send_direction() raises RuntimeError if not connected."""
        client = PacmanClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            await client.send_direction("up")

    @pytest.mark.asyncio
    async def test_reset_direction_allows_resend(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """After reset_direction(), the same direction can be sent again."""
        await client.send_direction("up")
        client.reset_direction()
        await client.send_direction("up")
        assert len(fake_ws.sent) == 2

    @pytest.mark.asyncio
    async def test_send_direction_not_advanced_on_failure(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """_last_direction is not updated when _send() raises, allowing retry."""
        # Make send raise after the first successful call
        await client.send_direction("up")
        assert len(fake_ws.sent) == 1

        # Now make send fail
        original_send = fake_ws.send

        async def failing_send(data: str) -> None:
            raise ConnectionError("socket closed")

        fake_ws.send = failing_send  # type: ignore[assignment]

        with pytest.raises(ConnectionError):
            await client.send_direction("right")

        # _last_direction should still be "up" since the send failed
        assert client._last_direction == "up"

        # Restore send and retry — should succeed because dedup was not advanced
        fake_ws.send = original_send
        await client.send_direction("right")
        assert len(fake_ws.sent) == 2
        msg = json.loads(fake_ws.sent[1])
        assert msg == {"type": "input", "direction": "right"}

    @pytest.mark.asyncio
    async def test_close_resets_direction(self, fake_ws: FakeWebSocket) -> None:
        """close() resets the direction dedup state."""
        client = PacmanClient()
        client._ws = fake_ws
        await client.send_direction("right")
        await client.close()

        # Reconnect with a new fake
        new_ws = FakeWebSocket()
        client._ws = new_ws
        await client.send_direction("right")
        assert len(new_ws.sent) == 1


# --- Messages iterator tests ---


class TestMessages:
    """Tests for the messages() async generator."""

    @pytest.mark.asyncio
    async def test_messages_yields_welcome(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """messages() parses and yields a Welcome message."""
        fake_ws.queue_message(
            {
                "type": "welcome",
                "id": "abc-123",
                "name": "TestPlayer",
                "players": [
                    {
                        "id": "abc-123",
                        "name": "TestPlayer",
                        "status": "lobby",
                        "role": None,
                        "position": None,
                        "direction": None,
                    }
                ],
            }
        )
        fake_ws.queue_close()

        msgs = []
        async for msg in client.messages():
            msgs.append(msg)

        assert len(msgs) == 1
        assert isinstance(msgs[0], Welcome)
        assert msgs[0].id == "abc-123"
        assert msgs[0].name == "TestPlayer"

    @pytest.mark.asyncio
    async def test_messages_yields_lobby(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """messages() parses and yields a Lobby message."""
        fake_ws.queue_message(
            {
                "type": "lobby",
                "players": [
                    {
                        "id": "p1",
                        "name": "Player1",
                        "status": "lobby",
                        "role": None,
                        "position": None,
                        "direction": None,
                    },
                    {
                        "id": "p2",
                        "name": "Player2",
                        "status": "lobby",
                        "role": None,
                        "position": None,
                        "direction": None,
                    },
                ],
            }
        )
        fake_ws.queue_close()

        msgs = []
        async for msg in client.messages():
            msgs.append(msg)

        assert len(msgs) == 1
        assert isinstance(msgs[0], Lobby)
        assert len(msgs[0].players) == 2

    @pytest.mark.asyncio
    async def test_messages_yields_state(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """messages() parses and yields a State message."""
        fake_ws.queue_message(
            {
                "type": "state",
                "tick": 42,
                "players": [
                    {
                        "id": "p1",
                        "name": "Player1",
                        "role": "pacman",
                        "position": {"x": 5, "y": 3},
                        "status": "active",
                        "score": 12,
                    }
                ],
                "dots": [[1, 1], [2, 3]],
                "powerPellets": [[1, 19]],
                "timeElapsed": 2.1,
            }
        )
        fake_ws.queue_close()

        msgs = []
        async for msg in client.messages():
            msgs.append(msg)

        assert len(msgs) == 1
        assert isinstance(msgs[0], State)
        assert msgs[0].tick == 42

    @pytest.mark.asyncio
    async def test_messages_yields_round_end(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """messages() parses and yields a RoundEnd message."""
        fake_ws.queue_message(
            {
                "type": "round_end",
                "result": "pacman",
                "scores": {"p1": 45, "p2": 2},
            }
        )
        fake_ws.queue_close()

        msgs = []
        async for msg in client.messages():
            msgs.append(msg)

        assert len(msgs) == 1
        assert isinstance(msgs[0], RoundEnd)
        assert msgs[0].result == "pacman"

    @pytest.mark.asyncio
    async def test_messages_yields_error(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """messages() parses and yields an Error message."""
        fake_ws.queue_message({"type": "error", "message": "Name is required"})
        fake_ws.queue_close()

        msgs = []
        async for msg in client.messages():
            msgs.append(msg)

        assert len(msgs) == 1
        assert isinstance(msgs[0], Error)
        assert msgs[0].message == "Name is required"

    @pytest.mark.asyncio
    async def test_messages_multiple_messages(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """messages() yields multiple messages in order."""
        fake_ws.queue_message(
            {
                "type": "welcome",
                "id": "abc",
                "name": "P1",
                "players": [
                    {
                        "id": "abc",
                        "name": "P1",
                        "status": "lobby",
                        "role": None,
                        "position": None,
                        "direction": None,
                    }
                ],
            }
        )
        fake_ws.queue_message(
            {
                "type": "lobby",
                "players": [
                    {
                        "id": "abc",
                        "name": "P1",
                        "status": "lobby",
                        "role": None,
                        "position": None,
                        "direction": None,
                    }
                ],
            }
        )
        fake_ws.queue_message({"type": "error", "message": "test error"})
        fake_ws.queue_close()

        msgs = []
        async for msg in client.messages():
            msgs.append(msg)

        assert len(msgs) == 3
        assert isinstance(msgs[0], Welcome)
        assert isinstance(msgs[1], Lobby)
        assert isinstance(msgs[2], Error)

    @pytest.mark.asyncio
    async def test_messages_skips_pong(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """messages() skips keepalive 'pong' responses."""
        fake_ws.queue_message("pong")
        fake_ws.queue_message({"type": "error", "message": "hello"})
        fake_ws.queue_message("pong")
        fake_ws.queue_close()

        msgs = []
        async for msg in client.messages():
            msgs.append(msg)

        assert len(msgs) == 1
        assert isinstance(msgs[0], Error)

    @pytest.mark.asyncio
    async def test_messages_handles_bytes(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """messages() decodes bytes messages."""
        fake_ws._messages.put_nowait(
            json.dumps({"type": "error", "message": "bytes test"}).encode("utf-8")
        )
        fake_ws.queue_close()

        msgs = []
        async for msg in client.messages():
            msgs.append(msg)

        assert len(msgs) == 1
        assert isinstance(msgs[0], Error)
        assert msgs[0].message == "bytes test"

    @pytest.mark.asyncio
    async def test_messages_raises_when_not_connected(self) -> None:
        """messages() raises RuntimeError if not connected."""
        client = PacmanClient()
        with pytest.raises(RuntimeError, match="Not connected"):
            async for _ in client.messages():
                pass

    @pytest.mark.asyncio
    async def test_messages_yields_round_start(
        self, client: PacmanClient, fake_ws: FakeWebSocket
    ) -> None:
        """messages() parses and yields a RoundStart message."""
        fake_ws.queue_message(
            {
                "type": "round_start",
                "map": {
                    "width": 3,
                    "height": 3,
                    "cells": [
                        ["wall", "wall", "wall"],
                        ["wall", "dot", "wall"],
                        ["wall", "wall", "wall"],
                    ],
                },
                "role": "pacman",
                "players": [
                    {
                        "id": "p1",
                        "name": "Player1",
                        "role": "pacman",
                        "position": {"x": 1, "y": 1},
                    }
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
        )
        fake_ws.queue_close()

        msgs = []
        async for msg in client.messages():
            msgs.append(msg)

        assert len(msgs) == 1
        assert isinstance(msgs[0], RoundStart)
        assert msgs[0].role == "pacman"
        assert msgs[0].map.width == 3
