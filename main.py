"""CopperHead Server - 2-player Snake game server."""

import asyncio
import json
import os
import random
import logging
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("copperhead")

app = FastAPI(title="CopperHead Server")


@app.on_event("startup")
async def startup_event():
    logger.info("🐍 CopperHead Server started")
    logger.info(f"   Grid: {GRID_WIDTH}x{GRID_HEIGHT}, Tick rate: {TICK_RATE}s")
    
    # Detect Codespaces environment
    codespace_name = os.environ.get("CODESPACE_NAME")
    github_domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
    
    if codespace_name:
        ws_url = f"wss://{codespace_name}-8000.{github_domain}/ws/"
        logger.info("")
        logger.info("=" * 60)
        logger.info("📡 CLIENT CONNECTION URL:")
        logger.info(f"   {ws_url}")
        logger.info("")
        logger.info("⚠️  IMPORTANT: Make port 8000 public!")
        logger.info("   1. Open the Ports tab (bottom panel)")
        logger.info("   2. Right-click port 8000 → Port Visibility → Public")
        logger.info("=" * 60)
        logger.info("")
    else:
        logger.info("")
        logger.info("📡 Client connection URL: ws://localhost:8000/ws/")
        logger.info("")

GRID_WIDTH = 30
GRID_HEIGHT = 20
TICK_RATE = 0.15  # seconds between game updates


class Snake:
    def __init__(self, player_id: int, start_pos: tuple[int, int], direction: str):
        self.player_id = player_id
        self.body = [start_pos]
        self.direction = direction
        self.next_direction = direction
        self.input_queue: list[str] = []
        self.alive = True

    def head(self) -> tuple[int, int]:
        return self.body[0]

    def queue_direction(self, direction: str):
        """Queue a direction change. Only queue if it's valid relative to the last queued or current direction."""
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
        # Check against the last queued direction, or next_direction if queue is empty
        last_dir = self.input_queue[-1] if self.input_queue else self.next_direction
        if direction in opposites and opposites[direction] != last_dir and direction != last_dir:
            self.input_queue.append(direction)
            # Limit queue size to prevent flooding
            if len(self.input_queue) > 3:
                self.input_queue.pop(0)

    def process_input(self):
        """Process one input from the queue."""
        if self.input_queue:
            new_dir = self.input_queue.pop(0)
            opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
            if opposites.get(new_dir) != self.direction:
                self.next_direction = new_dir

    def get_next_head(self) -> tuple[int, int]:
        """Get where the head will be after processing input and moving."""
        # Peek at next direction (process input without consuming)
        next_dir = self.next_direction
        if self.input_queue:
            candidate = self.input_queue[0]
            opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
            if opposites.get(candidate) != self.direction:
                next_dir = candidate
        
        hx, hy = self.head()
        moves = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        dx, dy = moves[next_dir]
        return (hx + dx, hy + dy)

    def move(self, grow: bool = False):
        self.process_input()
        self.direction = self.next_direction
        hx, hy = self.head()
        moves = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        dx, dy = moves[self.direction]
        new_head = (hx + dx, hy + dy)
        self.body.insert(0, new_head)
        if not grow:
            self.body.pop()

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "body": self.body,
            "direction": self.direction,
            "alive": self.alive,
        }


