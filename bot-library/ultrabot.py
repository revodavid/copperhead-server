#!/usr/bin/env python3
"""
CopperHead Bot Template - Your custom Snake game AI.

This bot connects to a CopperHead server and plays Snake autonomously.
Modify the calculate_move() function to implement your own strategy!

QUICK START
-----------
1. Install dependencies:   pip install -r requirements.txt
2. Run:                     python mybot.py --server ws://localhost:8765/ws/

For Codespaces, use the wss:// URL shown in the terminal, e.g.:
    python mybot.py --server wss://your-codespace-url.app.github.dev/ws/

WHAT TO CHANGE
--------------
The calculate_move() function (around line 200) is where your bot decides
which direction to move. The default strategy is simple: chase the nearest
food while avoiding walls and snakes. You can make it smarter!

Ideas for improvement:
  - Avoid getting trapped in dead ends (flood fill)
  - Predict where the opponent will move
  - Use different strategies based on snake length
  - Block the opponent from reaching food
"""

import asyncio
import json
import argparse
import random
import websockets


# ============================================================================
#  BOT CONFIGURATION - Change these to customize your bot
# ============================================================================

# The CopperHead server to connect to. Set this to your server's URL so you
# don't need to pass --server every time. Use "ws://" for local servers or
# "wss://" for Codespaces/remote servers.
GAME_SERVER = "ws://localhost:8765/ws/"

# Your bot's display name (shown to all players in the tournament)
BOT_NAME = "UltraBot-A"

# How your bot appears in logs
BOT_VERSION = "1.0"


# ============================================================================
#  BOT CLASS - Handles connection and game logic
# ============================================================================

