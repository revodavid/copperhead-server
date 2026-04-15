# CopperHead Server

Version: 4.1.0

A server for a 2-player Snake game. The CopperHead server manages game state and multi-round knockout competitions, communicating with human and robot clients via WebSocket API.

## Quick Start: Play CopperHead in CodeSpaces

1. **Launch the CopperHead server in CodeSpaces**: Click the green **Code** button on this repository page, select the **Codespaces** tab, and click **Create codespace on main**. 

    - When prompted, click **Make Public** so players can connect.

    ![Your application running on port 8765 is available](img/make-port-public.png)

1. **Wait for the server to start**: When it's ready, you will see **🎮 Play Now!** inserted at the top of this README.

1. **Click the link** displayed in README.md This opens the client in Administrator mode with your server already connected.

    ![Play Now link](img/connect-now.png "Play Now")

1. **Add yourself as a player to the lobby**: Edit your name, and then click **Join Lobby**.

1. (optional) **Click Invite Opponent ⧉** and send the URL in the clipboard to a friend. They can follow the link and join the lobby by clicking the **Join Lobby** button.

1. **To play against a bot**, just click **Start Tournament**.

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

* `--game-timeout`: Maximum number of seconds a player may wait before signaling ready for a game, or the maximum time a game may continue without either snake collecting a fruit. If the ready timeout expires, the inactive player is disconnected and forfeits. If the in-game fruit timeout expires, the current game ends as a stalemate and the longer snake wins. Equal lengths produce a draw for that game. If a match reaches three consecutive drawn games, the third draw is converted into a randomly awarded point to break the tie. Default is 30.

* `--grid-size`: Size of the game grid as WIDTHxHEIGHT. 

* `--speed`: The tick rate of the game in seconds per frame. The default is suitable for human players. Lower values increase game speed.

* `--bots`: Number of AI opponents to pre-populate the lobby with at the start of each competition. Default is 0. Bots are instances of CopperBot (`bot-library/copperbot.py`) at random difficulty levels. Human players who are already in the lobby reduce the number of bots spawned. With `auto_start: "always"` and `bots` equal to or greater than the number of required players, the game runs continuously.

* `--log-file`: Path to the log file for recording significant server events (player joins/disconnects, tournament milestones, admin token, URLs). Default is `server-log.txt`. This can also be set in `server-settings.json` as `"log_file"`.

### Server Settings File options

The command line options may alternatively be provided in a server settings file. See `server-settings.json` for defaults that will be used if no command-line options are provided.

If the server settings file is modified while the server is running, the server will automatically load the new settings, cancel all active games and restart the competition.

Additional options in the server settings file include:

#### `auto_start`

All players join via a **lobby** (waiting room) before entering the competition. An **Administrator** manages the tournament using a special admin URL printed to the console at server startup.

The `auto_start` setting in `server-settings.json` controls how players are admitted and competitions start:
- **`"always"`** — Players are automatically assigned to match slots as they join. The competition starts as soon as all slots are filled. Ideal for unattended servers.
- **`"admit_only"`** (default) — Players are automatically assigned to match slots, but an admin must click **Start Tournament** to begin. After each competition, the admin must start again.
- **`"never"`** — The admin manually assigns players to slots (via **Admit**) and starts the competition. The tournament also auto-pauses between rounds, requiring the admin to click **Resume Tournament** to start the next round. Full manual control.

The `"never"` option is especially useful for [hosting Bot Hack Tournaments](How-To-Host-A-Bot-Hack-Tournament.md) where the host needs to manage players and coordinate when play begins.

#### `game-timeout`

`game-timeout` sets two time limits, in seconds, for each game in a match. Before the game starts, it is the ready timeout: if a player does not send the `ready` action before the timeout expires, the server disconnects that player and awards the game to the opponent by forfeit.

During gameplay, `game-timeout` is also the stalemate timeout. If neither snake collects any fruit before the timeout expires, the current game ends immediately. The longer snake wins that game, and if both snakes are the same length, the game is a draw. If a match reaches three consecutive drawn games, the third draw is converted into a randomly awarded point. The default is `30`.

