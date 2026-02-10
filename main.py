"""CopperHead Server - 2-player Snake game server with competition mode."""

import argparse
import asyncio
import json
import os
import random
import logging
import subprocess
import sys
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("copperhead")

# Server configuration (set by CLI args or defaults)
class ServerConfig:
    arenas: int = 1
    points_to_win: int = 5
    reset_delay: int = 10
    grid_width: int = 30
    grid_height: int = 20
    tick_rate: float = 0.15
    bots: int = 0
    # Fruit settings
    fruit_warning: int = 20  # Ticks before expiry when lifetime is reported to client
    max_fruits: int = 1  # Max fruits on screen at once
    fruit_interval: int = 5  # Min ticks between fruit spawns
    # Fruit properties: {type: {"propensity": int, "lifetime": int (0=infinite)}}
    fruits: dict = None
    
    def __init__(self):
        # Default fruit config: only apples, never expire
        self.fruits = {
            "apple": {"propensity": 1, "lifetime": 0},
            "orange": {"propensity": 0, "lifetime": 0},
            "lemon": {"propensity": 0, "lifetime": 0},
            "grapes": {"propensity": 0, "lifetime": 0},
            "strawberry": {"propensity": 0, "lifetime": 0},
            "banana": {"propensity": 0, "lifetime": 0},
            "peach": {"propensity": 0, "lifetime": 0},
            "cherry": {"propensity": 0, "lifetime": 0},
            "watermelon": {"propensity": 0, "lifetime": 0},
            "kiwi": {"propensity": 0, "lifetime": 0},
        }

config = ServerConfig()

# For backward compatibility
GRID_WIDTH = property(lambda self: config.grid_width)
GRID_HEIGHT = property(lambda self: config.grid_height)
TICK_RATE = property(lambda self: config.tick_rate)

app = FastAPI(title="CopperHead Server")

# Enable CORS for client requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    logger.info("🐍 CopperHead Server started")
    logger.info(f"   Grid: {config.grid_width}x{config.grid_height}, Tick rate: {config.tick_rate}s")
    logger.info(f"   Arenas: {config.arenas}, Points to win: {config.points_to_win}")
    
    # Detect Codespaces environment
    codespace_name = os.environ.get("CODESPACE_NAME")
    github_domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
    
    if codespace_name:
        ws_url = f"wss://{codespace_name}-8765.{github_domain}/ws/"
    else:
        ws_url = "ws://localhost:8765/ws/"
    
    # Only show full connection info if not launched via start.py (which shows its own banner)
    if not os.environ.get("COPPERHEAD_QUIET_STARTUP"):
        if codespace_name:
            logger.info("")
            logger.info("=" * 60)
            logger.info("📡 CLIENT CONNECTION URL:")
            logger.info(f"   {ws_url}")
            logger.info("")
            logger.info("⚠️  IMPORTANT: Make port 8765 public!")
            logger.info("   1. Open the Ports tab (bottom panel)")
            logger.info("   2. Right-click port 8765 → Port Visibility → Public")
            logger.info("=" * 60)
            logger.info("")
        else:
            logger.info("")
            logger.info("📡 Client connection URL: ws://localhost:8765/ws/")
            logger.info("")
    
    # Initialize competition
    await competition.start_waiting()
    
    # Build client URL with server parameter
    import urllib.parse
    client_base = "https://revodavid.github.io/copperhead-client/"
    client_url = f"{client_base}?server={urllib.parse.quote(ws_url, safe='')}"
    
    # Show URL reminder at the bottom so it's visible after all startup messages
    logger.info("")
    logger.info(f"📡 Server URL: {ws_url}")
    logger.info(f"🎮 Play now: {client_url}")
    if codespace_name:
        logger.info(f"⚠️  Remember to make port 8765 PUBLIC in the Ports tab!")
    
    # Start config file watcher for auto-restart on config changes
    if _config_file_path:
        asyncio.create_task(watch_config_file())
        logger.info(f"👁️ Watching {os.path.basename(_config_file_path)} for changes")


class CompetitionState(Enum):
    WAITING_FOR_PLAYERS = "waiting_for_players"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    RESETTING = "resetting"


class PlayerInfo:
    """Track a player in the competition."""
    def __init__(self, player_uid: str, name: str, websocket: WebSocket, is_bot: bool = False):
        self.uid = player_uid  # Unique ID across competition
        self.name = name
        self.websocket = websocket
        self.is_bot = is_bot  # True if this is a CopperBot
        self.match_wins = 0  # Matches won in competition
        self.game_points = 0  # Total game points across all matches
        self.opponent_points = 0  # Opponent's total points (for tiebreaker)
        self.eliminated = False
        self.current_room: Optional["GameRoom"] = None
        self.current_player_id: Optional[int] = None  # 1 or 2 in current room
        self.last_match_finish_time: float = 0  # Timestamp when last match finished (for Bye tiebreaker)


class MatchResult:
    """Result of a completed match."""
    def __init__(self, player1_uid: str, player2_uid: str, winner_uid: str,
                 player1_points: int, player2_points: int):
        self.player1_uid = player1_uid
        self.player2_uid = player2_uid
        self.winner_uid = winner_uid
        self.player1_points = player1_points
        self.player2_points = player2_points


