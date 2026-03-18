---
name: update-status-messages
description: Review and edit all status messages shown in the CopperHead client Play and Observe screens. Extracts messages to a markdown file for editing, then applies changes back to the code.
---

# Update Status Messages

Use this skill when the user wants to review, edit, or update the status messages displayed in the CopperHead client.

Examples:
- "update status messages"
- "edit the status messages"
- "change the status text"
- "review status messages"
- "I want to update the messages shown to players"
- "let me edit the status messages"

## Goal

Extract all status messages from the client code into a human-readable markdown file, let the user edit that file, then apply their changes back to the code.

## Architecture

- **Client code**: `copperhead-client\game.js` contains all status messages as `setStatus(message, color)` calls.
- **Staging file**: `copperhead-client\status-messages.md` is a temporary editing interface used to present messages for review. It does NOT need to be committed to git.
- **Status colors**: `waiting` (yellow), `playing` (green), `victory` (bright green), `error` (red).

## Phase 1: Extract messages

1. Read `copperhead-client\game.js` and find every `setStatus(...)` call.

2. For each call, extract:
   - The **message text** (the first argument)
   - The **color** (the second argument: `"waiting"`, `"playing"`, `"victory"`, or `"error"`)
   - The **context** — what triggers this message (use the surrounding code's `case` labels, `if` conditions, and comments to write a short plain-English description)

3. Replace JavaScript template expressions with `{{PLACEHOLDER}}` syntax. Use this mapping:

   | JS Expression | Placeholder |
   |---------------|-------------|
   | `${playerName}`, `${data.name}` | `{{PLAYER_NAME}}` |
   | `${opponentName}`, `${loserName}` | `{{OPPONENT_NAME}}` |
   | `${currentRound}`, `${currentRound \|\| 1}` | `{{CURRENT_ROUND}}` |
   | `${totalRounds}` | `{{TOTAL_ROUNDS}}` |
   | `${data.current}` | `{{CURRENT}}` |
   | `${data.required}` | `{{REQUIRED}}` |
   | `${winnerName}`, `${matchWinnerName}`, `${roundWinner}` | `{{WINNER_NAME}}` |
   | `${p1Name}`, `${p1}`, `${obsP1}`, `${startP1}` | `{{PLAYER_1}}` |
   | `${p2Name}`, `${p2}`, `${obsP2}`, `${startP2}` | `{{PLAYER_2}}` |
   | `${byePlayerName}` | `{{BYE_PLAYER}}` |
   | `${nextRound}` | `{{NEXT_ROUND}}` |
   | `${timeLimit}` | `{{TIME_LIMIT}}` |
   | Any other `${...}` expression | Create a descriptive `{{UPPER_SNAKE_CASE}}` name |

   **IMPORTANT**: Record the exact mapping you used for each message (placeholder → original JS expression) so you can reverse it in Phase 3. Keep this mapping in memory; do not write it to the file.

4. Group messages into these sections, in this order:
   - **Connection & Lobby** — connecting, registration, lobby join/leave/kick, player count, waiting to connect
   - **Tournament Flow (Player)** — round announcements, byes, match assignment ready prompt, waiting for game, eliminated
   - **In-Game (Player)** — game in progress for the player
   - **Game Over (Player)** — player wins, losses, draws, stalemates
   - **Match/Round End (Player)** — match complete (won/lost), waiting for next round
   - **Observer Messages** — connecting as observer, waiting, game in progress, bye watching
   - **Game Over (Observer)** — observer sees game end (draws, stalemates, wins)
   - **Match/Round End (Observer)** — observer sees match/round/tournament end
   - **Errors** — connection errors, disconnects, server full, disqualified

5. If the same logical message appears in multiple code locations (e.g., observer "Game in progress" in `observer_joined`, `state`, `start`, and `competition_status` handlers), list it only ONCE in the table.

6. Write the file to `copperhead-client\status-messages.md` using this exact format:

   ```markdown
   # CopperHead Client — Status Messages

   Edit messages below. I'll update the code to match.
   Use `{{PLACEHOLDER}}` for dynamic values. Leave Color as-is unless you want to change it.

   Colors: `waiting` (yellow) | `playing` (green) | `victory` (bright green) | `error` (red)

   ---

   ## Section Name

   | # | Message | Color | Context |
   |---|---------|-------|---------|
   | 1 | Message text with {{PLACEHOLDER}} | waiting | Short description of when shown |
   ```

   - Number messages sequentially starting from 1 across all sections.
   - Each logical message gets exactly one row.
   - If a `setStatus` uses a variable fallback like `data.message || "fallback"`, document the fallback text as the message.

## Phase 2: User edits

7. After writing the file, use the `ask_user` tool to invite the user to edit:

   **Question**: "I've written all status messages to `copperhead-client/status-messages.md`. Open the file and edit any Message text or Color you'd like to change, then let me know when you're done."

   **Choices**: `["I'm done editing", "Skip — no changes needed"]`

8. If the user chooses "Skip", delete `status-messages.md` and report that no changes were made. Stop here.

## Phase 3: Apply changes

9. Read the edited `status-messages.md` file.

10. For each message row in the file, compare it against the current message in `game.js`:
    - If the **message text** changed, update the corresponding `setStatus(...)` call(s) in `game.js`.
    - If the **color** changed, update the second argument of the `setStatus(...)` call(s).
    - Convert `{{PLACEHOLDER}}` syntax back to the original JavaScript template expressions using the mapping recorded in Phase 1.

11. When a single table row maps to multiple code locations (because the same logical message appears in several handlers), update **ALL** of them consistently.

12. **Button label consistency**: If a game-over status message references a button label in quotes (e.g., `Click "Ready" to start next game`), also update the nearby `readyBtn.textContent` assignment to match the quoted label.

13. After making all edits, report a summary of what changed (list changed messages with before/after).

14. Delete `copperhead-client\status-messages.md` after applying changes.

## Important rules

- Do NOT change variable names, function signatures, control flow, or game logic — only update string literals inside `setStatus()` calls.
- Some `setStatus()` calls use a dynamic value with fallback: `setStatus(data.message || "fallback", ...)`. Only update the fallback literal; do not change the `data.message` reference.
- Preserve all surrounding code (sound effects, button visibility, DOM updates, event handlers) exactly as-is.
- If the edited file contains a message that doesn't correspond to any existing `setStatus()` call, warn the user and skip it.
- If a `setStatus()` call in the code has no corresponding row in the edited file, leave it unchanged.
