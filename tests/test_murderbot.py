#!/usr/bin/env python3
"""
Unit tests for the MurderBot strategy threshold.
"""

import importlib.util
import os
import sys
import unittest
from unittest.mock import patch


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOT_PATH = os.path.join(SERVER_DIR, "bot-library", "murderbot.py")

if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

module_spec = importlib.util.spec_from_file_location("murderbot", BOT_PATH)
murderbot = importlib.util.module_from_spec(module_spec)
assert module_spec.loader is not None
module_spec.loader.exec_module(murderbot)


class MurderBotTests(unittest.TestCase):
    def create_bot(
        self,
        body_length: int,
        *,
        foods=None,
        my_head=(5, 5),
        my_direction="up",
        opponent_body=None,
        opponent_direction="left",
    ) -> murderbot.RobotPlayer:
        bot = murderbot.RobotPlayer("ws://localhost:8765/ws/", difficulty=10, quiet=True)
        bot.player_id = 1
        bot.grid_width = 20
        bot.grid_height = 16

        my_body = [[my_head[0], my_head[1]]]
        for index in range(1, body_length):
            my_body.append([my_head[0], my_head[1] + index])

        if opponent_body is None:
            opponent_body = [[7, 5], [8, 5]]

        bot.game_state = {
            "grid": {"width": 20, "height": 16},
            "running": True,
            "foods": foods if foods is not None else [{"x": 4, "y": 5, "type": "apple"}],
            "snakes": {
                "1": {"body": my_body, "direction": my_direction, "alive": True},
                "2": {"body": opponent_body, "direction": opponent_direction, "alive": True},
            },
        }
        return bot

    @patch("random.random", return_value=1.0)
    def test_prioritizes_food_before_length_five(self, _mock_random):
        bot = self.create_bot(body_length=4)

        move = bot.calculate_move()

        self.assertEqual(move, "left")

    @patch("random.random", return_value=1.0)
    def test_switches_back_to_aggression_at_length_five(self, _mock_random):
        bot = self.create_bot(body_length=5)

        move = bot.calculate_move()

        self.assertEqual(move, "right")

    @patch("random.random", return_value=1.0)
    def test_targets_tile_in_front_of_opponent_head(self, _mock_random):
        bot = self.create_bot(
            body_length=5,
            foods=[],
            my_head=(2, 2),
            my_direction="up",
            opponent_body=[[2, 7], [3, 7], [4, 7]],
            opponent_direction="left",
        )

        move = bot.calculate_move()

        self.assertEqual(move, "left")


if __name__ == "__main__":
    unittest.main()