For backward compatibility, the server also accepts the older `kick-time` and `kick_time` setting names.

## Bot Opponents

This repo provides a simple AI opponent (CopperBot - `bot-library/copperbot.py`) that will be launched as necessary to provide AI opponents. CopperBot's logic is basic and can be easily defeated: you are encouraged to develop your own AI opponents with improved strategies. See [How-To-Build-Your-Own-Bot.md](How-To-Build-Your-Own-Bot.md) for details.

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

### Deploy to Azure

CopperHead Server (and optionally the client) can be deployed to [Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/) for a publicly accessible game server.

**Prerequisites:**
- An Azure subscription ([free trial](https://azure.microsoft.com/free/))
- [Azure CLI](https://aka.ms/azure-cli) installed and logged in (`az login`)
- Both `copperhead-server` and `copperhead-client` repos cloned side by side (same parent directory)

**Deployment overview:**

The deploy script creates the following Azure resources:
- **Azure Container Registry** — stores the Docker image
- **Azure Storage Account + File Share** — holds `server-settings.json` and `server-log.txt`
- **Azure Container Apps environment + app** — runs the server container

If the `copperhead-client` directory is found alongside `copperhead-server`, the client files are automatically bundled into the Docker image. The server serves them at the root URL, so players can access both the client and server from a single URL.

**Step 1: Log into Azure**

From the command line, log into Azure with

```
az login --use-device-code
```

TIP: Log into Azure before launching GitHub Copilot CLI (if you are using it). 

BONUS TIP: To log into a specific tenant, add `--tenant <tenant_id>` to the command. This is useful if you have access to multiple Azure tenants.

**Step 2: Configure game server settings**

Copy `server-settings.json` to `server-settings.azure.json` and customize it for your Azure deployment. This file is gitignored so your Azure-specific settings (like `admin_token`) stay private.

**Step 3: Deploy**

If you are using [GitHub Copilot CLI](https://docs.github.com/en/copilot/github-copilot-in-the-cli), you can simply say **"deploy to azure"** and the `deploy-to-azure` skill (in `.github/skills/`) will handle the full deployment process automatically, including bundling the client, copying Azure settings, deploying, and reporting the URLs.

To deploy manually with PowerShell on Windows, run:

```powershell
pwsh -ExecutionPolicy Bypass -File .\tools\deploy-azure.ps1
git checkout server-settings.json   # Restore the original
```

On Linux/macOS or in Codespaces, use `bash tools/deploy-azure.sh` instead.

The script prints the public HTTP URL plus ready-to-share player and admin URLs when finished. If the client was bundled, players can visit the player URL directly in a browser to play.

**Updating server settings (no redeploy needed):**

`server-settings.json` is stored on an Azure File Share, so you can edit it without redeploying:

1. Open the [Azure Portal](https://portal.azure.com)
2. Open the storage account used by your deployment
3. Open **File shares** → `copperhead-config`
4. Click `server-settings.json` and edit it
5. Save — the server auto-reloads within seconds

The server log file (`server-log.txt`) is also on the same file share for easy access.

**Redeploying (after code changes):**

Run the deploy script again. It rebuilds the Docker image, re-bundles the client, uploads the settings, and updates the container app. The URL stays the same.

**Useful commands:**

```bash
# Replace <app-name> and <resource-group> with your deployment values
az containerapp logs show --name <app-name> --resource-group <resource-group> --follow --format text

az group delete --name <resource-group> --yes --no-wait
```

**Continuous deployment:**

A GitHub Actions workflow (`.github/workflows/deploy-azure.yml`) automatically rebuilds and redeploys on every push to `main`. See the workflow file for setup instructions (Azure credentials, service principal).

## API

See [API.md](API.md) for the complete API reference, including WebSocket endpoints, HTTP endpoints, and message formats.

## License

MIT
