# CopperHead Server

A server for a 2-player Snake game. CopperHead manages game state and scoring, communicating with player clients via WebSocket API.

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

## Installation

```bash
pip install -r requirements.txt
```

## Running the Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API

### WebSocket Endpoint

Connect to `ws://localhost:8000/ws/{player_id}` where `player_id` is 1 or 2.

### Messages

**Client → Server:**
- `{"action": "move", "direction": "up|down|left|right"}` - Change snake direction
- `{"action": "ready"}` - Signal ready to start

**Server → Client:**
- `{"type": "state", "game": {...}}` - Game state update
- `{"type": "start"}` - Game started
- `{"type": "gameover", "winner": 1|2|null}` - Game ended

## License

MIT
