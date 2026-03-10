# WebSocket Protocol

All communication happens over a single WebSocket connection using JSON text messages.

## Endpoint

```
ws://<server-host>/ws
```

Connect with a standard WebSocket client. No authentication required for players.

## Keepalive

The server supports automatic ping/pong. Send a text message `"ping"` and the server replies with `"pong"`. Use this to detect connection health if needed.

---

## Client → Server Messages

Your client sends only **2 message types**.

### `join`

Send once after connecting to register as a player.

```json
{
  "type": "join",
  "name": "TeamAwesome"
}
```

| Field | Type | Rules |
|-------|------|-------|
| `type` | `"join"` | Required |
| `name` | `string` | Required. 1–30 characters after trimming whitespace. |

**Errors:**
- Name is empty → `error` message
- Name too long (>30 chars) → `error` message
- Already joined on this connection → `error` message
- Server is full → `error` message, connection closed
- Round in progress → `error` message

### `input`

Send at any time during a round to change your movement direction.

```json
{
  "type": "input",
  "direction": "left"
}
```

| Field | Type | Rules |
|-------|------|-------|
| `type` | `"input"` | Required |
| `direction` | `"up" \| "down" \| "left" \| "right"` | Required. |

**Notes:**
- Ignored if no round is active
- Ignored if your player is dead
- You must send `join` before `input`
- Direction persists — you keep moving in the last direction you set until you change it or hit a wall

---

## Server → Client Messages

The server sends **6 message types**.

### `welcome`

Sent to you after a successful `join`.

