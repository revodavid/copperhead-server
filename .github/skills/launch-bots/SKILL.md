---
name: launch-bots
description: Launch CopperHead bots with tools\launch_bots.py, including count, bot type, and difficulty.
---

# Launch CopperHead bots

Use this skill when the user wants to launch, spawn, start, or add bots to a CopperHead server.

Examples:
- "launch 10 bots"
- "spawn 6 shybots"
- "launch 8 copperbots at difficulty 3"
- "start 12 ultrabots"
- "add 5 Sleepy Snake bots"

## Goal

Run `copperhead-server\tools\launch_bots.py` in detached mode so the bots keep running after the agent finishes, then report what was launched and whether the bots joined active matches or are waiting in the lobby.

## Script

- **Launcher**: `copperhead-server\tools\launch_bots.py`
- **Default server URL**: `ws://localhost:8765/ws/`
- **Valid bot types**: `copperbot`, `murderbot`, `shybot`, `sleepy_snake`, `ultrabot`
- **Difficulty range**: `1` to `10`

The script supports:

```powershell
python tools\launch_bots.py <count> [--server <ws-url>] [--bot <type>] [--difficulty <1-10>] [--quiet]
```

## Parameters

- **Count**: required positive integer
- **Bot type**: optional; if omitted, the script chooses random bot types
- **Difficulty**: optional; if omitted, the script chooses random difficulty levels

Map friendly names in the user's request to script values:

| User wording | CLI value |
|--------------|-----------|
| CopperBot | `copperbot` |
| MurderBot | `murderbot` |
| ShyBot | `shybot` |
| Sleepy Snake | `sleepy_snake` |
| UltraBot | `ultrabot` |

## Required behavior

- If the user does not clearly specify the number of bots, use the `ask_user` tool to collect:
  - bot count
  - bot type (`random` or one of the valid bot types)
  - difficulty (`random` or `1-10`)
- If the user specifies an invalid bot type or difficulty, explain the valid choices and ask again with `ask_user`.
- Unless the user specifies a different server URL, target `ws://localhost:8765/ws/`.
- Verify the server is reachable before launching bots.
- Always run the launcher from `copperhead-server` in detached mode.
- Prefer `--quiet` unless the user explicitly asks for verbose bot output.
- Do **not** treat a full or already-running tournament as an error. Extra bots may wait in the lobby for the next tournament.
- After launching, check the server status and lobby so the response can say whether the bots are currently playing or queued.

## Launch procedure

1. Determine the target server URL.
   - Use the user's `ws://` or `wss://` URL if they provide one.
   - Otherwise use `ws://localhost:8765/ws/`.

2. Determine launch arguments.
   - Start with:

     ```powershell
     python tools\launch_bots.py <count> --server <server-url>
     ```

   - Add `--bot <type>` only when the user requested a specific bot type.
   - Add `--difficulty <n>` only when the user requested a specific difficulty.
   - Add `--quiet` unless the user asked for verbose output.

3. Verify the server is reachable.
   - Convert the WebSocket URL to an HTTP base URL by replacing:
     - `ws://` -> `http://`
     - `wss://` -> `https://`
     - trailing `/ws/` (or `/ws`) -> `/`
   - Check `<http-base>status`.

4. Launch the bots in detached mode.

   ```powershell
   Set-Location <project_root>\copperhead-server
   python tools\launch_bots.py <count> --server <server-url> [--bot <type>] [--difficulty <n>] [--quiet]
   ```

5. Wait a few seconds, then query:
   - `<http-base>status`
   - `<http-base>lobby`

6. Report:
   - how many bots were launched
   - the bot type mode (specific type or random)
   - the difficulty mode (specific level or random)
   - the target server URL
   - whether bots are already in active matches or waiting in the lobby

## Notes

- `launch_bots.py` stays alive while the launched bot processes run, so detached mode is required.
- When bot type or difficulty is omitted, the launcher intentionally randomizes them.
- Lobby-queued bots are expected behavior and should be reported as success, not failure.
