#!/usr/bin/env python3
"""
ShyBot - a harassing CopperHead bot that stays small and pesters opponents.

ShyBot's strategy:
  1. Stay safe: always keep at least 1 tile of buffer from walls.
  2. Stay short: grab food only when length is 3 or less AND food is within
     2 tiles. Actively avoid food when length is 4 or more.
  3. Harass: move toward the opponent's head, but never get within 1 tile
     of it. The goal is to crowd the opponent and force self-collisions.

Difficulty behavior (1-10):
  - 1-3: Sloppy — frequent random mistakes, barely avoids walls, loosely
         tracks the opponent, sometimes eats food when it shouldn't.
  - 4-6: Competent — mostly follows strategy, occasional missteps.
  - 7-10: Precise — strict wall avoidance, disciplined food control,
          accurately shadows the opponent at distance 2.
"""

import argparse
import asyncio
import json
import random

import websockets


class ShyBot:
    """Autonomous player that stays short and harasses the opponent."""

    def __init__(
        self,
        server_url: str,
        name: str = None,
        difficulty: int = 5,
        quiet: bool = False,
        skip_wait: bool = False,
    ):
        self.server_url = server_url
        self.name = name or f"ShyBot L{difficulty}"
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

    def log(self, msg: str):
        if not self.quiet:
            print(msg.encode("ascii", errors="replace").decode("ascii"))

    # ------------------------------------------------------------------
    # Connection & message handling (standard bot boilerplate)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Helper methods for move calculation
    # ------------------------------------------------------------------

    def _get_foods(self) -> list[dict]:
        """Get food positions, supporting both old and new API formats."""
        foods = self.game_state.get("foods", [])
        if not foods and self.game_state.get("food"):
            old_food = self.game_state.get("food")
            foods = [{"x": old_food[0], "y": old_food[1], "type": "apple"}]
        return foods

    def _build_danger_map(self, snakes: dict) -> set[tuple[int, int]]:
        """Build a set of tiles occupied by snake bodies.

        Our own tail is excluded (it moves away next tick), but opponent
        tails are kept as dangerous — if the opponent eats food, the tail
        stays in place and becomes an obstacle.
        """
        dangerous = set()
        for snake_id, snake_data in snakes.items():
            body = snake_data.get("body", [])
            is_me = str(snake_id) == str(self.player_id)
            if is_me:
                # Our tail is safe — it will move away next tick
                for segment in body[:-1]:
                    dangerous.add((segment[0], segment[1]))
            else:
                # Opponent tail stays if they eat, so treat it as dangerous
                for segment in body:
                    dangerous.add((segment[0], segment[1]))
        return dangerous

    def _count_safe_neighbors(self, x: int, y: int, dangerous: set[tuple[int, int]]) -> int:
        """Count how many adjacent tiles are safe (not wall, not snake)."""
        count = 0
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            nx = x + dx
            ny = y + dy
            if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height and (nx, ny) not in dangerous:
                count += 1
        return count

    def _wall_distance(self, x: int, y: int) -> int:
        """Manhattan distance to the nearest wall edge."""
        return min(x, self.grid_width - 1 - x, y, self.grid_height - 1 - y)

    def _get_opponent(self, snakes: dict) -> dict | None:
        """Find the opponent snake, if alive."""
        opponent_id = 3 - self.player_id
        opponent = snakes.get(str(opponent_id)) or snakes.get(opponent_id)
        if opponent and opponent.get("alive", True) and opponent.get("body"):
            return opponent
        return None

    # ------------------------------------------------------------------
    # Core AI: calculate_move
    # ------------------------------------------------------------------

    def calculate_move(self) -> str | None:
        """Pick the best direction to move.

        Scoring priorities:
          1. Safety first — avoid walls, snakes, and dead-end traps.
          2. Wall buffer — penalize tiles within 1 of the wall edge.
          3. Food logic — seek food when short (length <= 4) and close
             (distance <= 2); avoid food when long (length >= 4).
          4. Harassment — move toward the opponent's head but stay at
             least 2 tiles away (Manhattan distance) so we're never
             adjacent.
        """
        if not self.game_state:
            return None

        snakes = self.game_state.get("snakes", {})
        my_snake = snakes.get(str(self.player_id)) or snakes.get(self.player_id)
        if not my_snake or not my_snake.get("body"):
            return None

        head = (my_snake["body"][0][0], my_snake["body"][0][1])
        current_dir = my_snake.get("direction", "right")
        my_length = len(my_snake.get("body", []))
        foods = self._get_foods()
        dangerous = self._build_danger_map(snakes)
        opponent = self._get_opponent(snakes)

        directions = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0),
        }
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}

        # Build list of candidate moves (non-reversing, in-bounds, not blocked)
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
            safe_moves.append({
                "direction": direction,
                "x": new_x,
                "y": new_y,
            })

        # If no safe moves, pick any non-reversing move (we're doomed anyway)
        if not safe_moves:
            for direction in directions:
                if direction != opposites.get(current_dir):
                    return direction
            return current_dir

        # Precision scales with difficulty: 0.1 (level 1) to 1.0 (level 10).
        # At low precision the bot makes more random mistakes and follows
        # its strategy less strictly.
        precision = self.difficulty / 10.0

        best_dir = None
        best_score = float("-inf")

        for move in safe_moves:
            score = 0.0
            mx, my = move["x"], move["y"]

            # --- 1. Escape routes: strongly prefer tiles with more exits ---
            # Always important for survival, but weighted more at higher
            # difficulty so low-level bots sometimes pick dead ends.
            escape_routes = self._count_safe_neighbors(mx, my, dangerous)
            score += escape_routes * (30 + 30 * precision)

            # --- 2. Wall buffer: penalize tiles near the wall ---
            # At low difficulty the bot barely notices walls; at high
            # difficulty it strongly avoids the edge.
            wall_dist = self._wall_distance(mx, my)
            if wall_dist == 0:
                score -= 200 * precision
            elif wall_dist == 1:
                score -= 80 * precision
            else:
                score += wall_dist * (1 + 2 * precision)

            # --- 3. Food logic (depends on our length) ---
            # At low difficulty the bot is less disciplined about staying
            # short — it sometimes ignores nearby food or eats when long.
            for food in foods:
                food_dist_now = abs(head[0] - food["x"]) + abs(head[1] - food["y"])
                food_dist_new = abs(mx - food["x"]) + abs(my - food["y"])
                lands_on_food = (mx == food["x"] and my == food["y"])

                if my_length <= 3:
                    # Short snake: seek nearby food (scaled by precision)
                    if food_dist_now <= 2:
                        if lands_on_food:
                            score += 150 * precision
                        elif food_dist_new < food_dist_now:
                            score += 50 * precision
                else:
                    # Length 4+: avoid food (scaled by precision)
                    if lands_on_food:
                        score -= 200 * precision
                    elif food_dist_new < food_dist_now and food_dist_now <= 3:
                        score -= 40 * precision

            # --- 4. Opponent harassment ---
            # At low difficulty the bot barely tracks the opponent; at high
            # difficulty it precisely shadows at distance 2.
            if opponent:
                opp_head = (opponent["body"][0][0], opponent["body"][0][1])
                dist_now = abs(head[0] - opp_head[0]) + abs(head[1] - opp_head[1])
                dist_new = abs(mx - opp_head[0]) + abs(my - opp_head[1])

                if dist_new <= 1:
                    # Too close! Shy away — always penalized, but more
                    # strongly at high difficulty.
                    score -= 150 + 150 * precision
                elif dist_new == 2:
                    # Perfect stalking distance
                    score += 120 * precision
                elif dist_new < dist_now:
                    # Closing in from a safe distance
                    score += 60 * precision
                elif dist_new > dist_now:
                    # Moving away
                    score -= 20 * precision

                # Avoid the tile directly ahead of the opponent
                opp_dir = opponent.get("direction")
                dir_vec = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
                if opp_dir in dir_vec:
                    odx, ody = dir_vec[opp_dir]
                    opp_next = (opp_head[0] + odx, opp_head[1] + ody)
                    if (mx, my) == opp_next:
                        score -= 250 * precision

            # --- 5. Random noise (high at low difficulty, near zero at 10) ---
            noise = random.uniform(0, 50) * (1.0 - precision)
            score += noise

            if score > best_score:
                best_score = score
                best_dir = move["direction"]

        return best_dir


# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(description="ShyBot Robot Player")
    parser.add_argument("--server", "-s", default="ws://localhost:8765/ws/",
                        help="Server WebSocket URL (default: ws://localhost:8765/ws/)")
    parser.add_argument("--name", "-n", default=None,
                        help="Bot display name (default: ShyBot L<difficulty>)")
    parser.add_argument("--difficulty", "-d", type=int, default=5,
                        help="AI difficulty 1-10 (default: 5)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress output (for spawned bots)")
    parser.add_argument("--skip-wait", action="store_true",
                        help="Skip server reachability check (used when spawned by server)")
    args = parser.parse_args()

    robot = ShyBot(
        args.server,
        name=args.name,
        difficulty=args.difficulty,
        quiet=args.quiet,
        skip_wait=args.skip_wait,
    )

    if not args.quiet:
        print("ShyBot Robot Player")
        print(f"   Server: {args.server}")
        print(f"   Difficulty: {args.difficulty}")
        print()

    await robot.play()


if __name__ == "__main__":
    asyncio.run(main())
