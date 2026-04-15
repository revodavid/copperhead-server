#!/usr/bin/env python3
"""
Unit tests for the three draws rule in match scoring.
"""

import os
import sys
import unittest
from unittest.mock import patch


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import main


class ThreeDrawRuleTests(unittest.TestCase):
    def setUp(self):
        self.room = main.GameRoom(1)

    def test_first_two_draws_remain_draws(self):
        self.room.game.winner = None

        first_award = self.room._apply_completed_game_result()
        self.room.game.winner = None
        second_award = self.room._apply_completed_game_result()

        self.assertFalse(first_award)
        self.assertFalse(second_award)
        self.assertIsNone(self.room.game.winner)
        self.assertEqual(self.room.consecutive_draws, 2)
        self.assertEqual(self.room.wins, {1: 0, 2: 0})

    @patch("main.random.choice", return_value=2)
    def test_third_consecutive_draw_is_awarded_randomly(self, mock_choice):
        self.room.consecutive_draws = 2
        self.room.game.winner = None

        draw_awarded = self.room._apply_completed_game_result()

        self.assertTrue(draw_awarded)
        self.assertEqual(self.room.game.winner, 2)
        self.assertEqual(self.room.consecutive_draws, 0)
        self.assertEqual(self.room.wins, {1: 0, 2: 1})
        mock_choice.assert_called_once_with([1, 2])

    @patch("main.random.choice", return_value=1)
    def test_third_stalemate_draw_is_awarded_randomly(self, mock_choice):
        self.room.consecutive_draws = 2
        self.room.game.winner = None
        self.room.game.end_reason = "stalemate"

        draw_awarded = self.room._apply_completed_game_result()

        self.assertTrue(draw_awarded)
        self.assertEqual(self.room.game.winner, 1)
        self.assertEqual(self.room.game.end_reason, "stalemate")
        self.assertEqual(self.room.wins, {1: 1, 2: 0})
        mock_choice.assert_called_once_with([1, 2])

    def test_win_resets_draw_streak(self):
        self.room.consecutive_draws = 2
        self.room.game.winner = 1

        draw_awarded = self.room._apply_completed_game_result()

        self.assertFalse(draw_awarded)
        self.assertEqual(self.room.consecutive_draws, 0)
        self.assertEqual(self.room.wins, {1: 1, 2: 0})


if __name__ == "__main__":
    unittest.main()