class MyBot:
    """A CopperHead bot that connects to the server and plays Snake."""

    def __init__(self, server_url: str, name: str = None):
        self.server_url = server_url
        self.name = name or BOT_NAME
        self.player_id = None
        self.game_state = None
        self.running = False
        self.room_id = None
        # Grid dimensions (updated automatically from server)
        self.grid_width = 30
        self.grid_height = 20

    def log(self, msg: str):
        """Print a message to the console."""
        print(msg.encode("ascii", errors="replace").decode("ascii"))

    # ========================================================================
    #  CONNECTION - You probably don't need to change anything below here
    #  until you get to calculate_move()
    # ========================================================================

    async def wait_for_open_competition(self):
        """Wait until the server is reachable, then return.
        
        Bots always join the lobby regardless of competition state —
        the lobby is always available and the bot will wait there until
        the next competition starts.
        """
        import aiohttp

        base_url = self.server_url.rstrip("/")
        if base_url.endswith("/ws"):
            base_url = base_url[:-3]
        # Convert ws:// to http:// for the REST API
        http_url = base_url.replace("ws://", "http://").replace("wss://", "https://")

        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{http_url}/status") as resp:
                        if resp.status == 200:
                            self.log("Server reachable - joining lobby...")
                            return True
                        else:
                            self.log(f"Server not ready (status {resp.status}), waiting...")
            except Exception as e:
                self.log(f"Cannot reach server: {e}, retrying...")

            await asyncio.sleep(5)

    async def connect(self):
        """Connect to the game server."""
        await self.wait_for_open_competition()

        base_url = self.server_url.rstrip("/")
        if base_url.endswith("/ws"):
            base_url = base_url[:-3]
        url = f"{base_url}/ws/join"

        try:
            self.log(f"Connecting to {url}...")
            self.ws = await websockets.connect(url)
            self.log("Connected! Joining lobby...")
            # Send join message to enter the lobby
            await self.ws.send(json.dumps({
                "action": "join",
                "name": self.name
            }))
            return True
        except Exception as e:
            self.log(f"Connection failed: {e}")
            return False

    async def play(self):
        """Main game loop. Runs until disconnected or eliminated."""
        if not await self.connect():
            self.log("Failed to connect. Exiting.")
            return

        self.running = True

        try:
            while self.running:
                message = await self.ws.recv()
                data = json.loads(message)
                await self.handle_message(data)
        except websockets.ConnectionClosed:
            self.log("Disconnected from server.")
        except Exception as e:
            self.log(f"Error: {e}")
        finally:
            self.running = False
            try:
                await self.ws.close()
            except Exception:
                pass
            self.log("Bot stopped.")

    async def handle_message(self, data: dict):
        """Process messages from the server and respond appropriately."""
        msg_type = data.get("type")

        if msg_type == "error":
            self.log(f"Server error: {data.get('message', 'Unknown error')}")
            self.running = False

        elif msg_type == "joined":
            # Server assigned us a player ID and room
            self.player_id = data.get("player_id")
            self.room_id = data.get("room_id")
            self.log(f"Joined Arena {self.room_id} as Player {self.player_id}")

            # Tell the server we're ready to play
            await self.ws.send(json.dumps({
                "action": "ready",
                "mode": "two_player",
                "name": self.name
            }))
            self.log(f"Ready! Playing as '{self.name}'")

        elif msg_type == "state":
            # Game state update - this is where we decide our next move
            self.game_state = data.get("game")
            grid = self.game_state.get("grid", {})
            if grid:
                self.grid_width = grid.get("width", self.grid_width)
                self.grid_height = grid.get("height", self.grid_height)

            if self.game_state and self.game_state.get("running"):
                direction = self.calculate_move()
                if direction:
                    await self.ws.send(json.dumps({
                        "action": "move",
                        "direction": direction
                    }))

        elif msg_type == "start":
            self.log("Game started!")

        elif msg_type == "gameover":
            winner = data.get("winner")
            my_wins = data.get("wins", {}).get(str(self.player_id), 0)
            opp_id = 3 - self.player_id
            opp_wins = data.get("wins", {}).get(str(opp_id), 0)
            points_to_win = data.get("points_to_win", 5)

            if winner == self.player_id:
                self.log(f"Won! (Score: {my_wins}-{opp_wins}, first to {points_to_win})")
            elif winner:
                self.log(f"Lost! (Score: {my_wins}-{opp_wins}, first to {points_to_win})")
            else:
                self.log(f"Draw! (Score: {my_wins}-{opp_wins}, first to {points_to_win})")

            # Signal ready for next game in the match
            await self.ws.send(json.dumps({
                "action": "ready",
                "name": self.name
            }))

        elif msg_type == "match_complete":
            winner_id = data.get("winner", {}).get("player_id")
            winner_name = data.get("winner", {}).get("name", "Unknown")
            final_score = data.get("final_score", {})
            my_score = final_score.get(str(self.player_id), 0)
            opp_id = 3 - self.player_id
            opp_score = final_score.get(str(opp_id), 0)

            if winner_id == self.player_id:
                self.log(f"Match won! Final: {my_score}-{opp_score}")
                self.log("Waiting for next round...")
            else:
                self.log(f"Match lost to {winner_name}. Final: {my_score}-{opp_score}")
                self.log("Eliminated. Exiting.")
                self.running = False

        elif msg_type == "match_assigned":
            # Assigned to a new match in the next tournament round
            self.room_id = data.get("room_id")
            self.player_id = data.get("player_id")
            self.game_state = None
            opponent = data.get("opponent", "Opponent")
            self.log(f"Next round! Arena {self.room_id} vs {opponent}")
            # Signal ready to the server
            await self.ws.send(json.dumps({"action": "ready", "name": self.name}))

        elif msg_type in ("lobby_joined", "lobby_update"):
            # In the lobby waiting for the competition to start
            if msg_type == "lobby_joined":
                self.log(f"Joined lobby as '{data.get('name', self.name)}'")

        elif msg_type in ("lobby_left", "lobby_kicked"):
            self.log("Removed from lobby.")
            self.running = False

        elif msg_type == "competition_complete":
            champion = data.get("champion", {}).get("name", "Unknown")
            self.log(f"Tournament complete! Champion: {champion}")
            self.running = False

        elif msg_type == "waiting":
            self.log("Waiting for opponent...")

    # ========================================================================
    #  YOUR AI STRATEGY - Modify calculate_move() to change how your bot plays
    # ========================================================================

    def calculate_move(self) -> str | None:
        """Decide which direction to move.

        Safety-first: never move into a current obstacle (wall or any snake
        body). Strongly avoid tiles that may become obstacles next tick,
        such as tiles adjacent to an opponent's head.

        Priority #2: avoid entering a constrained space. If moving somewhere
        would leave fewer than (2 * my_length) reachable tiles, avoid that
        move when any other move is available.

        Fallback behaviour: if there are no strictly safe moves, check whether
        continuing in the current direction would immediately collide. If
        continuing is safe, return None (no move) so the server keeps the
        current direction. If continuing would collide, pick the least-bad
        available move (prefer tail tiles, avoid opponent-adjacent tiles).
        """
        if not self.game_state:
            return None

        from collections import deque

        # Helper to print priority when verbose mode is enabled
        def report_priority(p):
            if getattr(self, 'quiet', False):
                return
            if getattr(self, 'verbose', False):
                try:
                    print(p, end=' ', flush=True)
                except Exception:
                    pass

        snakes = self.game_state.get("snakes", {})
        my_snake = snakes.get(str(self.player_id))

        if not my_snake or not my_snake.get("body"):
            return None

        head = my_snake["body"][0]
        my_length = len(my_snake.get("body", []))
        current_dir = my_snake.get("direction", "right")

        # Get food items from the game state
        foods = self.game_state.get("foods", [])

        # Find the nearest food item
        nearest_food = None
        nearest_dist = float('inf')
        for food in foods:
            dist = abs(head[0] - food["x"]) + abs(head[1] - food["y"])
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_food = food

        # Direction vectors
        directions = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0)
        }

        # Can't reverse direction (e.g. can't go left if currently going right)
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}

        # Build a set of all currently occupied positions (strictly unsafe)
        dangerous = set()
        tails = set()
        for snake_data in snakes.values():
            body = snake_data.get("body", [])
            for segment in body:
                dangerous.add((segment[0], segment[1]))
            if body:
                tail = body[-1]
                tails.add((tail[0], tail[1]))

        # Compute tiles that may become obstacles next tick (risky but not
        # strictly occupied). This includes tiles adjacent to opponent heads.
        risky_next = set()
        for pid, snake_data in snakes.items():
            try:
                pid_int = int(pid)
            except Exception:
                continue
            if pid_int == self.player_id:
                continue
            body = snake_data.get("body", [])
            if not body:
                continue
            opp_head = body[0]
            for dx, dy in directions.values():
                nx, ny = opp_head[0] + dx, opp_head[1] + dy
                if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                    risky_next.add((nx, ny))

        # Strict safety: treat tiles adjacent to opponent heads as obstacles (Priority 1)
        dangerous_strict = set(dangerous) | set(risky_next)

        def is_safe(x, y):
            """Original safety: inside bounds and not currently occupied by any snake."""
            if x < 0 or x >= self.grid_width or y < 0 or y >= self.grid_height:
                return False
            return (x, y) not in dangerous

        def is_strict_safe(x, y):
            """Strict safety for Priority #1: also avoid tiles adjacent to opponent head."""
            if x < 0 or x >= self.grid_width or y < 0 or y >= self.grid_height:
                return False
            return (x, y) not in dangerous_strict

        def count_escape_routes(x, y):
            """Count how many strict safe moves are available from a position."""
            count = 0
            for dx, dy in directions.values():
                if is_strict_safe(x + dx, y + dy):
                    count += 1
            return count

        # Helper: flood fill reachable tiles from a start position, treating
        # tail tiles as free (they may vacate). Stop early if reach threshold.
        def reachable_count(start_x, start_y, threshold):
            # Treat opponent-adjacent tiles as blocked for reachability checks
            blocked = set(dangerous_strict) - set(tails)
            if (start_x, start_y) in blocked:
                return 0
            q = deque()
            q.append((start_x, start_y))
            visited = { (start_x, start_y) }
            cnt = 0
            while q:
                x, y = q.popleft()
                cnt += 1
                if cnt >= threshold:
                    return cnt
                for dx, dy in directions.values():
                    nx, ny = x + dx, y + dy
                    if nx < 0 or nx >= self.grid_width or ny < 0 or ny >= self.grid_height:
                        continue
                    if (nx, ny) in visited or (nx, ny) in blocked:
                        continue
                    visited.add((nx, ny))
                    q.append((nx, ny))
            return cnt

        # Helper: apply difficulty randomness to a chosen direction
        def maybe_randomize(chosen_dir, alternatives):
            # alternatives: list of direction strings available for random choice
            diff = getattr(self, 'difficulty', 5)
            try:
                diff = int(diff)
            except Exception:
                diff = 5
            diff = max(1, min(10, diff))
            # Level 10: always intended move
            if diff >= 10:
                return chosen_dir
            # Linear probability mapping: level 1 -> 0.02, level 10 -> 0.0
            prob = 0.02 * (10 - diff) / 9.0
            if prob > 0 and alternatives and random.random() < prob:
                return random.choice(alternatives)
            return chosen_dir

        # First: roll for a random move according to difficulty. If roll succeeds,
        # pick a random non-reversing safe move (is_safe). This introduces
        # intentional imperfection at low difficulty levels.
        try:
            diff = int(getattr(self, 'difficulty', 5))
        except Exception:
            diff = 5
        diff = max(1, min(10, diff))
        # level 1 -> 0.02, level 10 -> 0.0, linear in between
        rand_prob = 0.02 * (10 - diff) / 9.0
        if rand_prob > 0 and random.random() < rand_prob:
            # collect non-reversing directions
            choices = []
            for direction, (dx, dy) in directions.items():
                if direction == opposites.get(current_dir):
                    continue
                nx, ny = head[0] + dx, head[1] + dy
                # keep moves that are inside grid
                if 0 <= nx < self.grid_width and 0 <= ny < self.grid_height:
                    choices.append(direction)
            # prefer moves that are at least 'safe' (not currently occupied)
            safe_choices = []
            for direction in choices:
                dx, dy = directions[direction]
                nx, ny = head[0] + dx, head[1] + dy
                if is_safe(nx, ny):
                    safe_choices.append(direction)
            pick_from = safe_choices if safe_choices else choices
            if pick_from:
                choice = random.choice(pick_from)
                report_priority(0)
                return choice

        # Find all strictly safe (non-wall, non-snake, non-reversing) moves
        safe_moves = []
        for direction, (dx, dy) in directions.items():
            if direction == opposites.get(current_dir):
                continue
            new_x = head[0] + dx
            new_y = head[1] + dy
            if is_strict_safe(new_x, new_y):
                safe_moves.append({"direction": direction, "x": new_x, "y": new_y})

        # If no strictly safe moves exist, decide between staying (if safe)
        # or picking the least-bad available move.
        if not safe_moves:
            # Position if we continue in the current direction
            cur_dx, cur_dy = directions.get(current_dir, (1, 0))
            cont_x, cont_y = head[0] + cur_dx, head[1] + cur_dy
            # If continuing is strictly safe, prefer doing nothing (return None)
            if is_safe(cont_x, cont_y):
                report_priority(1)
                return None

            # Otherwise choose the least-bad move (prefer tail tiles, avoid risky_next)
            candidates = []
            for direction, (dx, dy) in directions.items():
                if direction == opposites.get(current_dir):
                    continue
                nx, ny = head[0] + dx, head[1] + dy
                if nx < 0 or nx >= self.grid_width or ny < 0 or ny >= self.grid_height:
                    continue
                candidates.append({"direction": direction, "x": nx, "y": ny})

            best_dir = None
            best_score = float('-inf')
            for move in candidates:
                score = 0
                nx, ny = move["x"], move["y"]

                # Strongly avoid tiles adjacent to opponent heads
                if (nx, ny) in risky_next:
                    score -= 10000

                # Prefer moving into tail tiles (they may vacate)
                if (nx, ny) in tails:
                    score += 500

                # If currently occupied by a body segment (not tail), heavy penalty
                if (nx, ny) in dangerous and (nx, ny) not in tails:
                    score -= 5000

                # Prefer positions with more escape routes
                score += count_escape_routes(nx, ny) * 20

                # Slight preference for food
                if nearest_food:
                    food_dist = abs(nx - nearest_food["x"]) + abs(ny - nearest_food["y"]) 
                    score += (self.grid_width + self.grid_height - food_dist)

                if score > best_score:
                    best_score = score
                    best_dir = move["direction"]

            if best_dir:
                report_priority(1)
                return best_dir

            # As a last resort, return any non-reversing direction (may collide)
            for direction in directions:
                if direction != opposites.get(current_dir):
                    report_priority(1)
                    return direction
            report_priority(1)
            return current_dir

        # Apply Priority #2: filter out moves that lead to constrained spaces
        roomy_moves = []
        min_tiles_needed = 2 * my_length
        for move in safe_moves:
            rc = reachable_count(move["x"], move["y"], min_tiles_needed)
            if rc >= min_tiles_needed:
                roomy_moves.append(move)

        # If any roomy move exists, use only those. Otherwise proceed with all safe_moves
        candidate_moves = roomy_moves if roomy_moves else safe_moves

        # Priority #3: food targeting rules
        # 1) Prefer grapes (type == "grapes") except flashing grapes that are >30 tiles away
        # 2) Otherwise, target nearest food where we are closer than the opponent
        # If none match, fall back to scoring below.

        # Helper: find opponent head (if present)
        opponent_head = None
        for pid, s in snakes.items():
            try:
                pid_int = int(pid)
            except Exception:
                continue
            if pid_int != self.player_id:
                body = s.get("body", [])
                if body:
                    opponent_head = tuple(body[0])
                    break

        def manhattan(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        # Find valid grapes
        valid_grapes = []
        for f in foods:
            if f.get("type") != "grapes":
                continue
            fx, fy = f.get("x"), f.get("y")
            dist = abs(head[0] - fx) + abs(head[1] - fy)
            lifetime = f.get("lifetime")
            # Exclude flashing grapes that are >30 tiles away
            if lifetime is not None and dist > 30:
                continue
            valid_grapes.append((dist, fx, fy, f))

        if valid_grapes:
            # Choose nearest grape
            valid_grapes.sort(key=lambda x: x[0])
            target = (valid_grapes[0][1], valid_grapes[0][2])
            # Pick candidate move that reduces distance to target
            best_dir = None
            best_dist = float('inf')
            for move in candidate_moves:
                nx, ny = move["x"], move["y"]
                d = manhattan((nx, ny), target)
                if d < best_dist:
                    best_dist = d
                    best_dir = move["direction"]
            if best_dir:
                report_priority(3)
                return best_dir

        # No grapes chosen; find nearest food where we are closer than opponent
        candidate_foods = []
        for f in foods:
            fx, fy = f.get("x"), f.get("y")
            my_d = abs(head[0] - fx) + abs(head[1] - fy)
            opp_d = float('inf')
            if opponent_head:
                opp_d = abs(opponent_head[0] - fx) + abs(opponent_head[1] - fy)
            if my_d < opp_d:
                candidate_foods.append((my_d, fx, fy, f))

        if candidate_foods:
            candidate_foods.sort(key=lambda x: x[0])
            target = (candidate_foods[0][1], candidate_foods[0][2])
            best_dir = None
            best_dist = float('inf')
            for move in candidate_moves:
                nx, ny = move["x"], move["y"]
                d = manhattan((nx, ny), target)
                if d < best_dist:
                    best_dist = d
                    best_dir = move["direction"]
            if best_dir:
                report_priority(3)
                return best_dir

        # Priority #4 (revised): continue straight unless next to a wall, then
        # make a turn away from the wall. This keeps behavior simple and safe.
        # If possible, prefer continuing in the current direction.
        head_on_wall = head[0] in (0, self.grid_width - 1) or head[1] in (0, self.grid_height - 1)

        # If continuing straight is available, prefer it unless we're next to a wall and moving parallel to it
        on_left = head[0] == 0
        on_right = head[0] == self.grid_width - 1
        on_top = head[1] == 0
        on_bottom = head[1] == self.grid_height - 1
        parallel_to_wall = ((on_left or on_right) and current_dir in ("up", "down")) or ((on_top or on_bottom) and current_dir in ("left", "right"))

        for move in candidate_moves:
            if move["direction"] == current_dir:
                nx, ny = move["x"], move["y"]
                # avoid continuing if that tile is risky
                if (nx, ny) in risky_next:
                    break
                # If next to a wall and moving parallel to it, do not continue straight; choose a turn away instead
                if head_on_wall and parallel_to_wall:
                    break
                report_priority(4)
                return current_dir

        # If next to a wall, choose a move that increases distance from the nearest wall
        if head_on_wall:
            best_dir = None
            best_wall_dist = float('-inf')
            best_tie_escape = float('-inf')
            for move in candidate_moves:
                nx, ny = move["x"], move["y"]
                # avoid risky next-tick tiles
                if (nx, ny) in risky_next:
                    continue
                # distance to nearest wall after the move
                wall_dist = min(nx, self.grid_width - 1 - nx, ny, self.grid_height - 1 - ny)
                escape_routes = count_escape_routes(nx, ny)
                # prefer larger wall_dist, then more escape routes
                if wall_dist > best_wall_dist or (wall_dist == best_wall_dist and escape_routes > best_tie_escape):
                    best_wall_dist = wall_dist
                    best_tie_escape = escape_routes
                    best_dir = move["direction"]
            if best_dir:
                report_priority(4)
                return best_dir

        # Otherwise proceed to normal scoring (no special wall behavior)

        # SCORING - prefer candidate moves; heavily penalize moves that could become
        # obstacles next tick (risky_next).
        best_dir = None
        best_score = float('-inf')

        for move in candidate_moves:
            score = 0
            new_x, new_y = move["x"], move["y"]

            # Big bonus for landing directly on food
            for food in foods:
                if new_x == food["x"] and new_y == food["y"]:
                    score += 1000
                    break

            # Prefer moves that get closer to nearest food
            if nearest_food:
                food_dist = abs(new_x - nearest_food["x"]) + abs(new_y - nearest_food["y"]) 
                score += (self.grid_width + self.grid_height - food_dist) * 10

            # Prefer positions with more escape routes
            escape_routes = count_escape_routes(new_x, new_y)
            score += escape_routes * 50

            # Small bonus for staying away from walls
            edge_dist = min(new_x, self.grid_width - 1 - new_x,
                           new_y, self.grid_height - 1 - new_y)
            score += edge_dist * 5

            # Strongly avoid tiles that may become obstacles next tick
            if (new_x, new_y) in risky_next:
                score -= 10000

            # Update best move
            if score > best_score:
                best_score = score
                best_dir = move["direction"]

        # Determine which priority led to this selection and report it
        if roomy_moves:
            report_priority(2)
        else:
            report_priority(1)

        return best_dir


# ============================================================================
#  MAIN - Parse command line arguments and start the bot
# ============================================================================

async def main():
    parser = argparse.ArgumentParser(description="CopperHead Bot")
    parser.add_argument("--server", "-s", default=GAME_SERVER,
                        help=f"Server WebSocket URL (default: {GAME_SERVER})")
    parser.add_argument("--name", "-n", default=None,
                        help=f"Bot display name (default: {BOT_NAME})")
    parser.add_argument("--difficulty", "-d", type=int, default=5,
                        help="AI difficulty level 1-10 (1=most random, 10=deterministic)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress console output")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print per-tick priority numbers without newline")
    args = parser.parse_args()

    bot = MyBot(args.server, name=args.name)
    # Attach CLI flags to the bot instance so calculate_move can access them
    bot.verbose = args.verbose
    bot.quiet = args.quiet
    bot.difficulty = args.difficulty

    if not bot.quiet:
        print(f"{bot.name} v{BOT_VERSION}")
        print(f"  Server: {args.server}")
        print()

    await bot.play()


if __name__ == "__main__":
    asyncio.run(main())