"""Shared test fixtures and helpers for Pacman TUI client tests."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator


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
