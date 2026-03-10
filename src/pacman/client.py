"""WebSocket client for communicating with the Pacman game server."""

import json
from collections.abc import AsyncIterator

import websockets
from websockets.asyncio.client import ClientConnection

from pacman.models import ServerMessage, parse_message


class PacmanClient:
    """Manages a WebSocket connection to the Pacman game server.

    Handles connecting, sending join/input messages, and receiving
    parsed server messages as an async stream.
    """

    def __init__(self) -> None:
        self._ws: ClientConnection | None = None
        self._last_direction: str | None = None

    @property
    def connected(self) -> bool:
        """Whether the client has an open WebSocket connection."""
        return self._ws is not None and self._ws.close_code is None

    async def connect(self, url: str) -> None:
        """Open a WebSocket connection to the game server.

        Closes any stale connection before opening a new one to prevent
        resource leaks.

        Args:
            url: The WebSocket URL (e.g. ws://localhost:8000/ws).
        """
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None
        self._ws = await websockets.connect(url)
        self._last_direction = None

    async def close(self) -> None:
        """Close the WebSocket connection."""
        if self._ws is not None:
            ws = self._ws
            self._ws = None
            self._last_direction = None
            await ws.close()

    async def join(self, name: str) -> None:
        """Send a join message to register as a player.

        Args:
            name: The display name for this player (1-30 chars).

        Raises:
            RuntimeError: If not connected.
        """
        await self._send({"type": "join", "name": name})

    async def send_direction(self, direction: str) -> None:
        """Send an input message to change movement direction.

        Deduplicates: does nothing if direction matches the last sent value.

        Args:
            direction: One of "up", "down", "left", "right".

        Raises:
            RuntimeError: If not connected.
        """
        if direction == self._last_direction:
            return
        self._last_direction = direction
        await self._send({"type": "input", "direction": direction})

    def reset_direction(self) -> None:
        """Reset the direction dedup state.

        Call this when a new round starts so the first direction
        is always sent.
        """
        self._last_direction = None

    async def messages(self) -> AsyncIterator[ServerMessage]:
        """Yield parsed server messages from the WebSocket.

        Malformed or unrecognized messages are silently skipped to avoid
        tearing down the connection due to a single bad message.

        Yields:
            Parsed ServerMessage dataclass instances.

        Raises:
            RuntimeError: If not connected.
        """
        if self._ws is None:
            raise RuntimeError("Not connected")

        async for raw in self._ws:
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8")

            # Skip keepalive pong responses
            if raw == "pong":
                continue

            try:
                data = json.loads(raw)
                yield parse_message(data)
            except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                # Skip malformed or unrecognized messages
                continue

    async def _send(self, payload: dict) -> None:
        """Send a JSON message over the WebSocket.

        Args:
            payload: The message dict to serialize and send.

        Raises:
            RuntimeError: If not connected.
        """
        if self._ws is None:
            raise RuntimeError("Not connected")
        await self._ws.send(json.dumps(payload))