```json
{
  "type": "welcome",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "TeamAwesome",
  "players": [
    { "id": "...", "name": "OtherTeam", "status": "lobby", "role": null, "position": null, "direction": null },
    { "id": "550e8400-...", "name": "TeamAwesome", "status": "lobby", "role": null, "position": null, "direction": null }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Your unique player ID (UUID). Save this — you'll need it to find yourself in state updates. |
| `name` | `string` | Your display name (as the server stored it). |
| `players` | `Player[]` | Current player roster including you. |

**Player object (lobby):**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Player ID |
| `name` | `string` | Display name |
| `status` | `"lobby"` | Always `"lobby"` before a round |
| `role` | `null` | Not assigned yet |
| `position` | `null` | Not placed yet |
| `direction` | `null` | No direction yet |

### `lobby`

Broadcast to all players whenever someone joins or leaves the lobby.

```json
{
  "type": "lobby",
  "players": [
    { "id": "...", "name": "TeamA", "status": "lobby", "role": null, "position": null, "direction": null }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `players` | `Player[]` | Full current roster. |

### `round_start`

Sent to each player when a round begins. Each player receives their own role.

```json
{
  "type": "round_start",
  "map": {
    "width": 21,
    "height": 21,
    "cells": [["wall", "dot", "empty", ...], ...]
  },
  "role": "pacman",
  "players": [
    { "id": "...", "name": "TeamA", "role": "pacman", "position": { "x": 9, "y": 17 } },
    { "id": "...", "name": "TeamB", "role": "ghost", "position": { "x": 8, "y": 6 } }
  ],
  "config": {
    "tickRate": 20,
    "powerPelletDuration": 100,
    "ghostRespawnDelay": 60,
    "pacmanCount": 1,
    "maxPlayers": 10,
    "idleShutdownMinutes": 180
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `map` | `Map` | The game map. See [map-format.md](map-format.md). |
| `role` | `"pacman" \| "ghost"` | **Your** assigned role for this round. |
| `players` | `RoundPlayer[]` | All players with their roles and starting positions. |
| `config` | `GameConfig` | Server configuration for this round. |

**RoundPlayer object:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Player ID |
| `name` | `string` | Display name |
| `role` | `"pacman" \| "ghost"` | Assigned role |
| `position` | `{ x, y }` | Starting grid position |

**GameConfig object:**

| Field | Type | Description |
|-------|------|-------------|
| `tickRate` | `number` | Ticks per second (default: 20) |
| `powerPelletDuration` | `number` | Ticks that ghosts stay vulnerable (default: 100) |
| `ghostRespawnDelay` | `number` | Ticks before eaten ghost respawns (default: 60) |
| `pacmanCount` | `number` | Number of pacman players (default: 1) |
| `maxPlayers` | `number` | Max players allowed (default: 10) |
| `idleShutdownMinutes` | `number` | Server idle timeout in minutes |

### `state`

Broadcast every tick during a round. This is the main game update — render your game based on this.

```json
{
  "type": "state",
  "tick": 42,
  "players": [
    {
      "id": "...",
      "name": "TeamA",
      "role": "pacman",
      "position": { "x": 5, "y": 3 },
      "status": "active",
      "score": 12
    },
    {
      "id": "...",
      "name": "TeamB",
      "role": "ghost",
      "position": { "x": 10, "y": 7 },
      "status": "vulnerable",
      "score": 0
    }
  ],
  "dots": [[1, 1], [1, 2], [2, 3]],
  "powerPellets": [[1, 19], [19, 1]],
  "timeElapsed": 2.1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `tick` | `number` | Current tick count (starts at 1). |
| `players` | `StatePlayer[]` | All players with current positions and status. |
| `dots` | `[x, y][]` | Remaining dot positions. |
| `powerPellets` | `[x, y][]` | Remaining power pellet positions. |
| `timeElapsed` | `number` | Seconds since round started (tick / tickRate). |

**StatePlayer object:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | `string` | Player ID |
| `name` | `string` | Display name |
| `role` | `"pacman" \| "ghost"` | Role |
| `position` | `{ x, y }` | Current grid position |
| `status` | `string` | See [Player Statuses](#player-statuses) |
| `score` | `number` | Current score |

### `round_end`

Broadcast when a round finishes.

```json
{
  "type": "round_end",
  "result": "pacman",
  "scores": {
    "550e8400-...": 45,
    "7c9e6679-...": 2
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `result` | `"pacman" \| "ghosts" \| "cancelled"` | Who won. `"cancelled"` if the round was force-stopped. |
| `scores` | `Record<string, number>` | Final scores keyed by player ID. |

After `round_end`, the server returns to lobby. You'll receive a `lobby` message next.

### `error`

Sent when something goes wrong.

```json
{
  "type": "error",
  "message": "Name is required"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `message` | `string` | Human-readable error description. |

Common errors:
- `"Server is stopped"` — connection closed immediately after
- `"Round in progress"` — connection closed immediately after
- `"Name is required"` / `"Name too long"` — fix and resend `join`
- `"Already joined"` — you already sent `join` on this connection
- `"Server is full"` — connection closed after
- `"Must join first"` — send `join` before other messages
- `"Invalid direction"` — direction must be one of: up, down, left, right
- `"Unknown message type"` — check your `type` field

---

## Player Statuses

| Status | Meaning |
|--------|---------|
| `"lobby"` | In the lobby, waiting for round to start |
| `"active"` | Playing normally |
| `"vulnerable"` | Ghost only — can be eaten by pacman (power pellet active) |
| `"dead"` | Pacman only — killed by a ghost. Cannot move. No respawn. |
| `"respawning"` | Ghost only — eaten by pacman, waiting to respawn at ghost house |

---

## Message Flow Summary

```
Client                          Server
  |                               |
  |--- WebSocket connect -------->|
  |                               |
  |--- { type: "join", ... } ---->|
  |<-- { type: "welcome", ... } --|
  |<-- { type: "lobby", ... } ----|  (broadcast to all)
  |                               |
  |   ... waiting in lobby ...    |
  |<-- { type: "lobby", ... } ----|  (on join/leave)
  |                               |
  |   ... admin starts round ...  |
  |<-- { type: "round_start" } ---|
  |                               |
  |--- { type: "input", ... } --->|  (send anytime)
  |<-- { type: "state", ... } ----|  (every tick)
  |<-- { type: "state", ... } ----|
  |--- { type: "input", ... } --->|
  |<-- { type: "state", ... } ----|
  |                               |
  |<-- { type: "round_end" } -----|
  |<-- { type: "lobby", ... } ----|  (back to lobby)
  |                               |
```
