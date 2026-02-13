# Copilot Instructions for CopperHead Server

## Build & Run

```bash
pip install -r requirements.txt
python main.py                          # Start server with default settings
python main.py server-settings.json     # Start with specific config file
python start.py                         # Codespaces launcher (shows banner, updates README)
```

IMPORTANT: When launching game servers or bots, **always** launch in detached mode to avoid premature termination.

## Testing

```bash
python tests/test_tournament.py
```

This is an integration test that launches the server with `server-settings.test.json` (fast speed, 12 bots, 6 arenas), runs a full tournament, and checks for anomalies. There is no unit test framework (no pytest/unittest); the test script manages its own server subprocess and uses the HTTP API to poll for completion.

## Architecture

CopperHead is a 2-player Snake game server. The entire server is a single-file FastAPI application (`main.py`, ~2000 lines) with WebSocket-based real-time communication.

### Core classes in `main.py`

- **`ServerConfig`** – Global settings loaded from a JSON config file or CLI args. The server watches the config file and hot-reloads on changes.
- **`Competition`** – Manages a knockout tournament: player registration, round-robin pairings, bye logic for odd player counts, and champion declaration. State machine: `WAITING_FOR_PLAYERS → IN_PROGRESS → COMPLETE → RESETTING`.
- **`GameRoom`** – Runs a single match (best-of-N games) between two players. Each room has its own async game loop driven by `asyncio`.
- **`RoomManager`** – Creates/destroys `GameRoom` instances and routes player/observer WebSocket connections to the correct room.
- **`PlayerInfo`** – Tracks a player's identity, WebSocket, competition stats, and current room assignment.

### Key flow

1. Players connect via `/ws/join` (auto-matchmaking) and are registered with the `Competition`.
2. Once enough players join (`arenas × 2`), the competition starts: players are randomly paired into `GameRoom`s.
3. Each `GameRoom` runs games at a configurable tick rate. Game state (snake positions, food, grid) is broadcast to all connected clients every tick.
4. Match winners advance through rounds until a champion is declared. Losers are eliminated and disconnected.
5. After a `reset_delay`, the server restarts the competition cycle.

### Bot system (`copperbot.py`)

`copperbot.py` implements `RobotPlayer`, a standalone WebSocket client that connects to the server as an AI player. It uses a score-based decision system in `calculate_move()` with configurable difficulty (1-10). The server spawns bot subprocesses via the `/add_bot` HTTP endpoint or the `bots` config setting.

The `bot-library/` directory contains community-contributed bots. All bots must accept `--server`, `--name`, and `--difficulty` CLI arguments.

### Client

The server has no UI. Human players use a separate [CopperHead Client](https://revodavid.github.io/copperhead-client/) that connects via WebSocket. The client is hosted externally and not part of this repo.

## Configuration

Server settings are in JSON files (`server-settings.json`, `server-settings.local.json`, `server-settings.test.json`). Key settings: `arenas`, `points_to_win`, `grid_size` (e.g. `"20x16"`), `speed` (seconds per tick), `bots`, and `fruits` (a dict of fruit types with `propensity` and `lifetime`).

`server-settings.local.json` is gitignored for personal overrides.

## WebSocket API

- `/ws/join` – Auto-matchmaking (recommended)
- `/ws/observe` – Spectator mode
- `/ws/{player_id}` – Legacy direct join

Messages use JSON with `action` (client→server) and `type` (server→client) fields. See `How-To-Build-Your-Own-Bot.md` for the full message protocol reference.

## Conventions

- Python 3.10+ with type hints (e.g. `str | None`, `Optional[...]`).
- Async-first: all server logic uses `asyncio` with `async/await`. WebSocket handling and game loops are coroutines.
- Logging uses Python's `logging` module via `logger = logging.getLogger("copperhead")` — not `print()`.
- The server runs on port 8765 via uvicorn.
- Game coordinates are `[x, y]` arrays where `(0,0)` is top-left; `y` increases downward.
