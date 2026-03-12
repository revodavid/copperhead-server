#!/usr/bin/env python3
"""
Unit tests for the sleepy snake bot.

Usage:
    python tests/test_sleepy_snake.py
"""

import importlib.util
import os
import sys
import unittest
from unittest.mock import patch


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT_PATH = os.path.join(SERVER_DIR, "bot-library", "sleepy_snake.py")

if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

module_spec = importlib.util.spec_from_file_location("sleepy_snake", BOT_PATH)
sleepy_snake = importlib.util.module_from_spec(module_spec)
assert module_spec.loader is not None
module_spec.loader.exec_module(sleepy_snake)


def choose_highest_weight(options, weights, k):
    best_index = max(range(len(weights)), key=lambda index: weights[index])
    return [options[best_index]]


class SleepySnakeTests(unittest.TestCase):
    def create_bot(self, difficulty: int) -> sleepy_snake.SleepySnake:
        bot = sleepy_snake.SleepySnake("ws://localhost:8765/ws/", difficulty=difficulty, quiet=True)
        bot.player_id = 1
        bot.grid_width = 20
        bot.grid_height = 16
        return bot

    def set_game_state(self, bot: sleepy_snake.SleepySnake):
        bot.game_state = {
            "grid": {"width": 20, "height": 16},
            "running": True,
            "foods": [{"x": 6, "y": 5, "type": "apple"}],
            "snakes": {
                "1": {"body": [[5, 5], [4, 5], [3, 5]], "direction": "up", "alive": True},
                "2": {"body": [[15, 10], [16, 10], [17, 10]], "direction": "left", "alive": True},
            },
        }

    def test_difficulty_one_avoids_adjacent_food(self):
        bot = self.create_bot(1)
        self.set_game_state(bot)

        with patch.object(sleepy_snake.random, "uniform", return_value=0.0), patch.object(
            sleepy_snake.random,
            "choices",
            side_effect=choose_highest_weight,
        ), patch.object(sleepy_snake.random, "randint", return_value=5):
            move = bot.calculate_move()

        self.assertNotEqual(move, "right")

    def test_higher_difficulty_is_weighted_toward_food(self):
        bot = self.create_bot(10)
        self.set_game_state(bot)

        with patch.object(sleepy_snake.random, "uniform", return_value=0.0), patch.object(
            sleepy_snake.random,
            "choices",
            side_effect=choose_highest_weight,
        ), patch.object(sleepy_snake.random, "randint", return_value=5):
            move = bot.calculate_move()

        self.assertEqual(move, "right")

    def test_keeps_wandering_direction_until_turn_time_expires(self):
        bot = self.create_bot(5)
        self.set_game_state(bot)
        bot.wander_direction = "up"
        bot.ticks_until_turn = 3

        move = bot.calculate_move()

        self.assertEqual(move, "up")
        self.assertEqual(bot.ticks_until_turn, 2)

    def test_changes_direction_early_to_avoid_wall(self):
        bot = self.create_bot(5)
        self.set_game_state(bot)
        bot.game_state["snakes"]["1"]["body"] = [[0, 5], [1, 5], [2, 5]]
        bot.game_state["snakes"]["1"]["direction"] = "left"
        bot.wander_direction = "left"
        bot.ticks_until_turn = 4

        with patch.object(sleepy_snake.random, "uniform", return_value=0.0), patch.object(
            sleepy_snake.random,
            "choices",
            side_effect=choose_highest_weight,
        ), patch.object(sleepy_snake.random, "randint", return_value=5):
            move = bot.calculate_move()

        self.assertNotEqual(move, "left")
        self.assertEqual(bot.ticks_until_turn, 4)

    def test_difficulty_one_changes_direction_early_to_avoid_food(self):
        bot = self.create_bot(1)
        self.set_game_state(bot)
        bot.wander_direction = "right"
        bot.ticks_until_turn = 4

        with patch.object(sleepy_snake.random, "uniform", return_value=0.0), patch.object(
            sleepy_snake.random,
            "choices",
            side_effect=choose_highest_weight,
        ), patch.object(sleepy_snake.random, "randint", return_value=5):
            move = bot.calculate_move()

        self.assertNotEqual(move, "right")
        self.assertEqual(bot.ticks_until_turn, 4)


if __name__ == "__main__":
    unittest.main()
