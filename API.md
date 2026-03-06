# CopperHead Server API

## WebSocket Endpoints

- `/ws/join` — Join the lobby. After connecting, send `{"action": "join", "name": "YourName"}` to enter the lobby.
- `/ws/observe` — Observe active games

## HTTP Endpoints (Public)

- `GET /` — Server info
- `GET /status` — Server status including rooms, players, and settings
- `GET /competition` — Current competition state (round, players, results)
- `GET /history` — Championship history (past tournament winners)
- `GET /lobby` — Current lobby state (players, slots, auto_start mode)
- `GET /rooms/active` — List of active game rooms (for observers)

## HTTP Endpoints (Admin)

All admin endpoints require the admin token, passed as `admin_token` query parameter or `X-Admin-Token` header.

- `POST /lobby/kick?uid=X` — Kick a player from the lobby
- `POST /lobby/add_to_slot?uid=X` — Move a lobby player into the next open match slot
- `POST /lobby/remove_from_slot?uid=X` — Remove a player from a match slot
- `POST /lobby/add_bot?difficulty=N` — Add a CopperBot to the lobby (difficulty 1-10, random if omitted)
- `POST /lobby/play?name=Admin` — Admin joins the lobby as a player
- `POST /lobby/play_bot?name=Admin` — Admin joins and a bot is added for a 1v1
- `POST /start_tournament` — Start the tournament with current slot assignments

## Messages

### Client → Server

- `{"action": "join", "name": "PlayerName"}` — Join the lobby
- `{"action": "ready", "name": "PlayerName"}` — Signal ready for a match
- `{"action": "move", "direction": "up|down|left|right"}` — Change snake direction
- `{"action": "leave_lobby"}` — Leave the lobby

### Server → Client (Lobby)

- `{"type": "lobby_joined", "uid": "...", "name": "..."}` — Confirmed lobby join
- `{"type": "lobby_update", "players": [...], "slot_assignments": [...]}` — Lobby state changed
- `{"type": "lobby_left"}` — Confirmed lobby leave
- `{"type": "lobby_kicked"}` — Kicked from lobby by admin

### Server → Client (Game)

- `{"type": "match_assigned", "room_id": 1, "player_id": 1, "opponent": "Name"}` — Assigned to a match (send `ready` to begin)
- `{"type": "waiting", "message": "..."}` — Waiting for opponent or competition to start
- `{"type": "start"}` — Game started
- `{"type": "state", "game": {...}, "wins": {...}, "names": {...}}` — Game state update (every tick)
- `{"type": "gameover", "winner": 1|2|null, "wins": {...}}` — Game ended
- `{"type": "match_complete", "winner": {...}, "final_score": {...}}` — Match ended (first to N points)
- `{"type": "competition_complete", "champion": {...}}` — Tournament ended
- `{"type": "error", "message": "..."}` — Error (e.g. lobby full, invalid action)

## Game State

Each tick, the `state` message includes a `game` object with the complete board state:

```json
{
  "running": true,
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
