# CopperHead Server

Version: 3.7.0

A server for a 2-player Snake game.The CopperHead server manages game state and multi-round knockout competitions, communicating with human and robot clients via WebSocket API.

## Quick Start: Play CopperHead

1. **Launch the CopperHead server in CodeSpaces**: Click the green **Code** button on this repository page, select the **Codespaces** tab, and click **Create codespace on main**. The server will start after a few minutes.

    - When prompted, click **Make Public** so players can connect.

    ![Your application running on port 8765 is available](img/make-port-public.png)

2. **Click the link** displayed in README.md (visible in the Explorer panel after startup). This opens the client with your server already connected.

    ![Play Now link](img/connect-now.png "Play Now")

3. **Play** vs a friend or a bot
    - Click **Join** and invite a friend to do the same on this server
    - Or, click **Play Bot** to join and add a bot opponent automatically

    ![Screenshot](img/screenshot-3.2.0.png)

## About CopperHead Server

CopperHead Server is responsible for managing game state, player matchmaking, and competition logic for a multi-round CopperHead tournament among human and/or AI players.

CopperHead Server does not provide any user interface or graphics for playing the game. Human players use [CopperHead Client](https://github.com/revodavid/copperhead-client) to play or observe games. Bots (automated players) connect via the WebSocket API.

This server can launch basic bot opponents, but better strategies are possible. To **build your own bot opponent**, see [How-To-Build-Your-Own-Bot.md](How-To-Build-Your-Own-Bot.md) for instructions.

### Game Rules

CopperHead is a 2-player game played on a rectangular grid. Each player controls a snake that moves around the grid, trying to eat food items to grow longer while avoiding collisions with walls, themselves, and the other player's snake. 

See [Game Rules](game-rules.md) for full details on game mechanics and scoring.

### Winning a Match

A Match of CopperHead consists of multiple games. The player who survives the game wins a point. The first player to reach a predefined number of points wins the match.

## CopperHead Tournaments

The CopperHead server is designed to host a knockout tournament among human and/or AI players to determine the Championship winner. See [Competition Logic](competition-logic.md) for full details on how competitions are structured and run.

Hosting a CopperHead Bot Hack Tournament is a fun way to engage friends or colleagues in coding AI opponents to compete in CopperHead. See [How-To-Host-A-Bot-Hack-Tournament.md](How-To-Host-A-Bot-Hack-Tournament.md) for step-by-step instructions.

## Server Reference

Usage: python main.py [options] [spec-file]

* `spec-file`: Optional path to a JSON configuration file. If no arguments are provided, `server-settings.json` is used if it exists.

If the configuration file is modified while the server is running, the server will automatically load the new settings, cancel all active games and restart the competition.

### Command-Line Options

Instead of using a spec file, you may provide command-line options. These options override any settings in the spec file.

* `--arenas`: Number of matches in round 1 of the competition. The default is 1, which is best for a single player vs one human or AI opponent. The competition will not begin until twice the number of players have joined.

* `--points-to-win`: Number of points required to win a match. Default is 5.

* `--reset-delay`: Once a competition is complete, the server will wait this many seconds before resetting. At reset the competition restarts: active bots are terminated, new bots are spawned according to the `--bots` setting (minus any human players already in the lobby), and the server begins accepting new players. 

* `--grid-size`: Size of the game grid as WIDTHxHEIGHT. 

* `--speed`: The tick rate of the game in seconds per frame. The default is suitable for human players. Lower values increase game speed.

* `--bots`: Number of AI opponents to pre-populate the lobby with at the start of each competition. Default is 0. Bots are instances of CopperBot (`copperbot.py`) at random difficulty levels. Human players who are already in the lobby reduce the number of bots spawned. With `auto_start: "always"` and `bots` equal to or greater than the number of required players, the game runs continuously.

### Lobby and Admin Mode

All players join via a **lobby** (waiting room) before entering the competition. An **administrator** manages the tournament using a special admin URL printed to the console at server startup.

The `auto_start` setting in `server-settings.json` controls how players are admitted and competitions start:
- **`"always"`** — Players are automatically assigned to match slots as they join. The competition starts as soon as all slots are filled. Ideal for unattended servers.
- **`"admit_only"`** (default) — Players are automatically assigned to match slots, but an admin must click **Start Competition** to begin. After each competition, the admin must start again.
- **`"never"`** — The admin manually assigns players to slots (via **Admit**) and starts the competition. Full manual control.

In both modes:
1. Players connect via `/ws/join` and send `{"action": "ready", "name": "YourName"}` to enter the lobby.
2. The admin can move players from the lobby into match slots, kick players, add CopperBots, and start the tournament when ready.
3. When the tournament starts, any empty match slots are auto-filled from the lobby (in join order), then with CopperBots.
4. Players receive `match_assigned` when placed in a room, and must send `{"action": "ready"}` to signal they are ready to play.

Lobby mode is especially useful for [hosting Bot Hack Tournaments](How-To-Host-A-Bot-Hack-Tournament.md) where the host needs to coordinate when play begins.

### Bot Opponents

This repo provides a simple AI opponent (CopperBot - `copperbot.py`) that will be launched as necessary to provide AI opponents. CopperBot's logic is basic and can be easily defeated: you are encouraged to develop your own AI opponents with improved strategies. See [How-To-Build-Your-Own-Bot.md](How-To-Build-Your-Own-Bot.md) for details.

### Observer Mode

Clients may join the server as observers to spectate active games. Observers do not participate in the game and cannot influence the outcome, but they can view the game state in real-time.

## Requirements and Installation

CopperHead Server is tested in GitHub Codespaces (Debian GNU/Linux 13) and on Windows 11 with Python 3.10+. It should run on any platform that supports the required dependencies.

- Python 3.10+
- FastAPI
- uvicorn
- websockets

### Local Installation

```bash
pip install -r requirements.txt
```

### Running the Server Locally

```bash
python main.py
```

For local servers, use: `ws://localhost:8765/ws`

## API

### WebSocket Endpoints

- `/ws/join` - Join the lobby (recommended). After connecting, send `{"action": "ready", "name": "YourName"}` to enter the lobby.
- `/ws/observe` - Observe active games

### HTTP Endpoints (Lobby)

These endpoints are always available. All endpoints except `GET /lobby` require the admin token for authentication.

- `GET /lobby` — Returns the current lobby state (public, no auth required)
- `POST /lobby/kick?uid=X&admin_token=TOKEN` — Kick a player from the lobby
- `POST /lobby/add_to_slot?uid=X&admin_token=TOKEN` — Move a player from the lobby to a match slot
- `POST /lobby/remove_from_slot?uid=X&admin_token=TOKEN` — Remove a player from a match slot
- `POST /lobby/add_bot?admin_token=TOKEN` — Add a CopperBot to the lobby
- `POST /lobby/play?admin_token=TOKEN&name=Admin` — Admin joins the lobby directly as a player
- `POST /lobby/play_bot?admin_token=TOKEN&name=Admin` — Admin joins and a bot is added for an instant 1v1
- `POST /start_tournament?admin_token=TOKEN` — Start the tournament with current slot assignments

### Messages

**Client → Server:**
- `{"action": "ready", "name": "PlayerName"}` - Join the lobby / signal ready for a match
- `{"action": "move", "direction": "up|down|left|right"}` - Change snake direction
- `{"action": "leave_lobby"}` - Leave the lobby

**Server → Client:**
- `{"type": "joined", "room_id": 1, "player_id": 1}` - Joined a room
- `{"type": "match_assigned", "room_id": 1, "player_id": 1, "opponent": "Name"}` - Assigned to a match (send `ready` to begin)
- `{"type": "state", "game": {...}, "wins": {...}, "names": {...}}` - Game state update
- `{"type": "start"}` - Game started
- `{"type": "gameover", "winner": 1|2|null}` - Game ended

**Server → Client (Lobby Mode):**
- `{"type": "lobby_update", ...}` - Broadcast with full lobby state (players, slots, etc.)
- `{"type": "lobby_joined", ...}` - Confirmation that the player has joined the lobby
- `{"type": "lobby_left", ...}` - Confirmation that the player has left the lobby
- `{"type": "lobby_kicked", ...}` - Notification that the player was kicked by an admin

## Spawning Bots

Use the `/lobby/add_bot` admin endpoint to spawn CopperBot opponents:

```bash
# Spawn a bot with random difficulty (requires admin token)
curl -X POST "http://localhost:8765/lobby/add_bot?admin_token=YOUR_TOKEN"

# Spawn a bot with specific difficulty
curl -X POST "http://localhost:8765/lobby/add_bot?difficulty=7&admin_token=YOUR_TOKEN"
```

## License

MIT
