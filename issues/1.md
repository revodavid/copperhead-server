### Description
Propose extending the API to allow bots to send a buffer of queued moves to the game server along with the current move. If the server does not receive a new move in time for subsequent ticks, it will execute moves from the bot's provided queue. This change should be fully backward-compatible for bots that do not use the feature.

### Proposed Changes
1. Add an optional `queued_moves` field to the move payload.
    ```json
    {
        "action": "move",
        "direction": "up",
        "queued_moves": ["left", "down", "right"]
    }
    ```

2. Server will store and process queued moves if no new move is received.
3. Default behavior remains for bots that do not include the `queued_moves` field.

### Benefits
- Enhances reliability of bot controls under network delays.
- Introduces flexibility for bots to provide pre-planned strategies.
- Fully backward-compatible.

### Steps to Implement
1. Update the WebSocket handler to parse and store `queued_moves`.
2. Modify the game loop to execute queued moves if the current tick times out.
3. Update API documentation to specify new behavior.