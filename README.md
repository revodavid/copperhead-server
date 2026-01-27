# CopperHead Server

Version: 3.2.0

A server for a 2-player Snake game. The CopperHead server manages game state and multi-round knockout competitions, communicating with human and robot clients via WebSocket API. The server also supports adding instances of the default "CopperBot" AI-controlled opponent to the competition, and an observer mode for spectating games.

NOTE: This repo only provides the server for hosting and managing the game. 

* To **play the game** against friends or bots, launch the [CopperHead client](https://revodavid.github.io/copperhead-client/). 
  - You can also launch the [copperhead-client](https://github.com/revodavid/copperhead-client) from this repository on your own Web server or via GitHub CodeSpaces.

The server provides basic bot opponents, but better strategies are possible. To **build your own bot opponent**, see [Building-Your-Own-Bot.md](Building-Your-Own-Bot.md) for instructions.

## Game Rules

CopperHead is a 2-player game played on a rectangular grid. Each player controls a snake that moves around the grid, trying to eat food items to grow longer while avoiding collisions with walls, themselves, and the other player's snake. 

The player who lasts the longest without colliding wins the game and is awareded a point. If both players collide simultaneously, the game ends in a draw and no points are awarded.

### Buffs and Food Bonuses

Each player may possess up to one buff at a time. Food items may affect your snake's length, award or remove a buff, or have other effects as follows:

* Apple: Increases your snake length by 1.

Food items may appear and disappear from the playfield according to server settings.

### Winning a Match

A Match of CopperHead consists of multiple games. The first player to reach a predefined number of points wins the match.

## CopperHead Championship

The CopperHead server is designed to host a knockout tournament among human and/or AI players to determine the Championship winner.

See [Competition Logic](competition-logic.md) for full details on how competitions are structured and run.

## Server Setup

Usage: python main.py [options] [spec-file]

* `spec-file`: Optional path to a JSON configuration file. If no arguments are provided, `server-settings.json` is used if it exists.

### Command-Line Options

Instead of using a spec file, you may provide command-line options. These options override any settings in the spec file.

* `--arenas`: Number of matches in round 1 of the competition. The default is 1, which is best for a single player vs one human or AI opponent. The competition will not begin until twice the number of players have joined.

* `--points-to-win`: Number of points required to win a match. Default is 5.

* `--reset-delay`: Once a competition is complete, the server will wait this many seconds before resetting. At reset the competition restarts: active bots are terminated, new bots are launched according to the `--bots` setting, and the server begins accepting new players. Default is 30 seconds.

* `--grid-size`: Size of the game grid as WIDTHxHEIGHT. Default is 30x20.

* `--speed`: The tick rate of the game in seconds per frame. The default (0.15 seconds) is suitable for human players. Lower values increase game speed and difficulty.

* `--bots`: Number of AI opponents to launch at server start. Default is 0. Bots are instances of CopperBot (`copperbot.py`) at random difficulty levels.

## Basic Bot Opponent

This repo provides a simple AI opponent (CopperBot - `copperbot.py`) that will be launched as necessary to provide AI opponents. CopperBot's logic is basic and can be easily defeated: you are encouraged to develop your own AI opponents with improved strategies. See `Bulding Your Own Bot.md` for details.

## Observer Mode

Clients may join the server as observers to spectate active games. Observers do not participate in the game and cannot influence the outcome, but they can view the game state in real-time.

## Requirements

- Python 3.10+
- FastAPI
- uvicorn
- websockets

## Quick Start with GitHub Codespaces

1. Click the **Code** button on the repository page
2. Select the **Codespaces** tab
3. Click **Create codespace on main**

The server will automatically start and display connection instructions in the terminal.

### Connecting Your Client

When the server starts, you'll see a banner with instructions like this:

```
============================================================
       🐍 COPPERHEAD SNAKE GAME SERVER 🐍
============================================================

📡 HOW TO PLAY:

   Step 1: Open the game client in your browser:
          https://revodavid.github.io/copperhead-client/

   Step 2: Paste this Server URL into the client:

          wss://your-codespace-name-8000.app.github.dev/ws/

   Step 3: ⚠️  IMPORTANT - Make your port PUBLIC:
          • Click the Ports tab in the bottom panel
          • Right-click on port 8000
          • Select Port Visibility → Public
```

Just follow these steps to connect and play!

## Local Installation

```bash
pip install -r requirements.txt
```

## Running the Server Locally

```bash
python main.py
```

For local servers, use: `ws://localhost:8000/ws`

## API

### WebSocket Endpoints

- `/ws/join` - Auto-matchmaking (recommended)
- `/ws/observe` - Observe active games
- `/ws/{player_id}` - Legacy endpoint (player_id: 1 or 2)

### Messages

**Client → Server:**
- `{"action": "ready", "name": "PlayerName"}` - Ready to play
- `{"action": "move", "direction": "up|down|left|right"}` - Change snake direction

**Server → Client:**
- `{"type": "joined", "room_id": 1, "player_id": 1}` - Joined a room
- `{"type": "state", "game": {...}, "wins": {...}, "names": {...}}` - Game state update
- `{"type": "start"}` - Game started
- `{"type": "gameover", "winner": 1|2|null}` - Game ended

## Spawning Bots

Use the `/add_bot` API endpoint to spawn CopperBot opponents:

```bash
# Spawn a bot with random difficulty (1-10)
curl -X POST "http://localhost:8000/add_bot"

# Spawn a bot with specific difficulty
curl -X POST "http://localhost:8000/add_bot?difficulty=7"
```

## License

MIT
