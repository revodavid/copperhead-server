# CopperHead Server — Tests & Tools

This folder contains unit tests, integration tests, and testing utilities for the CopperHead server.

## Test Scripts

Run any test with `python -m pytest tests/<filename>` from the `copperhead-server` directory.

| File | Description |
|------|-------------|
| `test_snake.py` | Unit tests for core Snake class movement rules (movement, growing, collisions). Designed so beginners can safely modify game logic while ensuring core mechanics still work. |
| `test_sleepy_snake.py` | Unit tests for the `sleepy_snake` bot in `bot-library/`. |
| `test_ready_timeout.py` | Tests for ready-timeout behavior when players are waiting to start a match. |
| `test_game_timeout.py` | Tests for in-game timeout and stalemate detection during active gameplay. |
| `test_tournament.py` | End-to-end integration test that launches a server, runs a full tournament, and verifies a champion is declared correctly. |

## Testing Utilities

| File | Description |
|------|-------------|
| `launch_bots.py` | Launches N bots against a running server. Useful for stress-testing tournaments, filling a lobby, or testing a bot against many competitors. Run `python tests/launch_bots.py --help` for usage. |
