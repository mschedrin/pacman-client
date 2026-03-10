# Map Format

The map is a 2D grid sent to your client in the `round_start` message.

## Structure

```json
{
  "width": 21,
  "height": 21,
  "cells": [
    ["wall", "wall", "wall", "wall", "..."],
    ["wall", "power_pellet", "dot", "dot", "..."],
    ...
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `width` | `number` | Number of columns |
| `height` | `number` | Number of rows |
| `cells` | `string[][]` | 2D array, indexed as `cells[y][x]` |

## Cell Types

| Cell Type | Meaning | Visual Suggestion |
|-----------|---------|-------------------|
| `"wall"` | Impassable barrier | Solid block |
| `"empty"` | Open space, nothing to collect | Empty floor |
| `"dot"` | Collectible dot (score point) | Small dot |
| `"power_pellet"` | Makes ghosts vulnerable when collected | Large flashing dot |
| `"pacman_spawn"` | Pacman starting position (walkable) | Treat as empty floor |
| `"ghost_spawn"` | Ghost starting position / respawn point (walkable) | Treat as empty floor |

## Indexing

- `cells[y][x]` — row first, then column
- `y = 0` is the top row
- `x = 0` is the left column
- Matches the `position: { x, y }` coordinates in player data

## Default Map

The server ships with a 21x21 map. Here's the layout (for reference only — always use the map data from `round_start`):

```
#####################
#o...........#.....o#
#.###.#####.#.#####.#
#.#...........#.....#
#.#.###.###.#.#.###.#
#...#.....#.#...#...#
#.###.#G#.#.###.###.#
#.....#G#...........#
#.###.# #.###.#####.#
#.#...#G#.#.........#
#.#.###.###.#.#.###.#
#.................#.#
#.###.###.###.###.#.#
#...#.....#...#.....#
#.#.#.###.#.#.#.###.#
#.#...#.....#...#...#
#.###.#.###.###.#.#.#
#.......#P#.........#
#.#####.# #.#####.#.#
#o.................o#
#####################
```

Legend: `#` wall, `.` dot, `o` power pellet, `P` pacman spawn, `G` ghost spawn, ` ` empty

## Rendering Tips

- The map is static for the entire round — cache it after `round_start`.
- Dots and power pellets are consumed during play. Use the `dots` and `powerPellets` arrays from `state` messages to know which ones remain, not the original map.
- Spawn cells are walkable floor — render them like empty cells during gameplay.
- You can render the map however you want: tiles, ASCII art, 3D, etc.
