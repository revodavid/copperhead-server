# CopperHead Server

Version: 4.0.1

A server for a 2-player Snake game.The CopperHead server manages game state and multi-round knockout competitions, communicating with human and robot clients via WebSocket API.

## Quick Start: Play CopperHead in CodeSpaces

1. **Launch the CopperHead server in CodeSpaces**: Click the green **Code** button on this repository page, select the **Codespaces** tab, and click **Create codespace on main**. 

    - When prompted, click **Make Public** so players can connect.

    ![Your application running on port 8765 is available](img/make-port-public.png)

1. **Wait for the server to start**: When it's ready, you will see **🎮 Play Now!** inserted at the top of this README.

1. **Click the link** displayed in README.md This opens the client in Administrator mode with your server already connected.

    ![Play Now link](img/connect-now.png "Play Now")

1. **Add yourself as a player to the lobby**: Edit your name, and then click **Join Game**.

1. (optional) **Click Invite Opponent ⧉** and send the URL in the clipboard to a friend. They can follow the link and join the lobby by clicking the Join Game button.

1. **To play against a bot**, just click **Start Competition**.

## About CopperHead Server

CopperHead Server is responsible for managing game state, player matchmaking, and competition logic for a multi-round CopperHead tournament among human and/or AI players.

CopperHead Server does not provide any user interface or graphics for playing the game. Human players use [CopperHead Client](https://github.com/revodavid/copperhead-client) to play or observe games. Bots (automated players) connect via the WebSocket API.

This server can launch basic bot opponents, but better strategies are possible. To **build your own bot opponent**, see [How-To-Build-Your-Own-Bot.md](How-To-Build-Your-Own-Bot.md) for instructions.

### Game Rules

CopperHead is a 2-player game played on a rectangular grid. Each player controls a snake that moves around the grid, trying to eat food items to grow longer while avoiding collisions with walls, themselves, and the other player's snake. 

See [Game Rules](game-rules.md) for full details on game mechanics and scoring.

## CopperHead Tournaments

The CopperHead server is designed to host a knockout tournament among human and/or AI players to determine the Championship winner. See [Competition Logic](competition-logic.md) for full details on how competitions are structured and run.

Hosting a CopperHead Bot Hack Tournament is a fun way to engage friends or colleagues in coding AI opponents to compete in CopperHead. See [How-To-Host-A-Bot-Hack-Tournament.md](How-To-Host-A-Bot-Hack-Tournament.md) for step-by-step instructions.

## Server Reference

### Usage

```
python main.py [options] [server-settings-file]
```

* `server-settings-file`: Optional path to a JSON configuration file. If no arguments are provided, `server-settings.json` is used if it exists.

If the configuration file is modified while the server is running, the server will automatically load the new settings, cancel all active games and restart the competition.

### Command-Line Options

* `--arenas`: Number of matches in round 1 of the competition. The default is 1, which is best for a single player vs one human or AI opponent. The competition will not begin until twice the number of players have joined.

* `--points-to-win`: Number of points required to win a match. Default is 5.

* `--reset-delay`: Once a competition is complete, the server will wait this many seconds before resetting. At reset the competition restarts: active bots are terminated, new bots are spawned according to the `--bots` setting (minus any human players already in the lobby), and the server begins accepting new players. 

* `--game-timeout`: Maximum number of seconds a player may wait before signaling ready for a game, or the maximum time a game may continue without either snake collecting a fruit. If the ready timeout expires, the inactive player is disconnected and forfeits. If the in-game fruit timeout expires, the current game ends as a stalemate and the longer snake wins. Equal lengths produce a draw. Default is 30.

* `--grid-size`: Size of the game grid as WIDTHxHEIGHT. 

* `--speed`: The tick rate of the game in seconds per frame. The default is suitable for human players. Lower values increase game speed.

* `--bots`: Number of AI opponents to pre-populate the lobby with at the start of each competition. Default is 0. Bots are instances of CopperBot (`copperbot.py`) at random difficulty levels. Human players who are already in the lobby reduce the number of bots spawned. With `auto_start: "always"` and `bots` equal to or greater than the number of required players, the game runs continuously.

### Server Settings File options

The command line options may alternatively provided in a server settings file. See `server-settings.json` for defaults that will be used if no command-line options are provided.

If the server settings file is modfied while the server is running, the server will automatically load the new settings, cancel all active games and restart the competition.

Additional options in the server settings file include:

#### `auto_start`

All players join via a **lobby** (waiting room) before entering the competition. An **Administrator** manages the tournament using a special admin URL printed to the console at server startup.

The `auto_start` setting in `server-settings.json` controls how players are admitted and competitions start:
- **`"always"`** — Players are automatically assigned to match slots as they join. The competition starts as soon as all slots are filled. Ideal for unattended servers.
- **`"admit_only"`** (default) — Players are automatically assigned to match slots, but an admin must click **Start Competition** to begin. After each competition, the admin must start again.
- **`"never"`** — The admin manually assigns players to slots (via **Admit**) and starts the competition. Full manual control.

The `"never"`option is especially useful for [hosting Bot Hack Tournaments](How-To-Host-A-Bot-Hack-Tournament.md) where the host needs to manage players and coordinate when play begins.

#### `game-timeout`

`game-timeout` sets two time limits, in seconds, for each game in a match. Before the game starts, it is the ready timeout: if a player does not send the `ready` action before the timeout expires, the server disconnects that player and awards the game to the opponent by forfeit.

During gameplay, `game-timeout` is also the stalemate timeout. If neither snake collects any fruit before the timeout expires, the current game ends immediately. The longer snake wins that game, and if both snakes are the same length, the game is a draw. The default is `30`.

For backward compatibility, the server also accepts the older `kick-time` and `kick_time` setting names.

## Bot Opponents

This repo provides a simple AI opponent (CopperBot - `copperbot.py`) that will be launched as necessary to provide AI opponents. CopperBot's logic is basic and can be easily defeated: you are encouraged to develop your own AI opponents with improved strategies. See [How-To-Build-Your-Own-Bot.md](How-To-Build-Your-Own-Bot.md) for details.

## Observer Mode

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

See [API.md](API.md) for the complete API reference, including WebSocket endpoints, HTTP endpoints, and message formats.

## License

MIT
