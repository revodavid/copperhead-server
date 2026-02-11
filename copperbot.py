#!/usr/bin/env python3
"""
CopperHead Robot - Autonomous Snake game player.

Connects to a CopperHead server and plays the game using AI.
Launched by the Add Bot button in the game client, or can be run standalone.

STRATEGY OVERVIEW
-----------------
CopperBot uses a score-based decision system. Each tick, it evaluates all safe
(non-reversing, non-wall, non-snake) moves and picks the one with the highest
score. The scoring considers four factors:

  1. Food pursuit: Strong bonus for landing on food, plus a distance-based
     bonus for moves that get closer to the nearest food item. Apples are
     slightly preferred over other food types.

  2. Survival: Moves that leave more escape routes (safe neighboring tiles)
     score higher, reducing the chance of getting trapped.

  3. Edge avoidance: A small bonus for staying away from walls, which keeps
     more options open for future moves.

  4. Head-on collision handling: The bot predicts where the opponent's head
     will be next tick (assuming no direction change) and adjusts its score
     for that tile based on difficulty level:
       - Level 1:    Always avoid the predicted tile.
       - Level 2-5:  Avoid with decreasing probability (90% to 10%).
       - Level 6-9:  Seek the collision (if longer) with increasing
                     probability (10% to 90%), otherwise avoid.
       - Level 10:   Always seek the collision if longer, otherwise avoid.

  5. Randomness: Lower difficulty levels introduce random score penalties,
     making the bot less consistent and easier to beat.

The bot also excludes tail segments from its danger map, since tails vacate
their position on the next tick (unless the snake just ate).

CUSTOMIZATION
-------------
To modify CopperBot's behavior, adjust the score weights in calculate_move():
  - collision_bonus / collision_penalty: Head-on collision aggression
  - Food bonus (1000): How much the bot prioritizes eating
  - escape_routes weight (50): How cautious the bot is about trapping itself
  - edge_dist weight (5): How much the bot avoids walls
  - mistake_chance: How often low-difficulty bots make random errors
"""

import asyncio
import json
import argparse
import random
import websockets
from collections import deque


