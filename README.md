# CopperHead Server

A server for a 2-player Snake game. CopperHead manages game state and scoring, communicating with player clients via WebSocket API.

**Client:** [copperhead-client](https://github.com/revodavid/copperhead-client) | [Play Online](https://revodavid.github.io/copperhead-client/)

## Features

- Real-time 2-player Snake game
- Up to 10 simultaneous game rooms
- Built-in AI opponent (ServerBot)
- Observer mode for spectating games
- WebSocket-based communication

## Requirements

- Python 3.10+
- FastAPI
- uvicorn
- websockets

## Quick Start with GitHub Codespaces

1. Click the **Code** button on the repository page
2. Select the **Codespaces** tab
3. Click **Create codespace on main**

The server will automatically start on port 8000.

### Finding Your Server URL for Clients

1. Open the **Ports** tab in the bottom panel of your Codespace
2. Find port **8000** in the list
3. **Right-click** on port 8000 → **Port Visibility** → **Public** (required for external connections)
4. Copy the forwarded address (it looks like `https://your-codespace-name-8000.app.github.dev`)
5. Use this URL format for the client:
   ```
   wss://your-codespace-name-8000.app.github.dev/ws
   ```

**Example:** If your Codespace URL is:
```
https://bookish-fortnight-p7wqx7rw7h96w7-8000.app.github.dev
```
Then your client Server URL is:
```
wss://bookish-fortnight-p7wqx7rw7h96w7-8000.app.github.dev/ws
```

**Note:** Use `wss://` (not `ws://`) for Codespaces since it uses HTTPS.

## Local Installation

```bash
pip install -r requirements.txt
```

## Running the Server Locally

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

For local servers, use: `ws://localhost:8000/ws`

## API

### WebSocket Endpoints

- `/ws/join` - Auto-matchmaking (recommended)
- `/ws/observe` - Observe active games
- `/ws/{player_id}` - Legacy endpoint (player_id: 1 or 2)

### Messages

**Client → Server:**
- `{"action": "ready", "mode": "vs_ai|two_player", "name": "PlayerName"}` - Ready to play
- `{"action": "move", "direction": "up|down|left|right"}` - Change snake direction
- `{"action": "set_ai_difficulty", "ai_difficulty": 1-10}` - Change AI difficulty

**Server → Client:**
- `{"type": "joined", "room_id": 1, "player_id": 1}` - Joined a room
- `{"type": "state", "game": {...}, "wins": {...}, "names": {...}}` - Game state update
- `{"type": "start", "mode": "..."}` - Game started
- `{"type": "gameover", "winner": 1|2|null}` - Game ended

## Game Modes

- **vs_ai**: Play against ServerBot (adjustable difficulty 1-10)
- **two_player**: Play against another human or CopperBot

## License

MIT