class Game:
    def __init__(self, mode: str = "two_player"):
        self.mode = mode
        self.reset()

    def reset(self):
        self.snakes: dict[int, Snake] = {
            1: Snake(1, (5, GRID_HEIGHT // 2), "right"),
            2: Snake(2, (GRID_WIDTH - 6, GRID_HEIGHT // 2), "left"),
        }
        self.food: Optional[tuple[int, int]] = None
        self.running = False
        self.winner: Optional[int] = None
        self.spawn_food()

    def spawn_food(self):
        occupied = set()
        for snake in self.snakes.values():
            occupied.update(snake.body)
        available = [
            (x, y)
            for x in range(GRID_WIDTH)
            for y in range(GRID_HEIGHT)
            if (x, y) not in occupied
        ]
        if available:
            self.food = random.choice(available)

    def update(self):
        if not self.running:
            return

        for snake in self.snakes.values():
            if snake.alive:
                # Calculate where the snake will actually move to (accounting for input queue)
                next_head = snake.get_next_head()
                
                # Check if next position has food - eating makes snake grow
                grow = next_head == self.food if self.food else False
                snake.move(grow)
                if grow:
                    self.spawn_food()

        # Check collisions
        for snake in self.snakes.values():
            if not snake.alive:
                continue
            hx, hy = snake.head()
            # Wall collision
            if hx < 0 or hx >= GRID_WIDTH or hy < 0 or hy >= GRID_HEIGHT:
                snake.alive = False
            # Self collision
            if snake.head() in snake.body[1:]:
                snake.alive = False
            # Other snake collision
            for other in self.snakes.values():
                if other.player_id != snake.player_id:
                    if snake.head() in other.body:
                        snake.alive = False

        # Check game over
        alive_snakes = [s for s in self.snakes.values() if s.alive]
        if len(alive_snakes) <= 1:
            self.running = False
            if len(alive_snakes) == 1:
                self.winner = alive_snakes[0].player_id
            else:
                self.winner = None  # Draw

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "grid": {"width": GRID_WIDTH, "height": GRID_HEIGHT},
            "snakes": {pid: s.to_dict() for pid, s in self.snakes.items()},
            "food": self.food,
            "running": self.running,
            "winner": self.winner,
        }


class AIPlayer:
    """AI-controlled snake with configurable difficulty (1-10)."""
    
    def __init__(self, difficulty: int = 5):
        self.difficulty = max(1, min(10, difficulty))
    
    def get_move(self, game: "Game", player_id: int) -> Optional[str]:
        snake = game.snakes.get(player_id)
        if not snake or not snake.alive:
            return None
        
        head = snake.head()
        food = game.food
        
        # Get all possible moves
        directions = ["up", "down", "left", "right"]
        moves = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
        
        # Filter out reverse direction
        valid_directions = [d for d in directions if d != opposites[snake.direction]]
        
        # Evaluate each direction
        scored_moves = []
        for direction in valid_directions:
            dx, dy = moves[direction]
            new_head = (head[0] + dx, head[1] + dy)
            
            # Check if move is safe
            is_safe = self._is_safe(new_head, game, player_id)
            
            # Calculate distance to food
            food_dist = 0
            if food:
                food_dist = abs(new_head[0] - food[0]) + abs(new_head[1] - food[1])
            
            scored_moves.append({
                "direction": direction,
                "safe": is_safe,
                "food_dist": food_dist,
                "new_head": new_head
            })
        
        # Sort by safety first, then by food distance
        safe_moves = [m for m in scored_moves if m["safe"]]
        unsafe_moves = [m for m in scored_moves if not m["safe"]]
        
        # Higher difficulty = smarter choices
        mistake_chance = (10 - self.difficulty) / 10 * 0.3  # 0% to 27% mistake rate
        
        if safe_moves:
            # Sort safe moves by food distance
            safe_moves.sort(key=lambda m: m["food_dist"])
            
            # At lower difficulties, sometimes pick suboptimal moves
            if random.random() < mistake_chance and len(safe_moves) > 1:
                return random.choice(safe_moves)["direction"]
            
            # Higher difficulty: look ahead for better paths
            if self.difficulty >= 7:
                best_move = self._look_ahead(safe_moves, game, player_id)
                if best_move:
                    return best_move
            
            return safe_moves[0]["direction"]
        elif unsafe_moves:
            # No safe moves, pick the least bad option
            return unsafe_moves[0]["direction"]
        
        return snake.direction
    
    def _is_safe(self, pos: tuple[int, int], game: "Game", player_id: int) -> bool:
        x, y = pos
        
        # Wall collision
        if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
            return False
        
        # Self collision
        snake = game.snakes[player_id]
        if pos in snake.body[:-1]:  # Exclude tail as it will move
            return False
        
        # Other snake collision
        for pid, other in game.snakes.items():
            if pid != player_id and other.alive:
                if pos in other.body:
                    return False
        
        return True
    
    def _look_ahead(self, moves: list, game: "Game", player_id: int) -> Optional[str]:
        """Look ahead to avoid traps."""
        best_move = None
        best_space = -1
        
        for move in moves:
            # Count available spaces from this position
            space = self._count_space(move["new_head"], game, player_id)
            if space > best_space:
                best_space = space
                best_move = move["direction"]
        
        return best_move
    
    def _count_space(self, start: tuple[int, int], game: "Game", player_id: int, max_depth: int = 10) -> int:
        """Flood fill to count available space."""
        visited = set()
        queue = [start]
        count = 0
        
        obstacles = set()
        for pid, snake in game.snakes.items():
            obstacles.update(snake.body[:-1] if pid == player_id else snake.body)
        
        while queue and count < max_depth * 4:
            pos = queue.pop(0)
            if pos in visited:
                continue
            
            x, y = pos
            if x < 0 or x >= GRID_WIDTH or y < 0 or y >= GRID_HEIGHT:
                continue
            if pos in obstacles:
                continue
            
            visited.add(pos)
            count += 1
            
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                queue.append((x + dx, y + dy))
        
        return count


class GameManager:
    def __init__(self):
        self.game = Game()
        self.connections: dict[int, WebSocket] = {}
        self.ready: set[int] = set()
        self.game_task: Optional[asyncio.Task] = None
        self.pending_mode: str = "two_player"
        self.ai_player: Optional[AIPlayer] = None
        self.ai_player_id: Optional[int] = None
        self.wins: dict[int, int] = {1: 0, 2: 0}  # Track games won per player
        self.names: dict[int, str] = {1: "Player 1", 2: "Player 2"}  # Player names

    async def connect(self, player_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections[player_id] = websocket
        logger.info(f"✅ Player {player_id} connected ({len(self.connections)} player(s) online)")
        await self.broadcast_state()

    def disconnect(self, player_id: int):
        self.connections.pop(player_id, None)
        self.ready.discard(player_id)
        if self.game_task:
            self.game_task.cancel()
            self.game_task = None
            logger.info("⏹️  Game stopped (player disconnected)")
        self.game = Game()
        self.pending_mode = "two_player"
        self.ai_player = None
        self.ai_player_id = None
        self.wins = {1: 0, 2: 0}  # Reset wins on disconnect
        self.names = {1: "Player 1", 2: "Player 2"}  # Reset names
        logger.info(f"❌ Player {player_id} disconnected ({len(self.connections)} player(s) online)")

    async def handle_message(self, player_id: int, data: dict):
        action = data.get("action")
        if action == "move" and self.game.running:
            direction = data.get("direction")
            if direction in ("up", "down", "left", "right"):
                if player_id in self.game.snakes:
                    self.game.snakes[player_id].queue_direction(direction)
        elif action == "set_ai_difficulty" and self.ai_player:
            new_difficulty = data.get("ai_difficulty", 5)
            new_difficulty = max(1, min(10, new_difficulty))
            self.ai_player.difficulty = new_difficulty
            logger.info(f"🤖 AI difficulty changed to {new_difficulty}")
        elif action == "ready":
            mode = data.get("mode", "two_player")
            if mode in ("two_player", "vs_ai"):
                self.pending_mode = mode
            
            # Set player name
            name = data.get("name", f"Player {player_id}")
            self.names[player_id] = name
            
            # Handle AI opponent setup
            if mode == "vs_ai":
                ai_difficulty = data.get("ai_difficulty", 5)
                self.ai_player = AIPlayer(difficulty=ai_difficulty)
                self.ai_player_id = 2 if player_id == 1 else 1
                self.names[self.ai_player_id] = "ServerBot"
                logger.info(f"🤖 AI opponent enabled (difficulty: {ai_difficulty}, player: {self.ai_player_id})")
            else:
                self.ai_player = None
                self.ai_player_id = None
            
            self.ready.add(player_id)
            logger.info(f"👍 {name} (Player {player_id}) ready (mode: {self.pending_mode})")
            
            # For vs_ai mode, only need 1 human player
            if self.pending_mode == "vs_ai":
                required_players = 1
            else:
                required_players = 2
            
            if len(self.ready) >= required_players and not self.game.running:
                await self.start_game()

    async def start_game(self):
        # For vs_ai mode, use two_player game setup
        game_mode = "two_player" if self.pending_mode == "vs_ai" else self.pending_mode
        self.game = Game(mode=game_mode)
        self.game.running = True
        
        if self.ai_player:
            logger.info(f"🎮 Game started! Mode: vs_ai (difficulty {self.ai_player.difficulty}), Human: Player {3 - self.ai_player_id}, AI: Player {self.ai_player_id}")
        else:
            logger.info(f"🎮 Game started! Mode: {self.game.mode}, Players: {list(self.game.snakes.keys())}")
        
        await self.broadcast({"type": "start", "mode": self.pending_mode})
        self.game_task = asyncio.create_task(self.game_loop())

    async def game_loop(self):
        try:
            while self.game.running:
                # AI makes its move before update
                if self.ai_player and self.ai_player_id:
                    ai_direction = self.ai_player.get_move(self.game, self.ai_player_id)
                    if ai_direction:
                        self.game.snakes[self.ai_player_id].queue_direction(ai_direction)
                
                self.game.update()
                await self.broadcast_state()
                if not self.game.running:
                    if self.game.winner:
                        self.wins[self.game.winner] += 1
                        winner_label = f"Player {self.game.winner}"
                        if self.ai_player and self.game.winner == self.ai_player_id:
                            winner_label = "AI"
                        logger.info(f"🏆 Game over! {winner_label} wins! Wins: {dict(self.wins)}")
                    else:
                        logger.info(f"🏁 Game over! Draw. Wins: {dict(self.wins)}")
                    await self.broadcast({"type": "gameover", "winner": self.game.winner, "wins": self.wins, "names": self.names})
                    self.ready.clear()
                await asyncio.sleep(TICK_RATE)
        except asyncio.CancelledError:
            pass

    async def broadcast_state(self):
        await self.broadcast({"type": "state", "game": self.game.to_dict(), "wins": self.wins, "names": self.names})

    async def broadcast(self, message: dict):
        disconnected = []
        for pid, ws in self.connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                disconnected.append(pid)
        for pid in disconnected:
            self.disconnect(pid)


manager = GameManager()


@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: int):
    if player_id not in (1, 2):
        await websocket.close(code=4000, reason="Invalid player_id")
        return
    if player_id in manager.connections:
        await websocket.close(code=4001, reason="Player already connected")
        return

    await manager.connect(player_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await manager.handle_message(player_id, data)
    except WebSocketDisconnect:
        manager.disconnect(player_id)


@app.get("/")
async def root():
    return {"name": "CopperHead Server", "status": "running"}


@app.get("/status")
async def status():
    return {
        "players_connected": list(manager.connections.keys()),
        "game_running": manager.game.running,
        "game_mode": manager.game.mode,
        "ready_players": list(manager.ready),
    }
