# CopperHead Server Changelog

All notable changes to the CopperHead Server are documented in this file.

## [4.0.7] - 2026-04-02

### Added
- New bot implementations: `shybot.py` and `ultrabot.py` in bot-library
- `/agent/chat` proxy endpoint for Foundry agent integration

### Fixed
- Fix container app creation YAML parsing error in deploy script

### Changed
- When `auto_start` is `"never"`, tournament auto-pauses between rounds; admin must click Resume Tournament to start next round (closes #23)
- Default server settings tweaks
- Between-round delay no longer holds the competition lock

## [4.0.6] - 2026-03-23

### Changed
- Version bump to 4.0.6

## [4.0.5] - 2026-03-18

### Changed
- Updated deploy-to-azure skill to use pwsh and fix env var chaining
- Version bump to 4.0.5

## [4.0.4] - 2026-03-18

### Added
- `GET /settings` endpoint to download the current server settings file (admin_token is stripped for security)

### Changed
- Version bump to 4.0.4

## [4.0.2] - 2026-03-16

### Added
- Tournament countdown timer (`tournament_countdown` setting) — configurable countdown before tournament starts (issue #14)
- Server log file (`--log-file` option, default `server-log.txt`) — logs significant events to a file (issue #19)
- Configurable admin token (`--admin-token` option) — set via CLI or `server-settings.json` (issue #20)
- Azure Container Apps deployment with `deploy-azure.ps1` / `deploy-azure.sh` (issue #15)
- Azure File Share mount for live editing of `server-settings.json` and viewing logs
- Client bundling — deploy scripts bundle the client into the server container for single-URL access
- Dockerfile and GitHub Actions CI/CD workflow
- Copilot skills (`deploy-to-azure`, `launch-game`, `update-status-messages`)
- Champion match history in `competition_complete` message and `/competition` endpoint (client issue #19)
- Match scores included in `/history` endpoint for Recent Winners display

### Fixed
- Observe button now opens the correct room via `?room=` query parameter (client issue #17)
- Root URL serves bundled client `index.html` when `client/` directory exists

## [4.0.1] - 2026-03-10

### Added
- Configurable `game-timeout` ready timeout that disconnects players who do not signal ready before a game starts
- Stalemate rule: if no fruit is collected within `game-timeout` seconds, the longer snake wins the game or it ends in a draw if both snakes are the same length
- Sleepy Snake bot in bot-library: a wandering bot with difficulty levels 1-10 that avoids food at low difficulty and drifts toward food at higher difficulty

## [4.0.0] - 2026-03-06

### Changed
- **BREAKING**: Lobby join action renamed from "ready" to "join"

## [3.7.0] - 2026-03-05

### Added
- Tri-state `auto_start` setting: `"always"`, `"admit_only"` (new default), or `"never"`
  - `"always"`: auto-admit players and auto-start when slots fill (unattended mode)
  - `"admit_only"`: auto-admit players, admin clicks Start Competition
  - `"never"`: admin admits players and starts manually
  - Backward compatible: `true` maps to `"always"`, `false` maps to `"never"`
- Lobby system for admin-controlled tournament management
- Admin token authentication for lobby endpoints
- HTTP endpoints for lobby management (kick, add_to_slot, add_bot, start_tournament, etc.)
- WebSocket lobby messages (lobby_update, lobby_joined, lobby_left, lobby_kicked)

## [3.6.1] - 2026-02-13

### Changed
- Moved Copilot tutorial to "Quick Start" section at top of How-To-Build-Your-Own-Bot.md
- Fixed CopperHead Client link in README to use GitHub URL instead of relative path
- Clarified README parameter descriptions (removed hardcoded defaults)
- Added note about running Copilot CLI in Codespaces or locally in Hack Tournament guide
- Emphasized detached mode instruction in Copilot instructions
- Apple fruit lifetime changed from 0 (infinite) to 300 ticks in default server settings

## [3.6.0] - 2026-02-11

### Added
- CopperBot head-on collision avoidance with difficulty-based behavior (Issue #5)
- `--name` argument for copperbot.py and murderbot.py
- Detailed strategy documentation in copperbot.py
- GitHub Copilot CLI in dev container (Issue #6)
- MIT license
- Tutorial: Use GitHub Copilot to build a bot (How-To-Build-Your-Own-Bot.md)
- Copilot instructions for server repository (.github/copilot-instructions.md)

### Changed
- Renamed Building-Your-Own-Bot.md to How-To-Build-Your-Own-Bot.md
- Dev container uses `python:3` image tag for latest stable Python

### Fixed
- Emoji crash on Windows console in copperbot.py and murderbot.py
- Bots now exit cleanly when tournament ends instead of raising SystemExit
- Player count in /competition endpoint now shows connected players while waiting
- Dev container image compatibility fixes

## [3.5.2] - 2026-02-10

### Added
- Tournament integration test (tests/test_tournament.py)
- server-settings.test.json for fast tournament testing

### Changed
- server-settings.test.json and tests/ added to .gitignore

## [3.5.1] - 2026-02-10

### Added
- Participant guide for Bot Hack Tournaments (How-to-Participate-in-a-Hack-Tournament.md)

### Fixed
- Version number in README.md now matches current release
- Competition status WebSocket broadcast now includes bye_player field
- Documentation fixes: typos, broken links, incorrect port numbers, and step numbering

## [3.5.0] - 2026-02-05

### Added
- Championship history endpoint (`/history`) tracks past competition winners
- Bots now automatically spawn when competition resets

### Changed
- Default port changed from 8000 to 8765 to avoid conflicts with local web servers

### Fixed
- Matches no longer continue beyond points_to_win limit (added guards to start_game and _start_next_game)
- Fixed duplicate bot spawning at server startup
- Observer now switches to another match when followed player has a bye

## [3.4.1] - 2026-02-04

### Added
- CHANGELOG.md file documenting version history

### Changed
- Players must signal ready before every game, not just every match
- Ready button text now contextual: "Start Match", "Next Game", "Return to Lobby"

### Fixed
- CopperBot and MurderBot now signal ready between games in a match
- MurderBot name attribute error fixed
- Updated game-rules.md to reflect current default fruit settings

## [3.4.0] - 2026-02-04

### Fixed
- CopperBot tail collision detection now works correctly
- Moved `import random` to top of file for cleaner code

## [3.3.2] - 2026-02-03

### Added
- Bot library with example bots (MurderBot)
- Tournament hosting documentation

### Fixed
- Draw logic now applies tiebreakers to all simultaneous crashes
- Reduced likelihood of draws: longer snake wins, direction tiebreaker

## [3.3.1] - 2026-02-02

### Added
- Auto-restart server when config file changes (hot reload)
- Active fruits list in `/status` endpoint
- Version and points_to_win in `/status` endpoint

## [3.3.0] - 2026-02-01

### Added
- Server URL parameter included in client links
- WebSocket URL displayed at bottom of startup output

### Changed
- Use postAttachCommand for visible terminal output in Codespaces
- Force unbuffered output for Codespaces terminal visibility

## [3.2.1] - 2026-01-31

### Added
- aiohttp dependency for CopperBot HTTP requests

### Changed
- Use code block for server URL in README for easier copying

## [3.2.0] - 2026-01-30

### Added
- Startup script (`start.py`) with prominent connection instructions
- README auto-updates with WebSocket URL when running in Codespaces

## [3.1.0] - 2026-01-29

### Added
- Grapes fruit type: eating grows your snake and shrinks opponent
- Head-to-head collision rule: direction-changing player loses

## [3.0.1] - 2026-01-28

### Added
- Configurable fruit system with propensity, lifetime, and spawn settings
- Multiple fruit types with different effects

## [3.0.0] - 2026-01-27

### Added
- Dynamic grid dimensions (configurable width and height)
- Complete bot documentation for building custom bots

### Changed
- **BREAKING**: Server configuration format updated

## [2.2.0] - 2026-01-26

### Fixed
- Double-speed bug by guarding against duplicate `start_game` calls

## [2.1.0] - 2026-01-25

### Fixed
- Double-start bug that caused games to run at 2x speed
- Snake starting positions now offset to prevent immediate collisions

## [2.0.0] - 2026-01-24

### Added
- Competition/tournament mode with knockout brackets
- Multi-arena support for parallel matches
- CopperBot AI players (difficulty levels 1-10)
- Observer mode for spectating games
- Auto-spawn bot-vs-bot matches when observers join with no active games

### Changed
- **BREAKING**: New WebSocket message format for competition mode
- Replaced ServerBot with spawned CopperBot subprocess
- Improved room management and matchmaking

### Fixed
- Asyncio lock to prevent matchmaking race condition
- CopperBot subprocess path resolution
- Room list updates for lobby observers

## [1.0.0] - 2026-01-20

### Added
- Initial release
- Basic 2-player Snake game server
- WebSocket-based real-time gameplay
- Simple win/loss tracking
