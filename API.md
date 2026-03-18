# CopperHead Server API

## Overview: Bot Connection Flow

A bot connects to the server and plays through a tournament in these steps:

1. **Connect** — Open a WebSocket to `/ws/join`
2. **Join lobby** — Send `{"action": "join", "name": "BotName"}`
3. **Wait** — Receive `lobby_joined` confirmation, then `lobby_update` messages as other players arrive
4. **Match assigned** — When the tournament starts, receive `match_assigned` with your `player_id`, `opponent`, and `room_id`
5. **Ready up** — Send `{"action": "ready"}` to signal you're ready to play
6. **Game loop** — Receive `state` messages every tick with the full board state. Send `{"action": "move", "direction": "up|down|left|right"}` to control your snake
7. **Game over** — Receive `gameover` with the result. Send `{"action": "ready"}` to start the next game in the match
8. **Match complete** — Receive `match_complete`. If you won, wait for the next `match_assigned` (next round). If you lost, the connection closes
9. **Tournament complete** — Receive `competition_complete` with the champion. Disconnect

All communication happens over a **single WebSocket connection** — lobby, game, and tournament messages share the same socket.

## WebSocket Endpoints

- `/ws/join` — Join the lobby (primary endpoint for all players and bots)
- `/ws/observe` — Observe active games (spectator mode)

## HTTP Endpoints (Public)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Server info (`{"name": "CopperHead Server", "status": "running"}`) |
| `GET` | `/status` | Server status: rooms, player counts, grid size, speed, points_to_win, competition state, fruits |
| `GET` | `/settings` | Raw server settings file (admin_token stripped). Returns `{}` if no settings file is loaded |
| `GET` | `/competition` | Competition state: round, total_rounds, players, champion, pairings, reset countdown |
| `GET` | `/history` | Championship history (`{"championships": [...]}`) |
| `GET` | `/lobby` | Lobby state: players, slot_assignments, open_slots, auto_start mode |
| `GET` | `/rooms/active` | Active game rooms (`{"rooms": [{"room_id", "names", "wins"}]}`) |

## HTTP Endpoints (Admin)

All admin endpoints require the admin token, passed as `admin_token` query parameter or `X-Admin-Token` header.

| Method | Path | Parameters | Description |
|--------|------|------------|-------------|
| `POST` | `/lobby/kick` | `uid` | Kick a player from the lobby |
| `POST` | `/lobby/add_to_slot` | `uid` | Move a lobby player into the next open match slot |
| `POST` | `/lobby/remove_from_slot` | `uid` | Remove a player from a match slot (back to waiting) |
| `POST` | `/lobby/add_bot` | `difficulty` (optional, 1-10) | Add a CopperBot to the lobby |
| `POST` | `/lobby/play` | `name` (optional) | Admin joins the lobby as a player |
| `POST` | `/lobby/play_bot` | `name` (optional) | Admin joins and a bot is added for a 1v1 (single-arena only) |
| `POST` | `/start_tournament` | — | Start the tournament with current lobby players |

## Messages

### Client → Server

| Action | Fields | Description |
|--------|--------|-------------|
| `join` | `name` | Join the lobby |
| `leave_lobby` | — | Leave the lobby |
| `ready` | `name` (optional) | Signal ready for the next game |
| `move` | `direction` (`up`/`down`/`left`/`right`) | Change snake direction (during gameplay) |

Observer-only actions:

| Action | Fields | Description |
|--------|--------|-------------|
| `switch_room` | `room_id` | Switch to observing a different room |
| `get_rooms` | — | Request list of active rooms |

### Server → Client (Lobby)

| Type | Fields | Description |
|------|--------|-------------|
| `lobby_joined` | `uid`, `name`, `message` | Confirmed lobby join |
| `lobby_update` | `auto_start`, `players`, `slot_assignments`, `max_slots`, `filled_slots`, `open_slots`, `waiting_count` | Lobby state changed |
| `lobby_left` | `message` | Confirmed lobby leave |
| `lobby_kicked` | `message` | Kicked from lobby by admin |
| `lobby_status` | `players`, `required`, `current` | Pre-tournament player count status |

### Server → Client (Game)

| Type | Fields | Description |
|------|--------|-------------|
| `match_assigned` | `room_id`, `player_id`, `opponent`, `points_to_win`, `game` | Assigned to a match — send `ready` to begin |
| `waiting` | `message` | Waiting for opponent or competition to start |
| `start` | `mode`, `room_id`, `wins` (if competition), `points_to_win` (if competition) | Game started |
| `state` | `game`, `wins`, `names`, `room_id` | Game state update (every tick) |
| `gameover` | `winner`, `wins`, `names`, `room_id`, `points_to_win`, `end_reason` | Single game ended |
| `match_complete` | `winner`, `final_score`, `room_id`, `remaining_matches`, `current_round`, `total_rounds` | Match ended (first to N points) |
| `competition_status` | `state`, `round`, `total_rounds`, `bye_player`, `pairings` | Round begins or status update |
| `competition_complete` | `champion`, `reset_in` | Tournament ended |
| `error` | `message` | Error (lobby full, invalid action, ready timeout, etc.) |

### Server → Client (Observer)

| Type | Fields | Description |
|------|--------|-------------|
| `observer_joined` | `room_id`, `game`, `wins`, `names` | Connected to a room as observer |
| `observer_lobby` | `message` | No active games to observe |
| `room_list` | `rooms`, `current_room`, `round`, `total_rounds` | List of active rooms |

## Game State

Each tick, the `state` message includes a `game` object with the complete board state:

```json
{
  "running": true,
  "tick": 42,
  "grid": {"width": 30, "height": 20},
  "snakes": {
    "1": {
      "body": [[10, 5], [9, 5], [8, 5]],
      "direction": "right",
      "alive": true,
      "buff": "default"
    },
    "2": {
      "body": [[20, 15], [21, 15]],
      "direction": "left",
      "alive": true,
      "buff": "default"
    }
  },
  "foods": [
    {"x": 15, "y": 10, "type": "apple", "lifetime": null}
  ]
}
```

- **running**: Is the game currently active?
- **tick**: Current game tick number
- **grid**: Board dimensions. `(0, 0)` is the top-left corner; `y` increases downward.
- **snakes**: Keyed by player ID (`"1"` or `"2"`):
  - **body**: Array of `[x, y]` coordinates (head is the first element)
  - **direction**: Current movement direction
  - **alive**: Is this snake still alive?
  - **buff**: Current active buff (e.g. `"default"`, `"speed"`, `"shield"`)
- **foods**: Array of food items with `x`, `y`, `type`, and `lifetime` (ticks until expiry, or `null`)

## Spawning Bots

Use the `/lobby/add_bot` admin endpoint to spawn CopperBot opponents:

```bash
# Spawn a bot with random difficulty (requires admin token)
curl -X POST "http://localhost:8765/lobby/add_bot?admin_token=YOUR_TOKEN"

# Spawn a bot with specific difficulty
curl -X POST "http://localhost:8765/lobby/add_bot?difficulty=7&admin_token=YOUR_TOKEN"
```
