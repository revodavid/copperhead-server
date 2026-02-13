# Build your own CopperHead bot

We encourage developers to build their own AI-controlled CopperHead bots to play with or to compete against other humans and bots in CopperBot Competitions.

The server can launch the default CopperBot AI opponent, which is implemented in the provided `copperbot.py` file. Modify this file guided by the instructions below to create your own bot with different strategies.

## Quick Start: Use GitHub Copilot to build a new bot

1. Launch a CodeSpace on the [`copperhead-server`](https://github.com/your-username/copperhead-server) repository.
1. When the CodeSpace is ready, click "Make Public" to open the server port
1. Click the "Play Now" link to open the client
1.  Back in Codespaces, Open the terminal, switch to the bash tab, and launch the GitHub Copilot CLI tool:
   ```bash
   copilot
   ```
1. Select "yes" when asked to trust the files in the current folder
1. Enter the prompt:
   ```
   make me a new bot mybot.py based on copperbot.py
   ```
   When prompted select a strategy, or use followup prompts to adjust your bot's strategy
1. Launch your bot in detached mode with the prompt below. (Detached mode prevents the bot from terminating prematurely.)
   ```
   launch mybot.py on server wss://turbo-disco-4qv9xqqv5cj56j-8765.app.github.dev/ws/ in detached mode
   ```   
1. In the client, your bot has joined the tournament. Click "Play" to test it yourself, or "Add bot" and observe.
1. Refine your bot's strategy with additional prompts to Copilot CLI, and relaunch to test it against human or other bot players.

## Understanding CopperHead Bots

CopperHead bots are Python programs that connect to the game server via WebSocket and autonomously play the Snake game. The bot architecture consists of three main components:

1. **Connection Handler**: Manages the WebSocket connection to the server, handles joining competitions, and processes incoming/outgoing messages.

2. **Message Processor**: Receives game state updates from the server and dispatches appropriate responses (ready signals, movement commands).

3. **AI Logic**: The `calculate_move()` function that analyzes the current game state and decides which direction to move.

### Key Functions in `copperbot.py`

| Function | Purpose |
|----------|---------|
| `connect()` | Establishes WebSocket connection to the server |
| `play()` | Main game loop - receives messages and calls handlers |
| `handle_message()` | Processes server messages and triggers appropriate actions |
| `calculate_move()` | **The AI brain** - decides which direction to move |

### Information provided by the server to clients

The server sends JSON messages to connected clients. Each message has a `type` field indicating what kind of message it is:

| Message Type | When Sent | Key Data |
|--------------|-----------|----------|
| `joined` | After connecting | `player_id`, `room_id` - your assigned player number and arena |
| `waiting` | Waiting for opponent | Indicates you're waiting for another player to join |
| `start` | Game begins | `mode`, `room_id` - the game is starting |
| `state` | Every game tick | `game` - complete game state (see below) |
| `gameover` | A game ends | `winner`, `wins`, `points_to_win` - who won and current scores |
| `match_complete` | Match ends | `winner`, `final_score` - who won the match |
| `match_assigned` | Next round starts | `room_id`, `player_id`, `opponent` - your new match assignment |
| `competition_complete` | Tournament ends | `champion` - the overall winner |
| `error` | Something went wrong | `message` - error description |

#### Game State Object

The `state` message includes a `game` object with:

```json
{
  "running": true,
  "grid": {"width": 30, "height": 20},
  "snakes": {
    "1": {
      "body": [[10, 5], [9, 5], [8, 5]],
      "direction": "right",
      "alive": true,
      "buff": "default"
    },
    "2": {
      "body": [[20, 15], [21, 15]],
      "direction": "left",
      "alive": true,
      "buff": "speed"
    }
  },
  "foods": [
    {"x": 15, "y": 10, "type": "apple", "lifetime": null}
  ]
}
```

- **running**: Boolean - is the game currently active?
- **grid**: Object with `width` and `height` of the game board
- **snakes**: Object with player IDs as keys, each containing:
  - **body**: Array of [x, y] coordinates (head is first element)
  - **direction**: Current movement direction ("up", "down", "left", "right")
  - **alive**: Boolean - is this snake still alive?
  - **buff**: Current active buff ("default", "speed", "shield", "inversion", "lucky", "slow", "scissors", "ghost")
- **foods**: Array of food items, each with:
  - **x**, **y**: Coordinates of the food
  - **type**: Fruit type ("apple", "orange", "lemon", "grapes", "strawberry", "banana", "peach", "cherry", "watermelon", "kiwi")
  - **lifetime**: Ticks remaining before fruit expires, or `null`. Only reported when the fruit is about to expire (within the server's `fruit_warning` threshold). A value of `null` means the fruit either never expires or is not yet close to expiring.

### Commands sent by bots to the server

Bots send JSON messages to control their snake:

| Action | Format | Description |
|--------|--------|-------------|
| Ready | `{"action": "ready", "mode": "two_player", "name": "MyBot"}` | Signal you're ready to play |
| Move | `{"action": "move", "direction": "up"}` | Change snake direction |

Valid directions: `"up"`, `"down"`, `"left"`, `"right"`

**Note**: You cannot reverse direction (e.g., go from "left" to "right" directly). The server will ignore invalid moves.

## Getting Started

Follow these steps to create your own bot:

### Step 1: Set up your environment

1. Make sure you have Python 3.10+ installed
2. Install required packages:
   ```bash
   pip install websockets aiohttp
   ```

### Step 2: Copy the bot template

1. Create a new folder for your bot project
2. Copy `copperbot.py` to your new folder
3. Rename it to something unique (e.g., `mysnakebot.py`)

### Step 3: Customize your bot

Open your bot file and find the `calculate_move()` function (around line 207). This is where the AI logic lives.

**Example modification - Make your bot more aggressive about food:**

Find this section in `calculate_move()`:
```python
# Big bonus for capturing food
if food and new_x == food[0] and new_y == food[1]:
    score += 1000  # Always prioritize eating
```

Change it to weight food even more heavily:
```python
# VERY aggressive food pursuit
if food and new_x == food[0] and new_y == food[1]:
    score += 5000  # Food is life!
```

### Step 4: Test your bot

There are two ways to test your bot:

#### Option A: Test against a CopperBot using the server API

This is the easiest way to quickly test your bot. Use the server's `/add_bot` API to spawn an opponent:

```bash
# First, spawn a CopperBot opponent
curl -X POST "http://localhost:8765/add_bot?difficulty=5"

# Then run your bot
python mysnakebot.py --server ws://localhost:8765/ws/ --difficulty 5
```

Or from the client UI, click "Add Bot" to spawn a CopperBot, then run your bot to join as the second player.

#### Option B: Test in a competition

For tournament-style testing with multiple bots:

1. Start a CopperHead server (or connect to an existing one)
2. Run your bot:
   ```bash
   python mysnakebot.py --server ws://localhost:8765/ws/ --difficulty 5
   ```
3. Your bot will wait for another player (human or bot) to join

**Tip**: Run two instances of your bot to watch them compete against each other!

### Step 5: Iterate and improve

Watch your bot play and identify weaknesses. Common improvements:
- Better trap detection (avoiding dead ends)
- Opponent prediction (where will they go?)
- Strategic food blocking

## Bot API Reference

### Command Line Arguments

| Argument | Short | Default | Description |
|----------|-------|---------|-------------|
| `--server` | `-s` | `ws://localhost:8765/ws/` | Server WebSocket URL |
| `--difficulty` | `-d` | `5` | Spawned opponent AI difficulty level (1-10) |
| `--quiet` | `-q` | `false` | Suppress console output |

### RobotPlayer Class

The main class that handles bot behavior.

#### Constructor

```python
RobotPlayer(server_url: str, difficulty: int = 5, quiet: bool = False)
```

- **server_url**: WebSocket URL of the CopperHead server
- **difficulty**: 1-10, affects how often the bot makes suboptimal moves
- **quiet**: If True, suppresses log output

#### Key Methods

**`async connect()`**
Connects to the server and waits for player assignment. Returns `True` on success.

**`async play()`**
Main game loop. Call this to start playing. Runs until disconnected or eliminated.

**`async handle_message(data: dict)`**
Processes incoming server messages. Override this to add custom message handling.

**`calculate_move() -> str | None`**
Returns the next move direction. **This is the main function to customize for your AI strategy.**

### Helper Functions in calculate_move()

The default bot includes these helper functions you can use:

**`is_safe(x, y) -> bool`**
Returns True if the position is not a wall and not occupied by any snake.

**`count_safe_neighbors(x, y) -> int`**
Returns how many adjacent squares are safe (0-4). Useful for avoiding traps.

### Grid Dimensions

The bot automatically receives grid dimensions from the server via the game state. These are stored as instance variables:

```python
self.grid_width   # Game board width (default: 30)
self.grid_height  # Game board height (default: 20)
```

These values are updated automatically when the first game state is received, so your bot will work correctly regardless of server configuration.

### Example: Simple Wall-Avoiding Bot

Here's a minimal `calculate_move()` implementation:

```python
def calculate_move(self) -> str | None:
    if not self.game_state:
        return None
    
    snakes = self.game_state.get("snakes", {})
    my_snake = snakes.get(str(self.player_id))
    if not my_snake or not my_snake.get("body"):
        return None
    
    head = my_snake["body"][0]
    current_dir = my_snake.get("direction", "right")
    
    # Build set of dangerous positions
    dangerous = set()
    for snake_data in snakes.values():
        for segment in snake_data.get("body", []):
            dangerous.add((segment[0], segment[1]))
    
    # Try each direction, pick the first safe one
    directions = ["up", "down", "left", "right"]
    opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
    deltas = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    
    for d in directions:
        if d == opposites[current_dir]:
            continue  # Can't reverse
        dx, dy = deltas[d]
        new_x, new_y = head[0] + dx, head[1] + dy
        
        # Check bounds using instance variables
        if new_x < 0 or new_x >= self.grid_width or new_y < 0 or new_y >= self.grid_height:
            continue
        # Check collision
        if (new_x, new_y) in dangerous:
            continue
        
        return d  # First safe direction
    
    return current_dir  # No safe move, keep going
```

This simple bot just avoids walls and other snakes, without seeking food. Use it as a starting point and add your own strategy!