class Competition:
    """Manages a round-robin knockout competition."""
    
    # Class-level history persists across competition resets
    championship_history: list[dict] = []
    
    def __init__(self):
        self.state = CompetitionState.WAITING_FOR_PLAYERS
        self.players: dict[str, PlayerInfo] = {}  # uid -> PlayerInfo
        self.current_round = 0
        self.rounds: list[list[tuple[str, str]]] = []  # Each round is list of (uid1, uid2) pairings
        self.match_results: list[list[MatchResult]] = []  # Results per round
        self.champion_uid: Optional[str] = None
        self.current_bye_uid: Optional[str] = None  # Player with Bye in current round
        self._lock = asyncio.Lock()
        self._next_uid = 1
        self.reset_start_time: Optional[float] = None  # Track when reset countdown started
    
    def _generate_uid(self) -> str:
        uid = f"P{self._next_uid}"
        self._next_uid += 1
        return uid
    
    async def start_waiting(self):
        """Initialize competition to waiting state."""
        # Clear all rooms - bots will disconnect themselves when they receive
        # competition_complete or when their websocket closes
        room_manager.clear_all_rooms()
        
        self.state = CompetitionState.WAITING_FOR_PLAYERS
        self.players.clear()
        self.current_round = 0
        self.rounds.clear()
        self.match_results.clear()
        self.champion_uid = None
        self.current_bye_uid = None
        self.reset_start_time = None
        self._next_uid = 1
        logger.info(f"🏆 Competition waiting for {config.arenas * 2} players")
        
        # Spawn bots for the new competition
        if config.bots > 0:
            import threading
            def delayed_bot_spawn():
                import time
                time.sleep(1)
                spawn_initial_bots(config.bots)
            threading.Thread(target=delayed_bot_spawn, daemon=True).start()
    
    def required_players(self) -> int:
        return config.arenas * 2
    
    async def register_player(self, name: str, websocket: WebSocket) -> Optional[PlayerInfo]:
        """Register a player for the competition. Returns PlayerInfo if accepted."""
        async with self._lock:
            if self.state != CompetitionState.WAITING_FOR_PLAYERS:
                return None
            
            if len(self.players) >= self.required_players():
                return None
            
            uid = self._generate_uid()
            is_bot = name.startswith("CopperBot")
            player = PlayerInfo(uid, name, websocket, is_bot=is_bot)
            self.players[uid] = player
            
            logger.info(f"📝 {name} ({uid}) registered ({len(self.players)}/{self.required_players()})")
            
            # Broadcast updated lobby status
            await self._broadcast_lobby_status()
            
            # Check if we have enough players to start
            if len(self.players) >= self.required_players():
                await self._start_competition()
            
            return player
    
    async def unregister_player(self, uid: str):
        """Remove a player from competition."""
        async with self._lock:
            if uid not in self.players:
                return
            
            player = self.players[uid]
            
            if self.state == CompetitionState.WAITING_FOR_PLAYERS:
                del self.players[uid]
                logger.info(f"📝 {player.name} ({uid}) left lobby ({len(self.players)}/{self.required_players()})")
                await self._broadcast_lobby_status()
            elif self.state == CompetitionState.IN_PROGRESS:
                # Mark as eliminated - opponent wins by forfeit
                player.eliminated = True
                logger.info(f"🚪 {player.name} ({uid}) disconnected - forfeit")
                
                # If this player has a Bye, they forfeit it and we need to handle round advancement
                if self.current_bye_uid == uid:
                    logger.info(f"🎫 Bye player {player.name} disconnected - eliminated")
                    self.current_bye_uid = None
                    # Check if this was the last match needed to advance
                    if self.match_results and len(self.match_results[self.current_round - 1]) >= len(self.rounds[self.current_round - 1]):
                        await self._advance_round()
                # The room will handle the forfeit logic for active games
    
    async def _broadcast_lobby_status(self):
        """Send lobby status to all waiting players."""
        status = {
            "type": "lobby_status",
            "players": [{"uid": p.uid, "name": p.name} for p in self.players.values()],
            "required": self.required_players(),
            "current": len(self.players)
        }
        for player in self.players.values():
            try:
                await player.websocket.send_json(status)
            except Exception:
                pass
    
    async def _start_competition(self):
        """Start the competition with all registered players."""
        self.state = CompetitionState.IN_PROGRESS
        self.current_round = 1
        
        # Randomly pair players for round 1
        uids = list(self.players.keys())
        random.shuffle(uids)
        pairings = [(uids[i], uids[i + 1]) for i in range(0, len(uids), 2)]
        self.rounds.append(pairings)
        self.match_results.append([])
        
        logger.info(f"🏆 Competition started! Round 1 with {len(pairings)} matches")
        for i, (uid1, uid2) in enumerate(pairings):
            p1, p2 = self.players[uid1], self.players[uid2]
            logger.info(f"   Arena {i + 1}: {p1.name} vs {p2.name}")
        
        # Notify all players and create rooms
        await self._broadcast_competition_status()
        await self._create_round_matches()
    
    async def _create_round_matches(self):
        """Create game rooms for current round's matches."""
        pairings = self.rounds[self.current_round - 1]
        
        for arena_id, (uid1, uid2) in enumerate(pairings, 1):
            player1 = self.players[uid1]
            player2 = self.players[uid2]
            
            # Create a room for this match
            room = room_manager.create_competition_room(arena_id, uid1, uid2)
            
            player1.current_room = room
            player1.current_player_id = 1
            player2.current_room = room
            player2.current_player_id = 2
            
            # Connect players to their room
            await room.connect_competition_player(1, player1)
            await room.connect_competition_player(2, player2)
        
        # Notify observers in lobby about new rooms so they get reassigned
        await room_manager.broadcast_room_list_to_all_observers()
    
    async def report_match_complete(self, room: "GameRoom", winner_uid: str, 
                                     p1_uid: str, p2_uid: str, p1_points: int, p2_points: int):
        """Called when a match (first to points_to_win) completes."""
        import time
        async with self._lock:
            try:
                result = MatchResult(p1_uid, p2_uid, winner_uid, p1_points, p2_points)
                self.match_results[self.current_round - 1].append(result)
                
                # Update player stats
                if winner_uid not in self.players:
                    logger.error(f"❌ Winner UID {winner_uid} not in competition players: {list(self.players.keys())}")
                    return
                winner = self.players[winner_uid]
                loser_uid = p2_uid if winner_uid == p1_uid else p1_uid
                if loser_uid not in self.players:
                    logger.error(f"❌ Loser UID {loser_uid} not in competition players: {list(self.players.keys())}")
                    return
                loser = self.players[loser_uid]
                
                winner.match_wins += 1
                winner.game_points += p1_points if winner_uid == p1_uid else p2_points
                winner.opponent_points += p2_points if winner_uid == p1_uid else p1_points
                winner.last_match_finish_time = time.time()  # Track for Bye tiebreaker
                loser.game_points += p2_points if winner_uid == p1_uid else p1_points
                loser.opponent_points += p1_points if winner_uid == p1_uid else p2_points
                loser.eliminated = True
                loser.current_room = None  # Prevent disconnect from affecting new rooms
                loser.current_player_id = None
                
                logger.info(f"🏆 Match complete: {winner.name} defeats {loser.name} ({p1_points}-{p2_points})")
                
                # Check if all matches in round are complete
                pairings = self.rounds[self.current_round - 1]
                logger.info(f"📊 Round {self.current_round}: {len(self.match_results[self.current_round - 1])}/{len(pairings)} matches complete")
                if len(self.match_results[self.current_round - 1]) >= len(pairings):
                    await self._advance_round()
            except Exception as e:
                logger.error(f"❌ Error in report_match_complete: {e}")
                import traceback
                traceback.print_exc()
    
    async def _advance_round(self):
        """Advance to next round or declare champion."""
        # Get winners from current round
        winners = [r.winner_uid for r in self.match_results[self.current_round - 1]]
        
        logger.info(f"📊 Round {self.current_round} complete. Winners: {[self.players[uid].name for uid in winners]}")
        
        # Clear all rooms from previous round
        room_manager.clear_all_rooms()
        
        # Reset bye for new round
        self.current_bye_uid = None
        
        if len(winners) == 1:
            # We have a champion!
            import time
            self.champion_uid = winners[0]
            self.state = CompetitionState.COMPLETE
            self.reset_start_time = time.time()  # Start countdown immediately
            champion = self.players[self.champion_uid]
            logger.info(f"🎉 Competition complete! Champion: {champion.name}")
            
            # Record in championship history
            Competition.championship_history.append({
                "champion": champion.name,
                "players": len(self.players),
                "timestamp": datetime.now().isoformat()
            })
            
            await self._broadcast_competition_complete()
            # Schedule reset
            asyncio.create_task(self._schedule_reset())
            return
        
        # Handle odd number of winners - highest scorer gets a Bye
        bye_player = None
        if len(winners) % 2 == 1:
            # Sort winners by: game_points (desc), finish_time (asc), random tiebreaker
            winner_players = [self.players[uid] for uid in winners]
            winner_players.sort(
                key=lambda p: (-p.game_points, p.last_match_finish_time, random.random())
            )
            bye_player = winner_players[0]
            winners.remove(bye_player.uid)
            self.current_bye_uid = bye_player.uid
            logger.info(f"🎫 {bye_player.name} receives Bye (highest scorer with {bye_player.game_points} points)")
        
        # Create next round pairings from remaining winners
        self.current_round += 1
        random.shuffle(winners)
        pairings = [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]
        self.rounds.append(pairings)
        self.match_results.append([])
        
        logger.info(f"🏆 Round {self.current_round} starting with {len(pairings)} match(es)")
        
        # If there was a Bye player, they auto-advance to next round's results
        if bye_player:
            import time
            # Create a "Bye" result - player advances without playing
            bye_result = MatchResult(bye_player.uid, bye_player.uid, bye_player.uid, 0, 0)
            self.match_results[self.current_round - 1].append(bye_result)
            bye_player.last_match_finish_time = time.time()
            logger.info(f"🎫 {bye_player.name} auto-advances via Bye")
        
        await self._broadcast_competition_status()
        # Pause so observers can see round results before next round begins
        await asyncio.sleep(5)
        await self._create_round_matches()
    
    async def _broadcast_competition_status(self):
        """Send competition status to all players."""
        pairings = self.rounds[self.current_round - 1] if self.rounds else []
        status = {
            "type": "competition_status",
            "state": self.state.value,
            "round": self.current_round,
            "total_rounds": self._calculate_total_rounds(),
            "pairings": [
                {
                    "arena": i + 1,
                    "player1": {"uid": uid1, "name": self.players[uid1].name},
                    "player2": {"uid": uid2, "name": self.players[uid2].name}
                }
                for i, (uid1, uid2) in enumerate(pairings)
            ]
        }
        for player in self.players.values():
            try:
                await player.websocket.send_json(status)
            except Exception:
                pass
    
    async def _broadcast_competition_complete(self):
        """Announce competition winner."""
        champion = self.players[self.champion_uid]
        msg = {
            "type": "competition_complete",
            "champion": {"uid": champion.uid, "name": champion.name},
            "reset_in": config.reset_delay
        }
        for player in self.players.values():
            try:
                await player.websocket.send_json(msg)
            except Exception:
                pass
    
    async def _schedule_reset(self):
        """Wait and then reset competition."""
        # State stays COMPLETE (set by caller), countdown already started
        logger.info(f"⏳ Competition resetting in {config.reset_delay} seconds...")
        await asyncio.sleep(config.reset_delay)
        await self.start_waiting()
        logger.info("🔄 Competition reset - ready for new players")
    
    def _calculate_total_rounds(self) -> int:
        """Calculate total rounds needed based on arenas configuration."""
        import math
        # With N arenas, we have 2N players, so we need ceil(log2(2N)) rounds
        # This equals ceil(log2(2 * arenas)) = ceil(1 + log2(arenas))
        return max(1, math.ceil(math.log2(config.arenas * 2))) if config.arenas > 0 else 1
    
    def get_status(self) -> dict:
        """Get current competition status."""
        import time
        bye_player_name = None
        if self.current_bye_uid and self.current_bye_uid in self.players:
            bye_player_name = self.players[self.current_bye_uid].name
        
        # Calculate remaining reset time
        reset_in = 0
        if self.reset_start_time and self.state == CompetitionState.COMPLETE:
            elapsed = time.time() - self.reset_start_time
            reset_in = max(0, int(config.reset_delay - elapsed))
        
        return {
            "state": self.state.value,
            "round": self.current_round if self.current_round > 0 else 1,
            "total_rounds": self._calculate_total_rounds(),
            "players": len(self.players),
            "required": self.required_players(),
            "champion": self.players[self.champion_uid].name if self.champion_uid else None,
            "points_to_win": config.points_to_win,
            "bye_player": bye_player_name,
            "reset_in": reset_in
        }
    
    def get_remaining_matches(self) -> int:
        """Get number of matches remaining in current round."""
        if not self.rounds or self.current_round == 0:
            return 0
        pairings = self.rounds[self.current_round - 1]
        completed = len(self.match_results[self.current_round - 1]) if self.match_results else 0
        return len(pairings) - completed


