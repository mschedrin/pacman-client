# Game Rules

## Overview

Multiplayer Pacman on a grid. The server controls everything — your client sends a direction and renders the result.

## Roles

Each round, players are randomly assigned either **pacman** or **ghost**.

- Number of pacmans is configurable (default: 1). Everyone else is a ghost.
- Roles are randomly assigned at round start.
- You find your role in the `round_start` message's `role` field.

## Movement

- The map is a grid. Players occupy one cell at a time.
- Players move **one cell per tick** in their current direction.
- Players start **stationary** — they don't move until you send your first `input`.
- Direction **persists** — once set, your player keeps moving that direction every tick.
- To change direction, send a new `input` message.
- Moving into a **wall** is blocked — you stay in place but keep your direction.
- Movement is processed at the start of each tick, before collision checks.

**Coordinate system:**
- `x` increases to the right (column index)
- `y` increases downward (row index)
- `(0, 0)` is the top-left corner

**Directions:**
| Direction | Effect |
|-----------|--------|
| `"up"` | y - 1 |
| `"down"` | y + 1 |
| `"left"` | x - 1 |
| `"right"` | x + 1 |

## Collisions

Collisions are checked every tick after movement. Order: dots → power pellets → player vs player.

### Pacman + Dot

- Pacman moves onto a dot → dot is consumed, pacman scores **+1 point**.

### Pacman + Power Pellet

- Pacman moves onto a power pellet → pellet consumed, **all active ghosts become vulnerable**.
- Vulnerability lasts for `powerPelletDuration` ticks (default: 100 ticks = 5 seconds at 20 tps).
- Eating another power pellet while ghosts are already vulnerable **resets** the timer.

### Pacman + Ghost (normal)

- Pacman and an active ghost occupy the same cell → **pacman dies**.
- Dead pacmans cannot move and do not respawn. They stay dead for the rest of the round.

### Pacman + Ghost (vulnerable)

- Pacman and a vulnerable ghost occupy the same cell → **ghost is eaten**.
- Pacman scores **+1 point**.
- The ghost enters `"respawning"` status and reappears at a ghost spawn point after `ghostRespawnDelay` ticks (default: 60 ticks = 3 seconds at 20 tps).
- Respawned ghosts return as `"active"` (not vulnerable, even if the vulnerability timer is still running).

## Scoring

| Action | Points |
|--------|--------|
| Eat a dot | +1 |
| Eat a vulnerable ghost | +1 |

Scores reset every round. There is no persistent leaderboard.

## Win Conditions

| Condition | Result |
|-----------|--------|
| All dots eaten | **Pacman wins** (`"pacman"`) |
| All pacmans dead | **Ghosts win** (`"ghosts"`) |
| Admin force-stops the round | **Cancelled** (`"cancelled"`) |

When a round ends, a `round_end` message is broadcast with the result and final scores, then the server returns to the lobby.

## Tick Pipeline

Each tick executes in this order:

1. **Tick counter** increments
2. **Movement** — all active/vulnerable players move one cell in their direction
3. **Dot collisions** — check if any pacman is on a dot
4. **Pellet collisions** — check if any pacman is on a power pellet
5. **Player collisions** — check pacman vs ghost interactions
6. **Timer updates** — decrement vulnerability timer and respawn timers
7. **Round end check** — check if all dots eaten or all pacmans dead
8. **State broadcast** — send `state` message to all clients

## Disconnection

- If a **pacman** disconnects during a round, they are marked as dead. If all pacmans are dead, ghosts win.
- If a **ghost** disconnects during a round, they are removed from the game. Play continues.
- There is **no reconnection** — disconnected players must reconnect and rejoin as new players in the next lobby.
