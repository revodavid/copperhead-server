"""CopperHead Server - 2-player Snake game server."""

import asyncio
import json
import random
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from typing import Optional

app = FastAPI(title="CopperHead Server")

GRID_WIDTH = 30
GRID_HEIGHT = 20
TICK_RATE = 0.15  # seconds between game updates


class Snake:
    def __init__(self, player_id: int, start_pos: tuple[int, int], direction: str):
        self.player_id = player_id
        self.body = [start_pos]
        self.direction = direction
        self.next_direction = direction
        self.score = 0
        self.alive = True

    def head(self) -> tuple[int, int]:
        return self.body[0]

    def set_direction(self, direction: str):
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
        if direction in opposites and opposites[direction] != self.direction:
            self.next_direction = direction

    def move(self, grow: bool = False):
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
            "score": self.score,
            "alive": self.alive,
        }


class Game:
    def __init__(self):
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
                grow = snake.head() == self.food if self.food else False
                snake.move(grow)
                if grow:
                    snake.score += 10
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
            "grid": {"width": GRID_WIDTH, "height": GRID_HEIGHT},
            "snakes": {pid: s.to_dict() for pid, s in self.snakes.items()},
            "food": self.food,
            "running": self.running,
            "winner": self.winner,
        }


class GameManager:
    def __init__(self):
        self.game = Game()
        self.connections: dict[int, WebSocket] = {}
        self.ready: set[int] = set()
        self.game_task: Optional[asyncio.Task] = None

    async def connect(self, player_id: int, websocket: WebSocket):
        await websocket.accept()
        self.connections[player_id] = websocket
        await self.broadcast_state()

    def disconnect(self, player_id: int):
        self.connections.pop(player_id, None)
        self.ready.discard(player_id)
        if self.game_task:
            self.game_task.cancel()
            self.game_task = None
        self.game.reset()

    async def handle_message(self, player_id: int, data: dict):
        action = data.get("action")
        if action == "move" and self.game.running:
            direction = data.get("direction")
            if direction in ("up", "down", "left", "right"):
                self.game.snakes[player_id].set_direction(direction)
        elif action == "ready":
            self.ready.add(player_id)
            if len(self.ready) == 2 and not self.game.running:
                await self.start_game()

    async def start_game(self):
        self.game.reset()
        self.game.running = True
        await self.broadcast({"type": "start"})
        self.game_task = asyncio.create_task(self.game_loop())

    async def game_loop(self):
        try:
            while self.game.running:
                self.game.update()
                await self.broadcast_state()
                if not self.game.running:
                    await self.broadcast({"type": "gameover", "winner": self.game.winner})
                    self.ready.clear()
                await asyncio.sleep(TICK_RATE)
        except asyncio.CancelledError:
            pass

    async def broadcast_state(self):
        await self.broadcast({"type": "state", "game": self.game.to_dict()})

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
        "ready_players": list(manager.ready),
    }
