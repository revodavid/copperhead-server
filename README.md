# CopperHead Server

A server for a 2-player Snake game. CopperHead manages game state and scoring, communicating with player clients via WebSocket API.

**Client:** [copperhead-client](https://github.com/revodavid/copperhead-client) | [Play Online](https://revodavid.github.io/copperhead-client/)

## Features

- Real-time 2-player Snake game
- WebSocket-based communication
- Game state management
- Score tracking

## Requirements

- Python 3.10+
- FastAPI
- uvicorn
- websockets

## Quick Start with GitHub Codespaces

1. Click the **Code** button on the repository page
2. Select the **Codespaces** tab
3. Click **Create codespace on main**

The server will automatically start and be available at port 8000. Codespaces will prompt you to open the forwarded port.

## Local Installation

```bash
pip install -r requirements.txt
```

## Running the Server Locally

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API

### WebSocket Endpoint

Connect to `ws://localhost:8000/ws/{player_id}` where `player_id` is 1 or 2.

### Messages

**Client → Server:**
- `{"action": "move", "direction": "up|down|left|right"}` - Change snake direction
- `{"action": "ready", "mode": "one_player|two_player"}` - Signal ready to start (mode optional, defaults to two_player)

**Server → Client:**
- `{"type": "state", "game": {...}}` - Game state update
- `{"type": "start", "mode": "one_player|two_player"}` - Game started
- `{"type": "gameover", "winner": 1|2|null}` - Game ended

## Game Modes

- **one_player**: Traditional Snake - maximize your score by eating food
- **two_player**: Competitive - outlast your opponent

## License

MIT
