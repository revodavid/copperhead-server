---
name: launch-game
description: Launch or relaunch the CopperHead server and client locally for testing and development.
---

# Launch CopperHead locally

Use this skill when the user asks to launch, start, run, relaunch, or restart CopperHead locally.

Examples:
- "launch the game"
- "start the game locally"
- "run the game"
- "relaunch the game"
- "start copperhead"
- "launch copperhead locally"

## Goal

Start the CopperHead server and client locally, verify that both are running, and report the correct local URLs to the user.

## Architecture

- **Server**: Python app at `copperhead-server\main.py`, runs on port `8765`
- **Client**: Static HTML, JavaScript, and CSS in `copperhead-client\`, served with `python -m http.server 3000`
- **Config**: `copperhead-server\server-settings.json` is the default config. `copperhead-server\server-settings.local.json` is a gitignored local override for development.

## Required behavior

- Always launch both server and client in detached mode so they keep running after the agent finishes.
- If the user asks to restart or relaunch the game, stop any existing processes already listening on ports `8765` or `3000` before starting new ones.
- If `server-settings.local.json` exists, prefer it over `server-settings.json`.
- After starting each process, verify that the expected port is listening before reporting success.
- If the server is running in lobby mode, read the admin token from the detached log and include the admin URL in the response.

## Launch procedure

1. Check for existing listeners on ports `8765` and `3000`.

   ```powershell
   Get-NetTCPConnection -LocalPort 8765,3000 -State Listen -ErrorAction SilentlyContinue |
     Select-Object LocalPort, OwningProcess
   ```

2. If the user asked to restart or relaunch, stop those specific process IDs with:

   ```powershell
   Stop-Process -Id <PID> -Force
   ```

3. Start the server from `copperhead-server` in detached mode.

   ```powershell
   Set-Location <project_root>\copperhead-server
   if (Test-Path server-settings.local.json) {
       python main.py server-settings.local.json
   } else {
       python main.py
   }
   ```

4. Verify the server is listening on port `8765`.

   ```powershell
   Start-Sleep -Seconds 5
   Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
   ```

5. If needed, read the admin token from the detached log output.

   ```powershell
   Get-ChildItem $env:TEMP\copilot-detached-<shellId>-* -Filter *.log |
     ForEach-Object { Get-Content $_.FullName } |
     Select-String "admin token"
   ```

6. Start the client from `copperhead-client` in detached mode.

   ```powershell
   Set-Location <project_root>\copperhead-client
   python -m http.server 3000
   ```

7. Verify the client is listening on port `3000`.

8. Report the local URLs:

   - Player URL: `http://localhost:3000/?server=ws://localhost:8765/ws/`
   - Admin URL: `http://localhost:3000/?server=ws://localhost:8765/ws/&admin=<TOKEN>` when lobby mode is enabled

## Important notes

- Use detached mode for both server and client.
- The admin token is generated each time the server starts.
- If the user only says "launch the game", use whatever mode the current server settings enable.
- The project root is the parent directory that contains both `copperhead-server\` and `copperhead-client\`.
