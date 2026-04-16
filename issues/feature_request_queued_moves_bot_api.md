# Feature Request: Add support for queued moves in the Bot API

## Summary
Extend the bot API to allow bots to send a buffer of queued moves along with the current move. If the server does not receive a new move in time for a subsequent tick, it will execute the next move from the bot's provided queue.

## Proposed API Change
Add an optional `queued_moves` field to the move payload:
```json
{
    "action": "move",
    "direction": "up",
    "queued_moves": ["left", "down", "right"]
}
```

## Server Behavior
- If a new move is received from the bot, execute it and clear the queue.
- If no new move is received within the tick, dequeue and execute the next move from `queued_moves`.
- If the queue is empty and no move is received, fall back to the current default behavior (continue in the last direction).

## Backward Compatibility
- Bots that do not include `queued_moves` in their move payloads are unaffected.
- This is a fully additive, optional extension to the existing API.

## Implementation Steps
1. Update the WebSocket handler to parse and store the optional `queued_moves` field.
2. Modify the game loop to consume queued moves when no new move is received in a tick.
3. Update `API.md` to document the new optional field and server behavior.