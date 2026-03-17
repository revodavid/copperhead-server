#!/usr/bin/env python3
"""
Sleepy Snake - a wandering CopperHead bot.

Sleepy Snake picks a direction and keeps drifting that way for 5-10 ticks.
It only changes direction early when continuing would hit a wall, another
snake, the tile directly ahead of the opponent snake, or, at difficulty 1, a
food tile.

Difficulty behavior:
- 1: avoid food whenever there is another safe option
- 2-10: become progressively more likely to drift toward the nearest food
"""

import argparse
import asyncio
import json
import random

import websockets


class SleepySnake:
    """Autonomous player that wanders safely around the board."""

    def __init__(
        self,
        server_url: str,
        name: str = None,
        difficulty: int = 5,
        quiet: bool = False,
        skip_wait: bool = False,
    ):
        self.server_url = server_url
        self.name = name or f"Sleepy Snake L{difficulty}"
        self.difficulty = max(1, min(10, difficulty))
        self.quiet = quiet
        self.skip_wait = skip_wait
        self.player_id = None
        self.game_state = None
        self.running = False
        self.wins = 0
        self.games_played = 0
        self.room_id = None
        self.grid_width = 30
        self.grid_height = 20
        self.wander_direction: str | None = None
        self.ticks_until_turn = 0

    def log(self, msg: str):
        if not self.quiet:
            print(msg.encode("ascii", errors="replace").decode("ascii"))

    async def wait_for_open_competition(self):
        """Wait until the server is reachable, then return."""
        import aiohttp

        base_url = self.server_url.rstrip("/")
        if base_url.endswith("/ws"):
            base_url = base_url[:-3]
        http_url = base_url.replace("ws://", "http://").replace("wss://", "https://")

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{http_url}/status") as response:
                        if response.status == 200:
                            self.log("Server reachable - joining lobby...")
                            return True
                        self.log(f"Server not ready (status {response.status}), waiting...")
            except Exception as exc:
                self.log(f"Cannot reach server: {exc}, waiting...")

            await asyncio.sleep(5)

    async def connect(self):
        """Connect to the game server using auto-matchmaking."""
        if not self.skip_wait:
            await self.wait_for_open_competition()

        base_url = self.server_url.rstrip("/")
        if base_url.endswith("/ws"):
            base_url = base_url[:-3]
        url = f"{base_url}/ws/join"

        try:
            self.log(f"Connecting to {url}...")
            self.ws = await websockets.connect(url)
            self.log("Connected! Joining lobby...")
            await self.ws.send(json.dumps({"action": "join", "name": self.name}))
            return True
        except Exception as exc:
            self.log(f"Connection failed: {exc}")
            return False

    async def play(self):
        """Main bot loop."""
        if not await self.connect():
            self.log("Failed to connect to server. Exiting.")
            return

        self.running = True

        try:
            while self.running:
                message = await self.ws.recv()
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.ConnectionClosed:
            self.log("Connection closed.")
        except Exception as exc:
            self.log(f"Error: {exc}")
        finally:
            self.running = False
            try:
                await self.ws.close()
            except Exception:
                pass
            self.log("Bot stopped.")

    async def handle_message(self, data: dict):
        """Handle incoming server messages."""
        msg_type = data.get("type")

        if msg_type == "error":
            self.log(f"Server error: {data.get('message', 'Unknown error')}")
            self.running = False
            return

        if msg_type == "joined":
            self.player_id = data.get("player_id")
            self.room_id = data.get("room_id")
            self.log(f"Joined Room {self.room_id} as Player {self.player_id}")
            await self.ws.send(json.dumps({"action": "ready", "mode": "two_player", "name": self.name}))
            self.log(f"Ready! Playing as '{self.name}' at difficulty {self.difficulty}")

        elif msg_type == "state":
            self.game_state = data.get("game")
            grid = self.game_state.get("grid", {})
            if grid:
                self.grid_width = grid.get("width", self.grid_width)
                self.grid_height = grid.get("height", self.grid_height)
            if self.game_state and self.game_state.get("running"):
                direction = self.calculate_move()
                if direction:
                    await self.ws.send(json.dumps({"action": "move", "direction": direction}))

        elif msg_type == "start":
            self.log("Game started!")

        elif msg_type == "gameover":
            self.games_played += 1
            winner = data.get("winner")
            my_wins = data.get("wins", {}).get(str(self.player_id), 0) or data.get("wins", {}).get(self.player_id, 0)
            opponent_id = 3 - self.player_id
            opponent_wins = data.get("wins", {}).get(str(opponent_id), 0) or data.get("wins", {}).get(opponent_id, 0)
            points_to_win = data.get("points_to_win", 5)

            if winner == self.player_id:
                self.wins += 1
                self.log(f"Won game! (Match: {my_wins}-{opponent_wins}, first to {points_to_win})")
            elif winner:
                self.log(f"Lost game! (Match: {my_wins}-{opponent_wins}, first to {points_to_win})")
            else:
                self.log(f"Draw! (Match: {my_wins}-{opponent_wins}, first to {points_to_win})")

            await self.ws.send(json.dumps({"action": "ready", "name": self.name}))
            self.log("Ready for next game...")

        elif msg_type == "match_complete":
            winner_id = data.get("winner", {}).get("player_id")
            winner_name = data.get("winner", {}).get("name", "Unknown")
            final_score = data.get("final_score", {})
            my_score = final_score.get(str(self.player_id), 0) or final_score.get(self.player_id, 0)
            opponent_id = 3 - self.player_id
            opponent_score = final_score.get(str(opponent_id), 0) or final_score.get(opponent_id, 0)

            if winner_id == self.player_id:
                self.log(f"Match won! Final: {my_score}-{opponent_score}")
                self.log("Waiting for next round assignment...")
            else:
                self.log(f"Match lost to {winner_name}. Final: {my_score}-{opponent_score}")
                self.log("Exiting.")
                self.running = False

        elif msg_type == "match_assigned":
            self.room_id = data.get("room_id")
            self.player_id = data.get("player_id")
            self.game_state = None
            opponent = data.get("opponent", "Opponent")
            self.log(f"Assigned to Arena {self.room_id} as Player {self.player_id} vs {opponent}")
            await self.ws.send(json.dumps({"action": "ready", "name": self.name}))

        elif msg_type in ("lobby_joined", "lobby_update"):
            if msg_type == "lobby_joined":
                self.log(f"Joined lobby as '{data.get('name', self.name)}'")

        elif msg_type in ("lobby_left", "lobby_kicked"):
            self.log("Removed from lobby.")
            self.running = False

        elif msg_type == "competition_complete":
            champion = data.get("champion", {}).get("name", "Unknown")
            self.log(f"Competition complete! Champion: {champion}")
            self.log("Exiting.")
            self.running = False

        elif msg_type == "waiting":
            self.log("Waiting for opponent...")

    def _get_foods(self) -> list[dict]:
        foods = self.game_state.get("foods", [])
        if not foods and self.game_state.get("food"):
            old_food = self.game_state.get("food")
            foods = [{"x": old_food[0], "y": old_food[1], "type": "apple"}]
        return foods

    def _build_danger_map(self, snakes: dict) -> set[tuple[int, int]]:
        dangerous = set()
        for snake_data in snakes.values():
            body = snake_data.get("body", [])
            # Skip the tail segment — it moves away on the next tick
            for segment in body[:-1]:
                dangerous.add((segment[0], segment[1]))
        return dangerous

    def _build_opponent_head_ahead_danger(self, snakes: dict) -> set[tuple[int, int]]:
        """Treat the tile directly ahead of each opponent as blocked."""
        directions = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
        }

        dangerous = set()
        for snake_id, snake_data in snakes.items():
            if str(snake_id) == str(self.player_id):
                continue
            if not snake_data.get("alive", True):
                continue

            body = snake_data.get("body", [])
            direction = snake_data.get("direction")
            if not body or direction not in directions:
                continue

            dx, dy = directions[direction]
            next_x = body[0][0] + dx
            next_y = body[0][1] + dy
            if 0 <= next_x < self.grid_width and 0 <= next_y < self.grid_height:
                dangerous.add((next_x, next_y))

        return dangerous

    def _count_safe_neighbors(self, x: int, y: int, dangerous: set[tuple[int, int]]) -> int:
        count = 0
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx = x + dx
            ny = y + dy
            if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height and (nx, ny) not in dangerous:
                count += 1
        return count

    def _get_safe_moves(
        self,
        head: tuple[int, int],
        current_dir: str,
        dangerous: set[tuple[int, int]],
    ) -> list[dict]:
        directions = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
        }
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}

        safe_moves = []
        for direction, (dx, dy) in directions.items():
            if direction == opposites.get(current_dir):
                continue

            new_x = head[0] + dx
            new_y = head[1] + dy
            if new_x < 0 or new_x >= self.grid_width or new_y < 0 or new_y >= self.grid_height:
                continue
            if (new_x, new_y) in dangerous:
                continue

            safe_moves.append(
                {
                    "direction": direction,
                    "x": new_x,
                    "y": new_y,
                    "escape_routes": self._count_safe_neighbors(new_x, new_y, dangerous),
                    "edge_distance": min(
                        new_x,
                        self.grid_width - 1 - new_x,
                        new_y,
                        self.grid_height - 1 - new_y,
                    ),
                }
            )

        return safe_moves

    def _find_nearest_food(self, head: tuple[int, int], foods: list[dict]) -> dict | None:
        nearest_food = None
        nearest_distance = float("inf")
        for food in foods:
            distance = abs(head[0] - food["x"]) + abs(head[1] - food["y"])
            if distance < nearest_distance:
                nearest_distance = distance
                nearest_food = food
        return nearest_food

    def _reset_turn_timer(self):
        """Hold the chosen direction for a total of 5-10 ticks, including this one."""
        self.ticks_until_turn = random.randint(5, 10) - 1

    def _score_move(
        self,
        move: dict,
        head: tuple[int, int],
        nearest_food: dict | None,
    ) -> float:
        score = 10.0
        score += move["escape_routes"] * 6.0
        score += move["edge_distance"] * 2.0
        score += random.uniform(0.0, 2.0)

        if nearest_food:
            current_distance = abs(head[0] - nearest_food["x"]) + abs(head[1] - nearest_food["y"])
            new_distance = abs(move["x"] - nearest_food["x"]) + abs(move["y"] - nearest_food["y"])
            distance_change = current_distance - new_distance

            if self.difficulty == 1:
                if distance_change > 0:
                    score -= distance_change * 10.0
                elif distance_change < 0:
                    score += abs(distance_change) * 5.0
                if move["x"] == nearest_food["x"] and move["y"] == nearest_food["y"]:
                    score -= 40.0
            else:
                food_pull = (self.difficulty - 1) / 9.0
                if distance_change > 0:
                    score += distance_change * (1.0 + 10.0 * food_pull)
                elif distance_change < 0:
                    score -= abs(distance_change) * max(0.5, 2.0 - food_pull)
                if move["x"] == nearest_food["x"] and move["y"] == nearest_food["y"]:
                    score += 3.0 + 22.0 * food_pull

        return max(0.1, score)

    def _choose_new_direction(self, safe_moves: list[dict], head: tuple[int, int], foods: list[dict]) -> str:
        nearest_food = self._find_nearest_food(head, foods)
        weights = [self._score_move(move, head, nearest_food) for move in safe_moves]
        chosen_move = random.choices(safe_moves, weights=weights, k=1)[0]
        self.wander_direction = chosen_move["direction"]
        self._reset_turn_timer()
        return self.wander_direction

    def _needs_forced_turn(self, safe_moves: list[dict], foods: list[dict]) -> bool:
        if not self.wander_direction:
            return True

        safe_lookup = {move["direction"]: move for move in safe_moves}
        current_move = safe_lookup.get(self.wander_direction)
        if not current_move:
            return True

        if self.difficulty == 1:
            for food in foods:
                if current_move["x"] == food["x"] and current_move["y"] == food["y"]:
                    return True

        return False

    def calculate_move(self) -> str | None:
        """Keep wandering until the timer expires, unless danger forces a turn."""
        if not self.game_state:
            return None

        snakes = self.game_state.get("snakes", {})
        my_snake = snakes.get(str(self.player_id)) or snakes.get(self.player_id)
        if not my_snake or not my_snake.get("body"):
            return None

        head = (my_snake["body"][0][0], my_snake["body"][0][1])
        current_dir = my_snake.get("direction", "right")
        foods = self._get_foods()
        dangerous = self._build_danger_map(snakes)
        dangerous.update(self._build_opponent_head_ahead_danger(snakes))
        safe_moves = self._get_safe_moves(head, current_dir, dangerous)

        if not safe_moves:
            opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
            for direction in ("up", "down", "left", "right"):
                if direction != opposites.get(current_dir):
                    return direction
            return current_dir

        if self._needs_forced_turn(safe_moves, foods):
            return self._choose_new_direction(safe_moves, head, foods)

        if self.ticks_until_turn <= 0:
            return self._choose_new_direction(safe_moves, head, foods)

        self.ticks_until_turn -= 1
        return self.wander_direction


async def main():
    parser = argparse.ArgumentParser(description="Sleepy Snake Robot Player")
    parser.add_argument("--server", "-s", default="ws://localhost:8765/ws/",
                        help="Server WebSocket URL (default: ws://localhost:8765/ws/)")
    parser.add_argument("--name", "-n", default=None,
                        help="Bot display name (default: Sleepy Snake L<difficulty>)")
    parser.add_argument("--difficulty", "-d", type=int, default=5,
                        help="AI difficulty 1-10 (default: 5)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress output (for spawned bots)")
    parser.add_argument("--skip-wait", action="store_true",
                        help="Skip server reachability check (used when spawned by server)")
    args = parser.parse_args()

    robot = SleepySnake(
        args.server,
        name=args.name,
        difficulty=args.difficulty,
        quiet=args.quiet,
        skip_wait=args.skip_wait,
    )

    if not args.quiet:
        print("Sleepy Snake Robot Player")
        print(f"   Server: {args.server}")
        print(f"   Difficulty: {args.difficulty}")
        print()

    await robot.play()


if __name__ == "__main__":
    asyncio.run(main())
