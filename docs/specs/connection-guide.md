# Connection Guide

## Connecting

Open a WebSocket to:

```
ws://<server-host>/ws
```

If the server uses HTTPS, use `wss://` instead.

### Connection Rejection

The server may reject your connection immediately with an `error` message followed by a close:

| Error | Meaning | What to do |
|-------|---------|------------|
| `"Server is stopped"` | Server isn't running yet | Wait for the admin to start it, then retry |
| `"Round in progress"` | A game round is active | Wait for the round to end, then retry |

In both cases, the WebSocket will be closed by the server right after the error message.

## Joining

After connecting, send a `join` message:

```json
{ "type": "join", "name": "YourTeamName" }
```

If successful, you'll receive `welcome` followed by a `lobby` broadcast.

**Do not send any other messages before `join`.** You'll get a `"Must join first"` error.

## Lobby Phase

While in the lobby:
- You'll receive `lobby` messages as players join/leave
- Display the player list if you want
- Wait for `round_start`
- You cannot send `input` yet — it will be ignored

## During a Round

Once you receive `round_start`:

1. Parse the map and cache it
2. Note your `role` (pacman or ghost)
3. Start rendering game state
4. Send `input` messages to control your character
5. Process `state` messages every tick to update your display

### Input Timing

- Send `input` whenever the player wants to change direction
- Don't spam — only send when the direction actually changes
- The server processes your latest direction on each tick
- There's no acknowledgment for `input` messages

### State Updates

`state` messages arrive at the configured tick rate (default: 20/sec = every 50ms). Each one contains the complete game state — no deltas.

## Round End

When the round ends, you receive:
1. `round_end` — with the result and final scores
2. `lobby` — you're back in the lobby with updated roster

The same WebSocket connection stays open. You don't need to reconnect.

## Error Handling

Handle `error` messages gracefully. Most errors are non-fatal — they tell you something was wrong with your message but the connection stays open.

Fatal errors that close the connection:
- `"Server is stopped"` (close code 1008)
- `"Round in progress"` (close code 1008)
- `"Server is full"` (close code 1008)
- `"Server stopped"` (close code 1001, server was shut down while you were connected)

## Example: Minimal Client (pseudocode)

```
ws = connect("ws://server/ws")
my_id = null

ws.send(json({ type: "join", name: "MyBot" }))

on ws.message(data):
    msg = parse_json(data)

    if msg.type == "welcome":
        my_id = msg.id
        print("Joined as", my_id)

    if msg.type == "lobby":
        print("Players:", [p.name for p in msg.players])

    if msg.type == "round_start":
        map = msg.map
        my_role = msg.role
        print("Round started! I am", my_role)

    if msg.type == "state":
        me = find(msg.players, id == my_id)
        // Simple AI: move right
        ws.send(json({ type: "input", direction: "right" }))
        render(msg)

    if msg.type == "round_end":
        print("Round over:", msg.result)
        print("My score:", msg.scores[my_id])

    if msg.type == "error":
        print("Error:", msg.message)

on ws.close:
    print("Disconnected")
```

## Tips

- **Save your player ID** from the `welcome` message. You'll need it to find yourself in `state.players` and `round_end.scores`.
- **Cache the map** from `round_start`. It doesn't change during a round.
- **Use `state.dots` and `state.powerPellets`** for remaining collectibles, not the original map cells.
- **Don't assume tick timing** — process each `state` message as it arrives. Network jitter happens.
- **Handle all 6 message types** even if you just log the ones you don't need yet.
- **Test with a simple client first** — connect, join, send a fixed direction, print state. Then build your UI on top.
