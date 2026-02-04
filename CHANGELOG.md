# CopperHead Server Changelog

All notable changes to the CopperHead Server are documented in this file.

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