class RobotPlayer:
    """Autonomous player that connects to CopperHead server and plays using AI."""
    
    def __init__(self, server_url: str, name: str = None, difficulty: int = 5, quiet: bool = False):
        self.server_url = server_url
        self.name = name or f"CopperBot L{difficulty}"
        self.difficulty = max(1, min(10, difficulty))
        self.quiet = quiet
        self.player_id = None
        self.game_state = None
        self.running = False
        self.wins = 0
        self.games_played = 0
        self.room_id = None
        # Grid dimensions - will be set from server game state
        self.grid_width = 30   # Default, updated when game state received
        self.grid_height = 20  # Default, updated when game state received
    
    def log(self, msg: str):
        if not self.quiet:
            # Replace emoji/special chars that Windows console can't display
            print(msg.encode("ascii", errors="replace").decode("ascii"))
        
    async def wait_for_open_competition(self):
        """Wait until a competition is accepting players."""
        import aiohttp
        
        base_url = self.server_url.rstrip("/")
        if base_url.endswith("/ws"):
            base_url = base_url[:-3]
        # Convert ws:// to http://
        http_url = base_url.replace("ws://", "http://").replace("wss://", "https://")
        
        while True:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{http_url}/competition") as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            state = data.get("state", "")
                            if state == "waiting_for_players":
                                self.log("Competition open - joining...")
                                return True
                            else:
                                self.log(f"Competition in progress ({state}), waiting...")
                        else:
                            self.log(f"Server not ready (status {resp.status}), waiting...")
            except Exception as e:
                self.log(f"Cannot reach server: {e}, waiting...")
            
            await asyncio.sleep(5)  # Wait 5 seconds before retrying
    
    async def connect(self):
        """Connect to the game server using auto-matchmaking."""
        # Wait for competition to be open
        await self.wait_for_open_competition()
        
        # Use the /join endpoint for auto-matchmaking
        base_url = self.server_url.rstrip("/")
        if base_url.endswith("/ws"):
            base_url = base_url[:-3]
        url = f"{base_url}/ws/join"
        
        try:
            self.log(f"Connecting to {url}...")
            self.ws = await websockets.connect(url)
            self.log(f"Connected! Waiting for player assignment...")
            return True
        except Exception as e:
            self.log(f"Connection failed: {e}")
            return False
    
    async def play(self):
        """Main game loop - terminates on disconnect or competition end."""
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
        """Handle incoming server messages."""
        msg_type = data.get("type")
        
        if msg_type == "error":
            # Server rejected us - likely competition in progress
            error_msg = data.get("message", "Unknown error")
            self.log(f"Server error: {error_msg}")
            # Connection will be closed by server, we'll exit gracefully
            self.running = False
            return
        
        if msg_type == "joined":
            # Server assigned us a player ID and room
            self.player_id = data.get("player_id")
            self.room_id = data.get("room_id")
            self.log(f"Joined Room {self.room_id} as Player {self.player_id}")
            
            # Send ready message
            await self.ws.send(json.dumps({
                "action": "ready",
                "mode": "two_player",
                "name": self.name
            }))
            self.log(f"Ready! Playing as '{self.name}' at difficulty {self.difficulty}")
        
        elif msg_type == "state":
            self.game_state = data.get("game")
            # Update grid dimensions from server
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
            self.games_played += 1
            winner = data.get("winner")
            my_wins = data.get("wins", {}).get(str(self.player_id), 0) or data.get("wins", {}).get(self.player_id, 0)
            opp_id = 3 - self.player_id
            opp_wins = data.get("wins", {}).get(str(opp_id), 0) or data.get("wins", {}).get(opp_id, 0)
            points_to_win = data.get("points_to_win", 5)
            
            if winner == self.player_id:
                self.wins += 1
                self.log(f"Won game! (Match: {my_wins}-{opp_wins}, first to {points_to_win})")
            elif winner:
                self.log(f"Lost game! (Match: {my_wins}-{opp_wins}, first to {points_to_win})")
            else:
                self.log(f"Draw! (Match: {my_wins}-{opp_wins}, first to {points_to_win})")
            
            # Signal ready for next game in the match
            await self.ws.send(json.dumps({
                "action": "ready",
                "name": self.name
            }))
            self.log("Ready for next game...")
        
        elif msg_type == "match_complete":
            # Match is over - check if we won or lost
            winner_id = data.get("winner", {}).get("player_id")
            winner_name = data.get("winner", {}).get("name", "Unknown")
            final_score = data.get("final_score", {})
            my_score = final_score.get(str(self.player_id), 0) or final_score.get(self.player_id, 0)
            opp_id = 3 - self.player_id
            opp_score = final_score.get(str(opp_id), 0) or final_score.get(opp_id, 0)
            
            if winner_id == self.player_id:
                self.log(f"Match won! Final: {my_score}-{opp_score}")
                self.log("Waiting for next round assignment...")
                # Don't sleep - server will send match_assigned for next round
            else:
                self.log(f"Match lost to {winner_name}. Final: {my_score}-{opp_score}")
                self.log("Exiting.")
                self.running = False
        
        elif msg_type == "match_assigned":
            # Assigned to a new match (Round 2+)
            self.room_id = data.get("room_id")
            self.player_id = data.get("player_id")
            self.game_state = None  # Reset game state for new match
            opponent = data.get("opponent", "Opponent")
            self.log(f"Assigned to Arena {self.room_id} as Player {self.player_id} vs {opponent}")
        
        elif msg_type == "competition_complete":
            # Competition is over
            champion = data.get("champion", {}).get("name", "Unknown")
            self.log(f"Competition complete! Champion: {champion}")
            self.log("Exiting.")
            self.running = False
            
        elif msg_type == "waiting":
            self.log("Waiting for opponent...")
    
    def calculate_move(self) -> str | None:
        """Calculate the best move using AI logic.

        Evaluates all safe moves and returns the direction with the highest
        score. See the module docstring for a full description of the strategy.
        """
        if not self.game_state:
            return None
            
        snakes = self.game_state.get("snakes", {})
        my_snake = snakes.get(str(self.player_id))
        
        if not my_snake or not my_snake.get("body"):
            return None
            
        head = my_snake["body"][0]
        current_dir = my_snake.get("direction", "right")
        
        # Get food - support both old API (food) and new API (foods)
        foods = self.game_state.get("foods", [])
        if not foods and self.game_state.get("food"):
            # Backward compatibility with old API
            old_food = self.game_state.get("food")
            foods = [{"x": old_food[0], "y": old_food[1], "type": "apple"}]
        
        # Find the nearest food (prefer apples)
        nearest_food = None
        nearest_dist = float('inf')
        for food in foods:
            dist = abs(head[0] - food["x"]) + abs(head[1] - food["y"])
            # Prefer apples (they make us grow)
            if food.get("type") == "apple":
                dist -= 0.5  # Slight preference for apples
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_food = food
        
        # Build set of dangerous positions (snake bodies, excluding tails)
        # 
        # SNAKE MOVEMENT MECHANICS:
        # When a snake moves, its head advances to a new position and its tail
        # vacates its current position (unless the snake just ate food and grows).
        # This means tail positions will be SAFE on the next tick in most cases.
        # 
        # By excluding tails from the dangerous set, the bot can:
        # - Move into positions that tails currently occupy (they'll be gone)
        # - Find more escape routes when surrounded
        # - Make less defensive, more effective decisions
        #
        # Note: If you want perfect accuracy, you'd also check if a snake's head
        # is on food (meaning it will grow and the tail stays). For simplicity,
        # we assume tails always move.
        dangerous = set()
        for snake_data in snakes.values():
            body = snake_data.get("body", [])
            # Exclude the last segment (tail) - it will move on the next tick
            for segment in body[:-1]:
                dangerous.add((segment[0], segment[1]))
        
        # Possible moves
        directions = {
            "up": (0, -1),
            "down": (0, 1),
            "left": (-1, 0),
            "right": (1, 0)
        }
        
        # Can't reverse
        opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
        
        # Use instance grid dimensions
        grid_width = self.grid_width
        grid_height = self.grid_height
        
        def is_safe(x, y):
            """Check if position is safe (not wall, not snake)."""
            if x < 0 or x >= grid_width or y < 0 or y >= grid_height:
                return False
            if (x, y) in dangerous:
                return False
            return True
        
        def count_safe_neighbors(x, y):
            """Count how many safe moves are available from a position."""
            count = 0
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy
                if is_safe(nx, ny):
                    count += 1
            return count
        
        # First pass: find all safe moves
        safe_moves = []
        for direction, (dx, dy) in directions.items():
            if direction == opposites.get(current_dir):
                continue
            new_x = head[0] + dx
            new_y = head[1] + dy
            if is_safe(new_x, new_y):
                safe_moves.append({"direction": direction, "x": new_x, "y": new_y})
        
        # If no safe moves, pick any non-reversing move (we're doomed)
        if not safe_moves:
            for direction in directions:
                if direction != opposites.get(current_dir):
                    return direction
            return current_dir
        
        # Evaluate safe moves
        best_dir = None
        best_score = float('-inf')
        
        # Predict opponent's next head position (assuming they don't change direction)
        opponent_id = 3 - self.player_id
        opponent = snakes.get(str(opponent_id))
        opp_next = None
        my_length = len(my_snake.get("body", []))
        opp_length = 0
        if opponent and opponent.get("body"):
            opp_head = opponent["body"][0]
            opp_dir = opponent.get("direction", "left")
            dir_vec = {"up": (0, -1), "down": (0, 1),
                       "left": (-1, 0), "right": (1, 0)}.get(opp_dir, (0, 0))
            opp_next = (opp_head[0] + dir_vec[0], opp_head[1] + dir_vec[1])
            opp_length = len(opponent.get("body", []))
        
        for move in safe_moves:
            score = 0
            new_x, new_y = move["x"], move["y"]
            
            # Head-on collision logic based on difficulty level
            #
            # The bot predicts where the opponent's head will be next tick
            # (assuming no direction change) and adjusts its score for that
            # tile based on difficulty:
            #
            #   Level 1:    Always avoid the predicted tile.
            #   Level 2-5:  Avoid with probability 90%-10% (interpolated),
            #               otherwise prioritize the tile.
            #   Level 6-9:  Prioritize the tile (if we're longer) with
            #               probability 10%-90% (interpolated),
            #               otherwise avoid it.
            #   Level 10:   Prioritize the tile if we're longer,
            #               otherwise avoid it.
            if opp_next and (new_x, new_y) == opp_next:
                collision_bonus = 2000   # reward for seeking head-on collision
                collision_penalty = -5000  # penalty for risking head-on collision

                if self.difficulty == 1:
                    # Always avoid
                    score += collision_penalty
                elif self.difficulty <= 5:
                    # Levels 2-5: avoid probability 90%->10%
                    avoid_prob = 0.9 - (self.difficulty - 2) * 0.8 / 3
                    if random.random() < avoid_prob:
                        score += collision_penalty
                    else:
                        score += collision_bonus
                elif self.difficulty <= 9:
                    # Levels 6-9: prioritize if longer, with probability 10%->90%
                    prioritize_prob = 0.1 + (self.difficulty - 6) * 0.8 / 3
                    if my_length > opp_length and random.random() < prioritize_prob:
                        score += collision_bonus
                    else:
                        score += collision_penalty
                else:
                    # Level 10: always prioritize if longer, otherwise avoid
                    if my_length > opp_length:
                        score += collision_bonus
                    else:
                        score += collision_penalty
            
            # Big bonus for capturing any food
            for food in foods:
                if new_x == food["x"] and new_y == food["y"]:
                    score += 1000  # Always prioritize eating
                    break
            
            # Prioritize moves that don't trap us (have escape routes)
            escape_routes = count_safe_neighbors(new_x, new_y)
            score += escape_routes * 50  # Important but not more than food
            
            # Distance to nearest food (closer is better)
            if nearest_food:
                food_dist = abs(new_x - nearest_food["x"]) + abs(new_y - nearest_food["y"])
                score += (grid_width + grid_height - food_dist) * 10
            
            # Prefer staying away from edges
            edge_dist = min(new_x, grid_width - 1 - new_x, 
                           new_y, grid_height - 1 - new_y)
            score += edge_dist * 5
            
            # Random factor based on difficulty (lower = more random)
            mistake_chance = (10 - self.difficulty) / 20
            if random.random() < mistake_chance:
                score -= random.randint(0, 30)
            
            if score > best_score:
                best_score = score
                best_dir = move["direction"]
        
        return best_dir


async def main():
    parser = argparse.ArgumentParser(description="CopperHead Robot Player")
    parser.add_argument("--server", "-s", default="ws://localhost:8765/ws/",
                        help="Server WebSocket URL (default: ws://localhost:8765/ws/)")
    parser.add_argument("--name", "-n", default=None,
                        help="Bot display name (default: CopperBot L<difficulty>)")
    parser.add_argument("--difficulty", "-d", type=int, default=5,
                        help="AI difficulty 1-10 (default: 5)")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Suppress output (for spawned bots)")
    args = parser.parse_args()
    
    robot = RobotPlayer(args.server, name=args.name, difficulty=args.difficulty, quiet=args.quiet)
    
    if not args.quiet:
        print("CopperHead Robot Player")
        print(f"   Server: {args.server}")
        print(f"   Difficulty: {args.difficulty}")
        print()
    
    await robot.play()


if __name__ == "__main__":
    asyncio.run(main())
