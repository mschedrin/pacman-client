# Multiplayer Pacman — Client Developer Guide

Build a Pacman game client in any language or framework. This guide covers everything you need to connect to the server and play.

## Quick Start

1. Open a WebSocket connection to the server at `ws://<server-host>/ws`
2. Send a `join` message with your team name
3. Receive `welcome`, then wait in the lobby
4. When a round starts, receive the map and your role
5. Send `input` messages to control your character
6. Receive `state` updates every tick and render the game
7. When the round ends, you're back in the lobby

## Documentation

| File | Contents |
|------|----------|
| [protocol.md](protocol.md) | WebSocket protocol — all message types and their JSON schemas |
| [game-rules.md](game-rules.md) | Game mechanics — movement, collisions, scoring, win conditions |
| [map-format.md](map-format.md) | Map data structure and cell types |
| [connection-guide.md](connection-guide.md) | Connection lifecycle, error handling, and example flows |

## Constraints

- **Server-authoritative** — the server computes all game state. Your client only sends a direction; the server decides what happens.
- **No reconnection** — if you disconnect, you must reconnect and rejoin as a new player.
- **JSON over WebSocket** — all messages are UTF-8 JSON strings. No binary protocol.
- **No room selection** — there is a single game room. Everyone connects to the same endpoint.

## What You Need to Build

At minimum, your client must:

1. Connect via WebSocket
2. Send `join` with a name
3. Handle all 6 server message types
4. Send `input` direction changes
5. Render the game state (any way you like — terminal, web, 3D, whatever)

Everything else — visuals, sound, animations, AI — is up to you.
