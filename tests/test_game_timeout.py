#!/usr/bin/env python3
"""
Unit tests for in-game game-timeout stalemate behavior.

Usage:
    python tests/test_game_timeout.py
"""

import os
import sys
import unittest


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import main


class GameTimeoutStalemateTests(unittest.TestCase):
    def setUp(self):
        self.original_game_timeout = main.config.game_timeout
        self.original_tick_rate = main.config.tick_rate

    def tearDown(self):
        main.config.game_timeout = self.original_game_timeout
        main.config.tick_rate = self.original_tick_rate

    def _create_running_game(self, snake1_body, snake2_body):
        game = main.Game()
        game.running = True
        game.snakes[1].body = list(snake1_body)
        game.snakes[2].body = list(snake2_body)
        return game

    def test_stalemate_awards_game_to_longer_snake(self):
        main.config.game_timeout = 30
        main.config.tick_rate = 1.0
        game = self._create_running_game(
            [(5, 8), (4, 8), (3, 8), (2, 8)],
            [(14, 9), (15, 9)],
        )
        game.ticks_since_last_collection = 29  # becomes 30 after update(), triggering stalemate

        game.update()

        self.assertFalse(game.running)
        self.assertEqual(game.end_reason, "stalemate")
        self.assertEqual(game.winner, 1)

    def test_stalemate_ends_equal_lengths_as_draw(self):
        main.config.game_timeout = 30
        main.config.tick_rate = 1.0
        game = self._create_running_game(
            [(5, 8), (4, 8), (3, 8)],
            [(14, 9), (15, 9), (16, 9)],
        )
        game.ticks_since_last_collection = 29  # becomes 30 after update(), triggering stalemate

        game.update()

        self.assertFalse(game.running)
        self.assertEqual(game.end_reason, "stalemate")
        self.assertIsNone(game.winner)

    def test_collecting_fruit_resets_stalemate_timer(self):
        main.config.game_timeout = 30
        main.config.tick_rate = 1.0
        game = self._create_running_game(
            [(5, 8), (4, 8), (3, 8)],
            [(14, 9), (15, 9), (16, 9)],
        )
        game.ticks_since_last_collection = 29  # would trigger stalemate without fruit collection
        game.foods = [{"x": 6, "y": 8, "type": "apple", "lifetime": None}]

        game.update()

        self.assertTrue(game.running)
        self.assertIsNone(game.end_reason)
        self.assertIsNone(game.winner)
        self.assertEqual(len(game.snakes[1].body), 4)


if __name__ == "__main__":
    unittest.main()