# Global competition instance
competition = Competition()


class Snake:
    def __init__(self, player_id: int, start_pos: tuple[int, int], direction: str):
        self.player_id = player_id
        self.body = [start_pos]
        self.direction = direction
        self.next_direction = direction
        self.input_queue: list[str] = []
        self.alive = True
        self.buff = "default"  # Current active buff (default, speed, shield, inversion, lucky, slow, scissors, ghost)
        self.changed_direction_last_move = False  # Track if direction changed in last move

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
        old_direction = self.direction
        if self.input_queue:
            new_dir = self.input_queue.pop(0)
            opposites = {"up": "down", "down": "up", "left": "right", "right": "left"}
            if opposites.get(new_dir) != self.direction:
                self.next_direction = new_dir
        self.changed_direction_last_move = (self.next_direction != old_direction)

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
            "buff": self.buff,
        }


class Game:
    # Available fruit types
    FRUIT_TYPES = ["apple", "orange", "lemon", "grapes", "strawberry", "banana", "peach", "cherry", "watermelon", "kiwi"]
    
    def __init__(self, mode: str = "two_player"):
        self.mode = mode
        self.reset()

    def reset(self):
        # Snakes start on different rows to avoid head-on collision
        self.snakes: dict[int, Snake] = {
            1: Snake(1, (5, config.grid_height // 2), "right"),
            2: Snake(2, (config.grid_width - 6, config.grid_height // 2 + 1), "left"),
        }
        self.foods: list[dict] = []  # List of {"x": int, "y": int, "type": str, "lifetime": int or None}
        self.running = False
        self.winner: Optional[int] = None
        self.ticks_since_last_fruit = config.fruit_interval  # Allow immediate first spawn

    def choose_fruit_type(self) -> Optional[str]:
        """Choose a random fruit type based on propensity weights. Returns None if no fruits configured."""
        weights = []
        types = []
        for fruit_type, props in config.fruits.items():
            propensity = props.get("propensity", 0)
            if propensity > 0:
                weights.append(propensity)
                types.append(fruit_type)
        if not weights:
            return None
        return random.choices(types, weights=weights, k=1)[0]

    def spawn_food_if_needed(self):
        """Spawn a food item if conditions are met (interval elapsed, under max_fruits)."""
        if len(self.foods) >= config.max_fruits:
            return
        if self.ticks_since_last_fruit < config.fruit_interval:
            return
        
        fruit_type = self.choose_fruit_type()
        if not fruit_type:
            return
        
        # Get lifetime from config (in ticks, 0 = infinite)
        lifetime_ticks = config.fruits[fruit_type].get("lifetime", 0)
        lifetime = lifetime_ticks if lifetime_ticks > 0 else None
        
        occupied = set()
        for snake in self.snakes.values():
            occupied.update(snake.body)
        for food in self.foods:
            occupied.add((food["x"], food["y"]))
        available = [
            (x, y)
            for x in range(config.grid_width)
            for y in range(config.grid_height)
            if (x, y) not in occupied
        ]
        if available:
            pos = random.choice(available)
            self.foods.append({"x": pos[0], "y": pos[1], "type": fruit_type, "lifetime": lifetime})
            self.ticks_since_last_fruit = 0

    def get_food_at(self, pos: tuple[int, int]) -> Optional[dict]:
        """Get the food item at the given position, or None if no food there."""
        for food in self.foods:
            if (food["x"], food["y"]) == pos:
                return food
        return None

    def remove_food_at(self, pos: tuple[int, int]):
        """Remove the food item at the given position."""
        self.foods = [f for f in self.foods if (f["x"], f["y"]) != pos]

    def update_food_lifetimes(self):
        """Decrement food lifetimes (in ticks) and remove expired foods."""
        self.ticks_since_last_fruit += 1
        expired = []
        for food in self.foods:
            if food["lifetime"] is not None:
                food["lifetime"] -= 1
                if food["lifetime"] <= 0:
                    expired.append((food["x"], food["y"]))
        # Remove expired foods
        for pos in expired:
            self.remove_food_at(pos)
        # Try to spawn new food if needed
        self.spawn_food_if_needed()

    def update(self):
        if not self.running:
            return

        for snake in self.snakes.values():
            if snake.alive:
                # Calculate where the snake will actually move to (accounting for input queue)
                next_head = snake.get_next_head()
                
                # Check if next position has food
                food = self.get_food_at(next_head)
                grow = False
                
                if food:
                    if food["type"] == "apple":
                        # Apple: grow by one
                        grow = True
                    elif food["type"] == "grapes":
                        # Grapes: grow by one, shrink opponent by one
                        grow = True
                        for other in self.snakes.values():
                            if other.player_id != snake.player_id and len(other.body) > 1:
                                other.body.pop()  # Remove tail segment
                
                snake.move(grow)
                if food:
                    self.remove_food_at(next_head)
                    # New food will spawn via spawn_food_if_needed() in update_food_lifetimes()

        # Check collisions
        for snake in self.snakes.values():
            if not snake.alive:
                continue
            hx, hy = snake.head()
            # Wall collision
            if hx < 0 or hx >= config.grid_width or hy < 0 or hy >= config.grid_height:
                snake.alive = False
            # Self collision
            if snake.head() in snake.body[1:]:
                snake.alive = False
            # Other snake collision (body)
            for other in self.snakes.values():
                if other.player_id != snake.player_id:
                    if snake.head() in other.body:
                        snake.alive = False
        
        # Check head-on collision (both snakes' heads in same position or crossed paths)
        snake_list = list(self.snakes.values())
        if len(snake_list) == 2:
            s1, s2 = snake_list[0], snake_list[1]
            
            # Detect head-on collision (both alive, same position or crossed paths)
            if s1.alive and s2.alive and s1.head() == s2.head():
                # Both heads at same position - mark both as crashed
                s1.alive = False
                s2.alive = False
            elif s1.alive and s2.alive and len(s1.body) >= 2 and len(s2.body) >= 2:
                s1_prev_head = s1.body[1]
                s2_prev_head = s2.body[1]
                if s1.head() == s2_prev_head and s2.head() == s1_prev_head:
                    # Crossed paths - mark both as crashed
                    s1.alive = False
                    s2.alive = False

        # Check game over and apply tiebreaker rules for simultaneous crashes
        alive_snakes = [s for s in self.snakes.values() if s.alive]
        if len(alive_snakes) <= 1:
            self.running = False
            if len(alive_snakes) == 1:
                self.winner = alive_snakes[0].player_id
            elif len(snake_list) == 2:
                # Both snakes crashed simultaneously - apply tiebreaker rules:
                # 1. Longer snake wins
                # 2. If equal length, player who changed direction most recently loses
                # 3. Otherwise, draw (no points awarded)
                s1, s2 = snake_list[0], snake_list[1]
                s1_len = len(s1.body)
                s2_len = len(s2.body)
                s1_changed = s1.changed_direction_last_move
                s2_changed = s2.changed_direction_last_move
                
                if s1_len > s2_len:
                    self.winner = s1.player_id
                elif s2_len > s1_len:
                    self.winner = s2.player_id
                elif s1_changed and not s2_changed:
                    # S1 changed direction most recently, S1 loses, S2 wins
                    self.winner = s2.player_id
                elif s2_changed and not s1_changed:
                    # S2 changed direction most recently, S2 loses, S1 wins
                    self.winner = s1.player_id
                else:
                    # Equal length, both or neither changed direction - draw
                    self.winner = None
            else:
                self.winner = None  # Draw (fallback)

    def to_dict(self) -> dict:
        # Only report lifetime if within warning threshold
        foods_for_client = []
        for food in self.foods:
            food_data = {"x": food["x"], "y": food["y"], "type": food["type"]}
            if food["lifetime"] is not None and food["lifetime"] <= config.fruit_warning:
                food_data["lifetime"] = food["lifetime"]
            else:
                food_data["lifetime"] = None
            foods_for_client.append(food_data)
        
        return {
            "mode": self.mode,
            "grid": {"width": config.grid_width, "height": config.grid_height},
            "snakes": {pid: s.to_dict() for pid, s in self.snakes.items()},
            "foods": foods_for_client,
            "running": self.running,
            "winner": self.winner,
        }


class GameRoom:
    """Manages a single game room with two players and optional observers."""
    
    def __init__(self, room_id: int, room_manager: "RoomManager" = None):
        self.room_id = room_id
        self.room_manager = room_manager
        self.game = Game()
        self.connections: dict[int, WebSocket] = {}
        self.observers: list[WebSocket] = []
        self.ready: set[int] = set()
        self.game_task: Optional[asyncio.Task] = None
        self.bot_process: Optional[subprocess.Popen] = None
        self.wins: dict[int, int] = {1: 0, 2: 0}
        self.names: dict[int, str] = {1: "Player 1", 2: "Player 2"}
        
        # All rooms are competition rooms
        self.player_uids: dict[int, str] = {}
        self.competition_players: dict[int, PlayerInfo] = {}  # player_id -> PlayerInfo
        self.match_reported: bool = False  # Track if match result already reported
        self.match_complete: bool = False  # Track if this room's match is finished

    def is_empty(self) -> bool:
        return len(self.connections) == 0

    def is_waiting_for_player(self) -> bool:
        """Returns True if room has one player and space for another."""
        # Room is waiting if it has exactly 1 connection and game not running
        return len(self.connections) == 1 and not self.game.running

    def is_full(self) -> bool:
        return len(self.connections) >= 2

    def is_active(self) -> bool:
        """Returns True if game is running OR match completed (still in current round)."""
        return self.game.running or self.match_complete

    def get_available_slot(self) -> Optional[int]:
        if 1 not in self.connections:
            return 1
        if 2 not in self.connections:
            return 2
        return None

    async def connect_player(self, player_id: int, websocket: WebSocket):
        self.connections[player_id] = websocket
        logger.info(f"✅ [Room {self.room_id}] Player {player_id} connected ({len(self.connections)} player(s))")
        await self.broadcast_state()

    async def connect_observer(self, websocket: WebSocket):
        await websocket.accept()
        self.observers.append(websocket)
        logger.info(f"👁️ [Room {self.room_id}] Observer connected ({len(self.observers)} observer(s))")
        # Send current state to observer
        await websocket.send_json({
            "type": "observer_joined",
            "room_id": self.room_id,
            "game": self.game.to_dict(),
            "wins": self.wins,
            "names": self.names
        })

    async def connect_competition_player(self, player_id: int, player_info: "PlayerInfo"):
        """Connect a player in competition mode (websocket already accepted)."""
        logger.info(f"🔗 [Arena {self.room_id}] Connecting {player_info.name} as Player {player_id}, ws={player_info.websocket is not None}")
        self.connections[player_id] = player_info.websocket
        self.competition_players[player_id] = player_info
        self.names[player_id] = player_info.name
        self.ready.add(player_id)
        
        # Notify player of their assignment
        try:
            if player_info.websocket:
                await player_info.websocket.send_json({
                    "type": "match_assigned",
                    "room_id": self.room_id,
                    "player_id": player_id,
                    "opponent": self.names[3 - player_id] if (3 - player_id) in self.names else "Opponent",
                    "points_to_win": config.points_to_win
                })
                logger.info(f"📤 [Arena {self.room_id}] Sent match_assigned to {player_info.name}")
            else:
                logger.error(f"❌ [Arena {self.room_id}] {player_info.name} has no websocket!")
        except Exception as e:
            logger.error(f"❌ [Arena {self.room_id}] Failed to notify {player_info.name}: {e}")
        
        logger.info(f"✅ [Arena {self.room_id}] {player_info.name} assigned as Player {player_id}, ready={len(self.ready)}, game.running={self.game.running}")
        
        # Start game when both players are connected
        if len(self.ready) >= 2 and not self.game.running:
            logger.info(f"🎮 [Arena {self.room_id}] Both players ready, starting game...")
            await self.start_game()

    async def disconnect_player(self, player_id: int):
        was_game_running = self.game.running
        opponent_id = 3 - player_id  # 1 -> 2, 2 -> 1
        opponent_connected = opponent_id in self.connections
        
        self.connections.pop(player_id, None)
        self.ready.discard(player_id)
        
        if self.game_task:
            self.game_task.cancel()
            self.game_task = None
            logger.info(f"⏹️ [Room {self.room_id}] Game stopped (player disconnected)")
        
        # If game was running OR competition is in progress, opponent wins by forfeit
        # This handles disconnects both during gameplay and during pre-game countdown
        competition_active = competition.state == CompetitionState.IN_PROGRESS
        if (was_game_running or competition_active) and opponent_connected and not self.match_reported:
            self.match_reported = True
            self.match_complete = True
            logger.info(f"🏆 [Room {self.room_id}] {self.names.get(opponent_id, 'Opponent')} wins by forfeit!")
            # Award match to opponent
            self.wins[opponent_id] = config.points_to_win
            
            # Broadcast forfeit/match complete
            await self.broadcast({
                "type": "match_complete",
                "winner": {"player_id": opponent_id, "name": self.names.get(opponent_id, "Opponent")},
                "final_score": self.wins,
                "room_id": self.room_id,
                "points_to_win": config.points_to_win,
                "forfeit": True
            })
            
            # Report match completion to competition
            if self.room_manager:
                opponent_uid = self.player_uids.get(opponent_id)
                if opponent_uid:
                    p1_uid = self.player_uids.get(1)
                    p2_uid = self.player_uids.get(2)
                    if p1_uid and p2_uid:
                        await competition.report_match_complete(
                            self, opponent_uid,
                            p1_uid, p2_uid,
                            self.wins.get(1, 0), self.wins.get(2, 0)
                        )
        
        self._stop_bot()
        
        # Only reset room state if match is NOT complete (preserve completed match data)
        if not self.match_complete:
            self.game = Game()
            self.wins = {1: 0, 2: 0}
            self.names = {1: "Player 1", 2: "Player 2"}
        
        logger.info(f"❌ [Room {self.room_id}] Player {player_id} disconnected ({len(self.connections)} player(s))")

    def _stop_bot(self):
        """Terminate the spawned CopperBot process if running."""
        if self.bot_process:
            try:
                self.bot_process.terminate()
                self.bot_process.wait(timeout=2)
                logger.info(f"🤖 [Room {self.room_id}] CopperBot process terminated")
            except Exception as e:
                logger.warning(f"⚠️ [Room {self.room_id}] Failed to terminate CopperBot: {e}")
            self.bot_process = None

    def disconnect_observer(self, websocket: WebSocket):
        if websocket in self.observers:
            self.observers.remove(websocket)
            logger.info(f"👁️ [Room {self.room_id}] Observer disconnected ({len(self.observers)} observer(s))")

    async def handle_message(self, player_id: int, data: dict):
        action = data.get("action")
        if action == "move" and self.game.running:
            direction = data.get("direction")
            if direction in ("up", "down", "left", "right"):
                if player_id in self.game.snakes:
                    self.game.snakes[player_id].queue_direction(direction)
        elif action == "ready":
            name = data.get("name", f"Player {player_id}")
            self.names[player_id] = name
            self.ready.add(player_id)
            logger.info(f"👍 [Room {self.room_id}] {name} ready ({len(self.ready)}/2 players)")
            
            # Start game when we have 2 ready players AND competition is in progress
            # (Don't start games while waiting for players to fill the competition)
            # Also check that game_task isn't running (handles transition between games in a match)
            game_task_active = self.game_task and not self.game_task.done()
            if len(self.ready) >= 2 and not self.game.running and not game_task_active:
                if competition.state == CompetitionState.IN_PROGRESS:
                    await self.start_game()
                else:
                    # Check if all players are now ready - start competition if so
                    total_ready = sum(len(r.ready) for r in room_manager.rooms.values())
                    max_players = config.arenas * 2
                    if total_ready >= max_players:
                        # Start the competition, which will start all games
                        await _start_competition_from_rooms()
                        # Note: _start_competition_from_rooms already starts all room games
                    else:
                        # Still waiting for more players
                        for pid, ws in self.connections.items():
                            try:
                                await ws.send_json({
                                    "type": "waiting",
                                    "message": f"Waiting for competition to start ({total_ready}/{max_players} players)"
                                })
                            except Exception:
                                pass
            elif len(self.ready) < 2:
                if player_id in self.connections:
                    await self.connections[player_id].send_json({
                        "type": "waiting",
                        "message": "Waiting for Player 2..."
                    })

    def _spawn_bot(self, difficulty: int):
        """Spawn a CopperBot process to play against the human player."""
        self._stop_bot()  # Clean up any existing bot
        
        # Get the server URL
        codespace_name = os.environ.get("CODESPACE_NAME")
        github_domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
        
        if codespace_name:
            server_url = f"wss://{codespace_name}-8765.{github_domain}/ws/"
        else:
            server_url = "ws://localhost:8765/ws/"
        
        # Path to copperbot.py (same directory as main.py)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "copperbot.py")
        
        try:
            self.bot_process = subprocess.Popen(
                [sys.executable, script_path, "--server", server_url, "--difficulty", str(difficulty), "--quiet"],
                cwd=script_dir
            )
            logger.info(f"🤖 [Room {self.room_id}] CopperBot L{difficulty} spawned (PID: {self.bot_process.pid})")
        except Exception as e:
            logger.error(f"❌ [Room {self.room_id}] Failed to spawn CopperBot: {e}")

    async def start_game(self):
        # Guard against duplicate start_game calls (e.g., during game-to-game transitions)
        if self.game.running or (self.game_task and not self.game_task.done()):
            logger.warning(f"⚠️ [Room {self.room_id}] start_game called but game already running or task active, ignoring")
            return
        
        # Guard: don't start if match is already complete
        if self.match_complete:
            logger.warning(f"⚠️ [Room {self.room_id}] start_game called but match is complete, ignoring")
            return
        
        # Guard: don't start if someone already won the match
        if self._check_match_complete():
            logger.warning(f"⚠️ [Room {self.room_id}] start_game called but match winner exists (wins={self.wins}), ignoring")
            return
        
        self.game = Game(mode="two_player")
        self.game.running = True
        
        logger.info(f"🎮 [Room {self.room_id}] Game started!")
        
        await self.broadcast({"type": "start", "mode": "two_player", "room_id": self.room_id})
        self.game_task = asyncio.create_task(self.game_loop())
        
        # Notify all observers about updated room list
        if self.room_manager:
            await self.room_manager.broadcast_room_list_to_all_observers()
        
        # Check if competition should start (all rooms have 2 ready players)
        if competition.state == CompetitionState.WAITING_FOR_PLAYERS:
            total_ready = sum(len(r.ready) for r in room_manager.rooms.values())
            max_players = config.arenas * 2
            if total_ready >= max_players:
                await _start_competition_from_rooms()

    async def game_loop(self):
        try:
            while self.game.running:
                self.game.update()
                # Update food lifetimes (in ticks)
                self.game.update_food_lifetimes()
                await self.broadcast_state()
                if not self.game.running:
                    if self.game.winner:
                        self.wins[self.game.winner] += 1
                        logger.info(f"🏆 [Room {self.room_id}] Game over! Winner: {self.names.get(self.game.winner, 'Unknown')}")
                    else:
                        logger.info(f"🏁 [Room {self.room_id}] Game over! Draw.")
                    
                    # Check for match completion (first to points_to_win)
                    match_winner = self._check_match_complete()
                    logger.info(f"🔍 [Room {self.room_id}] Match check: wins={self.wins}, points_to_win={config.points_to_win}, match_winner={match_winner}")
                    
                    await self.broadcast({"type": "gameover", "winner": self.game.winner, "wins": self.wins, "names": self.names, "room_id": self.room_id, "points_to_win": config.points_to_win})
                    
                    if match_winner:
                        # Clear game_task before advancing so clear_all_rooms()
                        # won't cancel this task mid-execution
                        self.game_task = None
                        try:
                            await self._handle_match_complete(match_winner)
                        except Exception as e:
                            logger.error(f"❌ [Arena {self.room_id}] Error handling match complete: {e}")
                            import traceback
                            traceback.print_exc()
                        # Notify all observers about updated room list
                        if self.room_manager:
                            await self.room_manager.broadcast_room_list_to_all_observers()
                        return  # Exit game loop - match is done
                    else:
                        # Continue match - clear ready state before pausing
                        # so ready signals arriving during the pause are preserved
                        self.ready.clear()
                        # Pause so observers can see the result before next game
                        await asyncio.sleep(3)
                        logger.info(f"🔄 [Room {self.room_id}] No match winner yet, waiting for players to ready up...")
                        await self._wait_for_ready()
                        
                await asyncio.sleep(config.tick_rate)
        except asyncio.CancelledError:
            pass
    
    def _check_match_complete(self) -> Optional[int]:
        """Check if a player has won the match. Returns winner player_id or None."""
        for player_id, wins in self.wins.items():
            if wins >= config.points_to_win:
                return player_id
        return None
    
    async def _handle_match_complete(self, winner_player_id: int):
        """Handle match completion in competition mode."""
        if self.match_reported:
            logger.warning(f"⚠️ [Arena {self.room_id}] Match already reported, skipping duplicate")
            return
        self.match_reported = True
        self.match_complete = True  # Mark room as finished
        
        winner_uid = self.player_uids[winner_player_id]
        loser_player_id = 3 - winner_player_id
        loser_uid = self.player_uids[loser_player_id]
        
        # Get remaining matches before this one completes
        remaining_matches = competition.get_remaining_matches()
        
        # Broadcast match result
        await self.broadcast({
            "type": "match_complete",
            "winner": {"player_id": winner_player_id, "name": self.names[winner_player_id]},
            "final_score": self.wins,
            "room_id": self.room_id,
            "remaining_matches": remaining_matches - 1,  # Subtract this match
            "current_round": competition.current_round,
            "total_rounds": competition._calculate_total_rounds()
        })
        
        logger.info(f"🏆 [Arena {self.room_id}] Match complete: {self.names[winner_player_id]} wins {self.wins[winner_player_id]}-{self.wins[loser_player_id]}")
        
        # Report to competition
        await competition.report_match_complete(
            self, winner_uid, 
            self.player_uids[1], self.player_uids[2],
            self.wins[1], self.wins[2]
        )
    
    async def _wait_for_ready(self):
        """Wait for both players to signal ready, then start the next game."""
        while len(self.ready) < 2:
            # Check if match is already complete (shouldn't start another game)
            if self.match_complete:
                logger.info(f"⚠️ [Room {self.room_id}] Match already complete, not starting new game")
                return
            # Check if players are still connected
            if len(self.connections) < 2:
                logger.info(f"⚠️ [Room {self.room_id}] Player disconnected while waiting for ready")
                return
            await asyncio.sleep(0.1)
        
        # Double-check match isn't complete before starting
        if self.match_complete:
            logger.info(f"⚠️ [Room {self.room_id}] Match completed while waiting, not starting new game")
            return
            
        # Both players ready - start next game
        await self._start_next_game()
    
    async def _start_next_game(self):
        """Start the next game in the match."""
        # Guard: don't start if match is complete
        if self.match_complete:
            logger.warning(f"⚠️ [Arena {self.room_id}] _start_next_game called but match is complete, ignoring")
            return
            
        # Guard: don't start if someone already won
        if self._check_match_complete():
            logger.warning(f"⚠️ [Arena {self.room_id}] _start_next_game called but match winner exists, ignoring")
            return
        
        self.game = Game(mode="two_player")
        self.game.running = True
        
        await self.broadcast({
            "type": "start", 
            "mode": "competition",
            "room_id": self.room_id,
            "wins": self.wins,
            "points_to_win": config.points_to_win
        })
        
        logger.info(f"🎮 [Arena {self.room_id}] Next game started (Score: {self.wins[1]}-{self.wins[2]})")

    async def broadcast_state(self):
        await self.broadcast({"type": "state", "game": self.game.to_dict(), "wins": self.wins, "names": self.names, "room_id": self.room_id})

    async def broadcast(self, message: dict):
        disconnected_players = []
        disconnected_observers = []
        
        # Send to players (copy dict to avoid modification during iteration)
        for pid, ws in list(self.connections.items()):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.warning(f"⚠️ [Room {self.room_id}] Failed to send to player {pid}: {e}")
                disconnected_players.append(pid)
        
        # Send to observers
        for ws in self.observers:
            try:
                await ws.send_json(message)
            except Exception:
                disconnected_observers.append(ws)
        
        # Only disconnect players if game is not in competition mode startup
        # (give competition players a chance to reconnect)
        for pid in disconnected_players:
            if not self.match_complete:  # Don't disconnect during active match
                await self.disconnect_player(pid)
        for ws in disconnected_observers:
            self.disconnect_observer(ws)


class RoomManager:
    """Manages multiple game rooms."""
    
    MAX_ROOMS = 10
    
    def __init__(self):
        self.rooms: dict[int, GameRoom] = {}
        self._matchmaking_lock = asyncio.Lock()
        self.lobby_observers: list[WebSocket] = []  # Observers waiting for a game
    
    async def find_or_create_room(self) -> tuple[Optional[GameRoom], int]:
        """Thread-safe matchmaking: find a waiting room or create a new one."""
        async with self._matchmaking_lock:
            # First, try to find a waiting room
            for room in self.rooms.values():
                if room.is_waiting_for_player():
                    player_id = room.get_available_slot() or 2
                    return room, player_id
            
            # No waiting room, create a new one
            for room_id in range(1, self.MAX_ROOMS + 1):
                if room_id not in self.rooms or self.rooms[room_id].is_empty():
                    room = GameRoom(room_id, self)
                    self.rooms[room_id] = room
                    logger.info(f"🏠 Room {room_id} created ({len([r for r in self.rooms.values() if not r.is_empty()])} active rooms)")
                    return room, 1
            
            return None, 0
    
    def find_waiting_room(self) -> Optional[GameRoom]:
        """Find a room waiting for a second player."""
        for room in self.rooms.values():
            if room.is_waiting_for_player():
                return room
        return None
    
    def find_active_room(self) -> Optional[GameRoom]:
        """Find any room with an active game (for observers)."""
        for room in self.rooms.values():
            if room.is_active():
                return room
        return None
    
    def get_active_rooms(self) -> list[GameRoom]:
        """Get all rooms with active games."""
        return [room for room in self.rooms.values() if room.is_active()]
    
    def get_room_by_id(self, room_id: int) -> Optional[GameRoom]:
        """Get a specific room by ID."""
        return self.rooms.get(room_id)
    
    async def broadcast_room_list_to_all_observers(self):
        """Send updated room list to all observers in all rooms."""
        rooms = self.get_active_rooms()
        room_data = [
            {
                "room_id": r.room_id,
                "names": r.names,
                "wins": r.wins,
                "match_complete": r.match_complete
            }
            for r in rooms
        ]
        
        # Include round info so observers can update their display
        bye_player_name = None
        if competition.current_bye_uid and competition.current_bye_uid in competition.players:
            bye_player_name = competition.players[competition.current_bye_uid].name
        round_info = {
            "round": competition.current_round,
            "total_rounds": competition._calculate_total_rounds(),
            "bye_player": bye_player_name
        }
        
        # Notify observers in rooms
        for room in self.rooms.values():
            for ws in room.observers[:]:  # Copy list to avoid modification during iteration
                try:
                    await ws.send_json({
                        "type": "room_list",
                        "rooms": room_data,
                        "current_room": room.room_id,
                        **round_info
                    })
                except Exception:
                    pass  # Observer disconnected, will be cleaned up later
        
        # Notify lobby observers and auto-join them to first active game
        if rooms and self.lobby_observers:
            first_room = rooms[0]
            room_data = [
                {
                    "room_id": r.room_id,
                    "names": r.names,
                    "wins": r.wins,
                    "match_complete": r.match_complete
                }
                for r in rooms
            ]
            for ws in self.lobby_observers[:]:
                try:
                    # Move from lobby to room
                    first_room.observers.append(ws)
                    await ws.send_json({
                        "type": "observer_joined",
                        "room_id": first_room.room_id,
                        "game": first_room.game.to_dict(),
                        "wins": first_room.wins,
                        "names": first_room.names
                    })
                    # Also send room list immediately
                    await ws.send_json({
                        "type": "room_list",
                        "rooms": room_data,
                        "current_room": first_room.room_id,
                        **round_info
                    })
                    logger.info(f"👁️ Lobby observer joined Room {first_room.room_id}")
                except Exception:
                    pass
            self.lobby_observers.clear()
        elif not rooms:
            # Send empty room list to lobby observers
            for ws in self.lobby_observers[:]:
                try:
                    await ws.send_json({
                        "type": "room_list",
                        "rooms": [],
                        "current_room": None,
                        **round_info
                    })
                except Exception:
                    pass
    
    def create_room(self) -> Optional[GameRoom]:
        """Create a new room if slots available."""
        for room_id in range(1, self.MAX_ROOMS + 1):
            if room_id not in self.rooms or self.rooms[room_id].is_empty():
                room = GameRoom(room_id, self)
                self.rooms[room_id] = room
                logger.info(f"🏠 Room {room_id} created ({len([r for r in self.rooms.values() if not r.is_empty()])} active rooms)")
                return room
        return None
    
    def create_competition_room(self, arena_id: int, p1_uid: str, p2_uid: str) -> GameRoom:
        """Create a room for a competition match."""
        room = GameRoom(arena_id, self)
        room.player_uids = {1: p1_uid, 2: p2_uid}
        self.rooms[arena_id] = room
        logger.info(f"🏟️ Arena {arena_id} created for competition match")
        return room
    
    def spawn_bot_vs_bot(self, difficulty1: int = 5, difficulty2: int = 5):
        """Spawn two bots to play against each other for observers to watch."""
        codespace_name = os.environ.get("CODESPACE_NAME")
        github_domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
        
        if codespace_name:
            server_url = f"wss://{codespace_name}-8765.{github_domain}/ws/"
        else:
            server_url = "ws://localhost:8765/ws/"
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_path = os.path.join(script_dir, "copperbot.py")
        
        try:
            # Spawn two bots with different difficulties for variety
            bot1 = subprocess.Popen(
                [sys.executable, script_path, "--server", server_url, "--difficulty", str(difficulty1), "--quiet"],
                cwd=script_dir
            )
            bot2 = subprocess.Popen(
                [sys.executable, script_path, "--server", server_url, "--difficulty", str(difficulty2), "--quiet"],
                cwd=script_dir
            )
            logger.info(f"🤖 Spawned bot-vs-bot match: CopperBot L{difficulty1} (PID: {bot1.pid}) vs CopperBot L{difficulty2} (PID: {bot2.pid})")
            return bot1, bot2
        except Exception as e:
            logger.error(f"❌ Failed to spawn bot-vs-bot match: {e}")
            return None, None
    
    def get_room(self, room_id: int) -> Optional[GameRoom]:
        return self.rooms.get(room_id)
    
    def cleanup_empty_rooms(self):
        """Remove empty rooms."""
        empty_rooms = [rid for rid, room in self.rooms.items() if room.is_empty()]
        for rid in empty_rooms:
            del self.rooms[rid]
            logger.info(f"🧹 Room {rid} cleaned up")
    
    def clear_all_rooms(self):
        """Clear all rooms for next round. Called between competition rounds."""
        # Collect all observers before clearing rooms - they need to be moved to lobby
        all_observers = []
        for room in self.rooms.values():
            all_observers.extend(room.observers)
            room.observers.clear()
        
        # Move observers to lobby so they can be reassigned to new rooms
        self.lobby_observers.extend(all_observers)
        if all_observers:
            logger.info(f"👁️ Moved {len(all_observers)} observer(s) to lobby for next round")
        
        for room in self.rooms.values():
            # Don't stop bots here - winners need to stay connected for Round 2+
            # Losing bots are terminated when they receive match_complete
            if room.game_task:
                room.game_task.cancel()
        self.rooms.clear()
        logger.info(f"🧹 All rooms cleared for next round")
    
    def get_status(self) -> dict:
        """Get status of all rooms."""
        # Count total players across all rooms
        total_players = sum(len(room.connections) for room in self.rooms.values())
        max_players = config.arenas * 2
        
        # Only show open slots if competition is waiting for players
        competition_in_progress = competition.state != CompetitionState.WAITING_FOR_PLAYERS
        open_slots = 0 if competition_in_progress else max_players - total_players
        
        # Get active fruits (propensity > 0)
        active_fruits = [
            fruit_type for fruit_type, props in config.fruits.items()
            if props.get("propensity", 0) > 0
        ]
        
        return {
            "version": "3.5.1",
            "arenas": config.arenas,
            "max_players": max_players,
            "total_players": total_players,
            "open_slots": open_slots,
            "competition_state": competition.state.value,
            "total_rooms": len(self.rooms),
            "speed": config.tick_rate,
            "grid_width": config.grid_width,
            "grid_height": config.grid_height,
            "points_to_win": config.points_to_win,
            "bots": config.bots,
            "fruits": active_fruits,
            "rooms": [
                {
                    "room_id": room.room_id,
                    "players": list(room.connections.keys()),
                    "ready": list(room.ready),
                    "observers": len(room.observers),
                    "game_running": room.game.running,
                    "waiting_for_player": room.is_waiting_for_player(),
                    "match_complete": room.match_complete,
                    "names": room.names,
                    "wins": room.wins
                }
                for room in self.rooms.values()
            ]
        }


room_manager = RoomManager()


@app.websocket("/ws/join")
async def join_game(websocket: WebSocket):
    """Auto-matchmaking: join a competition slot."""
    await websocket.accept()
    
    # Check if competition is accepting players
    if competition.state != CompetitionState.WAITING_FOR_PLAYERS:
        await websocket.send_json({
            "type": "error",
            "message": "Competition in progress - cannot join"
        })
        await websocket.close(code=4003, reason="Competition in progress")
        return
    
    # Check if there are open slots
    total_players = sum(len(room.connections) for room in room_manager.rooms.values())
    max_players = config.arenas * 2
    if total_players >= max_players:
        await websocket.send_json({
            "type": "error", 
            "message": "All slots filled"
        })
        await websocket.close(code=4002, reason="Server full")
        return
    
    # Find or create a room for this player
    room, player_id = await room_manager.find_or_create_room()
    
    if not room:
        await websocket.close(code=4002, reason="Server full - no room available")
        return
    
    # Generate a UID for this player and register with competition
    uid = f"player_{room.room_id}_{player_id}_{id(websocket)}"
    room.player_uids[player_id] = uid
    
    await room.connect_player(player_id, websocket)
    
    # Send player their assignment
    await websocket.send_json({
        "type": "joined",
        "room_id": room.room_id,
        "player_id": player_id
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            # Get current room from player's competition info (may change between rounds)
            player_info = competition.players.get(uid)
            current_room = player_info.current_room if player_info else room
            if current_room:
                # Use the player's current player_id (may change between rounds)
                current_player_id = player_info.current_player_id if player_info else player_id
                await current_room.handle_message(current_player_id, data)
    except WebSocketDisconnect:
        # Get current room for disconnect handling
        player_info = competition.players.get(uid)
        current_room = player_info.current_room if player_info else room
        if current_room:
            current_player_id = player_info.current_player_id if player_info else player_id
            await current_room.disconnect_player(current_player_id)
        # Also notify competition of disconnect (handles Bye player forfeits)
        await competition.unregister_player(uid)
        room_manager.cleanup_empty_rooms()


async def _start_competition_from_rooms():
    """Start the competition using players already in rooms."""
    competition.state = CompetitionState.IN_PROGRESS
    competition.current_round = 1
    
    # Build pairings from rooms
    pairings = []
    for room in room_manager.rooms.values():
        if len(room.connections) == 2:
            p1_uid = room.player_uids.get(1)
            p2_uid = room.player_uids.get(2)
            if p1_uid and p2_uid:
                pairings.append((p1_uid, p2_uid))
                # Reset room scores for fresh competition start
                room.wins = {1: 0, 2: 0}
                room.match_complete = False
                room.match_reported = False
                # Register players with competition - include their websockets
                p1_ws = room.connections.get(1)
                p2_ws = room.connections.get(2)
                competition.players[p1_uid] = PlayerInfo(p1_uid, room.names.get(1, "Player 1"), p1_ws)
                competition.players[p2_uid] = PlayerInfo(p2_uid, room.names.get(2, "Player 2"), p2_ws)
                # Track which room each player is in
                competition.players[p1_uid].current_room = room
                competition.players[p1_uid].current_player_id = 1
                competition.players[p2_uid].current_room = room
                competition.players[p2_uid].current_player_id = 2
    
    competition.rounds.append(pairings)
    competition.match_results.append([])
    
    logger.info(f"🏆 Competition started! Round 1 with {len(pairings)} matches")
    
    # Start games in all rooms that have 2 ready players
    for room in room_manager.rooms.values():
        if len(room.ready) >= 2 and not room.game.running:
            await room.start_game()


@app.websocket("/ws/observe")
async def observe_game(websocket: WebSocket):
    """Observe an active game. Supports switching rooms via messages."""
    await websocket.accept()
    
    # Find any room with players (active or completed)
    room = room_manager.find_active_room()
    if not room:
        # Try to find any non-empty room (completed games)
        for r in room_manager.rooms.values():
            if not r.is_empty():
                room = r
                break
    
    current_room = room
    
    if not room:
        # No games at all - inform observer and close
        await websocket.send_json({
            "type": "observer_lobby",
            "message": "No active games to observe."
        })
        logger.info(f"👁️ Observer joined but no games available")
        await websocket.close(code=4003, reason="No games to observe")
        return
    
    room.observers.append(websocket)
    await websocket.send_json({
        "type": "observer_joined",
        "room_id": room.room_id,
        "game": room.game.to_dict(),
        "wins": room.wins,
        "names": room.names
    })
    logger.info(f"👁️ [Room {room.room_id}] Observer connected ({len(room.observers)} observer(s))")
    
    try:
        while True:
            # Handle observer commands (room switching)
            message = await websocket.receive_text()
            try:
                data = json.loads(message)
                action = data.get("action")
                
                if action == "switch_room" and current_room:
                    target_room_id = data.get("room_id")
                    target_room = room_manager.get_room_by_id(target_room_id)
                    
                    if target_room and not target_room.is_empty():
                        # Disconnect from current room
                        current_room.disconnect_observer(websocket)
                        # Connect to new room
                        current_room = target_room
                        current_room.observers.append(websocket)
                        await websocket.send_json({
                            "type": "observer_joined",
                            "room_id": current_room.room_id,
                            "game": current_room.game.to_dict(),
                            "wins": current_room.wins,
                            "names": current_room.names
                        })
                        logger.info(f"👁️ Observer switched to Room {target_room_id}")
                    else:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Room {target_room_id} not available"
                        })
                
                elif action == "get_rooms":
                    # Send list of all rooms (active or with players)
                    rooms = [r for r in room_manager.rooms.values() if not r.is_empty()]
                    await websocket.send_json({
                        "type": "room_list",
                        "rooms": [
                            {
                                "room_id": r.room_id,
                                "names": r.names,
                                "wins": r.wins
                            }
                            for r in rooms
                        ],
                        "current_room": current_room.room_id if current_room else None,
                        "round": competition.current_round,
                        "total_rounds": competition._calculate_total_rounds()
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if current_room:
            current_room.disconnect_observer(websocket)


@app.websocket("/ws/compete")
async def compete(websocket: WebSocket):
    """Join a competition. Waits in lobby until enough players, then starts tournament."""
    await websocket.accept()
    
    # Get player name from first message
    try:
        data = await websocket.receive_json()
        name = data.get("name", "Anonymous")
    except Exception:
        await websocket.close(code=4001, reason="Expected name message")
        return
    
    # Register for competition
    player = await competition.register_player(name, websocket)
    
    if not player:
        await websocket.send_json({
            "type": "error",
            "message": "Competition not accepting players (in progress or full)"
        })
        await websocket.close(code=4003, reason="Competition not available")
        return
    
    # Send confirmation
    await websocket.send_json({
        "type": "registered",
        "uid": player.uid,
        "name": player.name,
        "competition_status": competition.get_status()
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            
            # Handle move commands during games
            if action == "move" and player.current_room:
                direction = data.get("direction")
                if direction in ("up", "down", "left", "right"):
                    player_id = player.current_player_id
                    if player_id and player_id in player.current_room.game.snakes:
                        player.current_room.game.snakes[player_id].queue_direction(direction)
            
            # Handle ready for next game
            elif action == "ready" and player.current_room:
                player.current_room.ready.add(player.current_player_id)
                if len(player.current_room.ready) >= 2 and not player.current_room.game.running:
                    await player.current_room.start_game()
                    
    except WebSocketDisconnect:
        await competition.unregister_player(player.uid)


# Legacy endpoint for backward compatibility
@app.websocket("/ws/{player_id}")
async def websocket_endpoint(websocket: WebSocket, player_id: int):
    """Legacy endpoint - redirects to join."""
    await websocket.accept()
    
    if player_id not in (1, 2):
        await websocket.close(code=4000, reason="Invalid player_id. Use /ws/join instead.")
        return
    
    # Find or create a room
    room = None
    if player_id == 2:
        room = room_manager.find_waiting_room()
    
    if not room:
        room = room_manager.create_room()
        if not room:
            await websocket.close(code=4002, reason="Server full")
            return
        player_id = 1  # Override to player 1 for new room
    else:
        player_id = room.get_available_slot() or 2
    
    await room.connect_player(player_id, websocket)
    await websocket.send_json({
        "type": "joined",
        "room_id": room.room_id,
        "player_id": player_id
    })
    
    try:
        while True:
            data = await websocket.receive_json()
            await room.handle_message(player_id, data)
    except WebSocketDisconnect:
        await room.disconnect_player(player_id)
        room_manager.cleanup_empty_rooms()


@app.get("/")
async def root():
    return {"name": "CopperHead Server", "status": "running"}


@app.get("/status")
async def status():
    return room_manager.get_status()


@app.get("/rooms/active")
async def active_rooms():
    """Get list of active rooms for observers."""
    rooms = room_manager.get_active_rooms()
    return {
        "rooms": [
            {
                "room_id": room.room_id,
                "names": room.names,
                "wins": room.wins
            }
            for room in rooms
        ]
    }


@app.get("/competition")
async def competition_status():
    """Get current competition status."""
    return competition.get_status()


@app.get("/history")
async def championship_history():
    """Get history of completed championships."""
    return {"championships": Competition.championship_history}


@app.post("/add_bot")
async def add_bot(difficulty: int = None):
    """Add a CopperBot to the first available room."""
    # Find a room waiting for a player
    room = room_manager.find_waiting_room()
    if not room:
        # No waiting room - check if we can create one
        total_players = sum(len(r.connections) for r in room_manager.rooms.values())
        if total_players >= config.arenas * 2:
            return {"success": False, "message": "All player slots filled"}
        # Create a new room for the bot
        room = room_manager.create_room()
        if not room:
            return {"success": False, "message": "Cannot create room"}
    
    # Use provided difficulty or random
    if difficulty is None or difficulty < 1 or difficulty > 10:
        difficulty = random.randint(1, 10)
    room._spawn_bot(difficulty)
    
    return {"success": True, "message": f"CopperBot L{difficulty} added to Room {room.room_id}"}


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CopperHead Server - 2-player Snake game with competition mode",
        usage="python main.py [options] [spec-file]"
    )
    parser.add_argument(
        "spec_file", nargs="?", default=None,
        help="Optional JSON config file. Defaults to server-settings.json if it exists."
    )
    parser.add_argument(
        "--arenas", type=int, default=None,
        help="Number of matches in round 1 (players needed = 2 * arenas). Default: 1"
    )
    parser.add_argument(
        "--points-to-win", type=int, default=None,
        help="Points required to win a match. Default: 5"
    )
    parser.add_argument(
        "--reset-delay", type=int, default=None,
        help="Seconds to wait before resetting after competition ends. Default: 10"
    )
    parser.add_argument(
        "--grid-size", type=str, default=None,
        help="Grid size as WIDTHxHEIGHT. Default: 30x20"
    )
    parser.add_argument(
        "--speed", type=float, default=None,
        help="Tick rate in seconds per frame. Default: 0.15"
    )
    parser.add_argument(
        "--bots", type=int, default=None,
        help="Number of AI bots to launch at server start. Default: 0"
    )
    parser.add_argument(
        "--host", type=str, default="0.0.0.0",
        help="Host to bind to. Default: 0.0.0.0"
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="Port to bind to. Default: 8765"
    )
    return parser.parse_args()


def load_spec_file(spec_file: str) -> dict:
    """Load configuration from a JSON spec file."""
    try:
        with open(spec_file, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {spec_file}: {e}")
        return {}


def validate_spec(spec: dict) -> bool:
    """Validate that a spec dictionary has valid values. Returns True if valid."""
    if not spec:
        return False
    
    # Check numeric values are positive where required
    if "arenas" in spec and (not isinstance(spec["arenas"], int) or spec["arenas"] < 1):
        logger.error("Invalid config: 'arenas' must be a positive integer")
        return False
    if "points_to_win" in spec and (not isinstance(spec["points_to_win"], int) or spec["points_to_win"] < 1):
        logger.error("Invalid config: 'points_to_win' must be a positive integer")
        return False
    if "reset_delay" in spec and (not isinstance(spec["reset_delay"], int) or spec["reset_delay"] < 0):
        logger.error("Invalid config: 'reset_delay' must be a non-negative integer")
        return False
    if "speed" in spec and (not isinstance(spec["speed"], (int, float)) or spec["speed"] <= 0):
        logger.error("Invalid config: 'speed' must be a positive number")
        return False
    if "bots" in spec and (not isinstance(spec["bots"], int) or spec["bots"] < 0):
        logger.error("Invalid config: 'bots' must be a non-negative integer")
        return False
    
    # Validate grid_size format if present
    if "grid_size" in spec:
        try:
            width, height = spec["grid_size"].lower().split("x")
            if int(width) < 5 or int(height) < 5:
                logger.error("Invalid config: grid dimensions must be at least 5x5")
                return False
        except (ValueError, AttributeError):
            logger.error("Invalid config: 'grid_size' must be in format 'WIDTHxHEIGHT'")
            return False
    
    return True


def apply_spec_to_config(spec: dict):
    """Apply a validated spec dictionary to the global config object."""
    if "arenas" in spec:
        config.arenas = spec["arenas"]
    if "points_to_win" in spec:
        config.points_to_win = spec["points_to_win"]
    if "reset_delay" in spec:
        config.reset_delay = spec["reset_delay"]
    if "speed" in spec:
        config.tick_rate = spec["speed"]
    if "bots" in spec:
        config.bots = spec["bots"]
    
    # Parse grid size
    if "grid_size" in spec:
        width, height = spec["grid_size"].lower().split("x")
        config.grid_width = int(width)
        config.grid_height = int(height)
    
    # Fruit settings
    if "fruit_warning" in spec:
        config.fruit_warning = spec["fruit_warning"]
    if "max_fruits" in spec:
        config.max_fruits = spec["max_fruits"]
    if "fruit_interval" in spec:
        config.fruit_interval = spec["fruit_interval"]
    
    # Load fruit properties from spec
    if "fruits" in spec:
        for fruit_type, props in spec["fruits"].items():
            if fruit_type in config.fruits:
                config.fruits[fruit_type]["propensity"] = props.get("propensity", 0)
                config.fruits[fruit_type]["lifetime"] = props.get("lifetime", 0)


# Global variable to track config file modification time
_config_file_mtime: float = 0.0
_config_file_path: str = ""


async def watch_config_file():
    """Background task that watches for config file changes and restarts competition."""
    global _config_file_mtime
    
    if not _config_file_path:
        return
    
    while True:
        await asyncio.sleep(2)  # Check every 2 seconds
        
        try:
            current_mtime = os.path.getmtime(_config_file_path)
            
            if current_mtime > _config_file_mtime:
                _config_file_mtime = current_mtime
                logger.info(f"🔄 Config file changed, attempting to reload...")
                
                # Try to load and validate the new config
                spec = load_spec_file(_config_file_path)
                if not spec:
                    logger.warning("⚠️ Config file is empty or invalid JSON, keeping current settings")
                    continue
                
                if not validate_spec(spec):
                    logger.warning("⚠️ Config file has invalid values, keeping current settings")
                    continue
                
                # Apply new config
                apply_spec_to_config(spec)
                logger.info(f"✅ Config reloaded: {config.arenas} arenas, {config.points_to_win} points to win, {config.grid_width}x{config.grid_height} grid")
                
                # Restart the competition with new settings
                await competition.start_waiting()
                logger.info("🔄 Competition restarted with new settings")
                
        except FileNotFoundError:
            pass  # File deleted, ignore
        except Exception as e:
            logger.error(f"Error watching config file: {e}")


def apply_config(args):
    """Apply parsed arguments to server config."""
    global _config_file_path, _config_file_mtime
    
    # Load spec file (explicit arg, or default server-settings.json)
    spec = {}
    if args.spec_file:
        spec = load_spec_file(args.spec_file)
        if spec:
            logger.info(f"📄 Loaded config from {args.spec_file}")
            _config_file_path = args.spec_file
    else:
        default_spec = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server-settings.json")
        if os.path.exists(default_spec):
            spec = load_spec_file(default_spec)
            if spec:
                logger.info(f"📄 Loaded config from server-settings.json")
                _config_file_path = default_spec
    
    # Set initial modification time so we don't trigger on startup
    if _config_file_path and os.path.exists(_config_file_path):
        _config_file_mtime = os.path.getmtime(_config_file_path)
    
    # Apply settings: CLI args override spec file, spec file overrides defaults
    config.arenas = args.arenas if args.arenas is not None else spec.get("arenas", 1)
    config.points_to_win = args.points_to_win if args.points_to_win is not None else spec.get("points_to_win", 5)
    config.reset_delay = args.reset_delay if args.reset_delay is not None else spec.get("reset_delay", 10)
    config.tick_rate = args.speed if args.speed is not None else spec.get("speed", 0.15)
    config.bots = args.bots if args.bots is not None else spec.get("bots", 0)
    
    # Parse grid size
    grid_size = args.grid_size if args.grid_size is not None else spec.get("grid_size", "30x20")
    try:
        width, height = grid_size.lower().split("x")
        config.grid_width = int(width)
        config.grid_height = int(height)
    except ValueError:
        logger.error(f"Invalid grid size '{grid_size}'. Using default 30x20.")
        config.grid_width = 30
        config.grid_height = 20
    
    # Fruit settings
    config.fruit_warning = spec.get("fruit_warning", 20)
    config.max_fruits = spec.get("max_fruits", 1)
    config.fruit_interval = spec.get("fruit_interval", 40)
    
    # Load fruit properties from spec
    if "fruits" in spec:
        for fruit_type, props in spec["fruits"].items():
            if fruit_type in config.fruits:
                config.fruits[fruit_type]["propensity"] = props.get("propensity", 0)
                config.fruits[fruit_type]["lifetime"] = props.get("lifetime", 0)


def spawn_initial_bots(count: int):
    """Spawn initial bots at server start."""
    if count <= 0:
        return
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "copperbot.py")
    
    codespace_name = os.environ.get("CODESPACE_NAME")
    github_domain = os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev")
    
    if codespace_name:
        server_url = f"wss://{codespace_name}-8765.{github_domain}/ws/"
    else:
        server_url = "ws://localhost:8765/ws/"
    
    for i in range(count):
        difficulty = random.randint(1, 10)
        try:
            subprocess.Popen(
                [sys.executable, script_path, "--server", server_url, "--difficulty", str(difficulty), "--quiet"],
                cwd=script_dir
            )
            logger.info(f"🤖 Spawned CopperBot L{difficulty} ({i+1}/{count})")
        except Exception as e:
            logger.error(f"❌ Failed to spawn bot: {e}")


if __name__ == "__main__":
    import uvicorn
    args = parse_args()
    apply_config(args)
    
    logger.info(f"🎮 Starting CopperHead Server")
    logger.info(f"   Arenas: {config.arenas} (need {config.arenas * 2} players)")
    logger.info(f"   Points to win: {config.points_to_win}")
    logger.info(f"   Grid: {config.grid_width}x{config.grid_height}")
    logger.info(f"   Speed: {config.tick_rate}s/tick")
    logger.info(f"   Bots: {config.bots}")
    
    # Note: Bots are spawned by start_waiting() during server startup
    
    uvicorn.run(app, host=args.host, port=args.port)
