#!/usr/bin/env python3
"""
Unit tests for the Snake class.

These tests focus on the server's core snake movement rules so beginner
developers can change the game logic with confidence.

Usage:
    python tests/test_snake.py
"""

import os
import sys
import unittest


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

from main import Snake


class SnakeTests(unittest.TestCase):
    def test_move_without_growing_keeps_length(self):
        snake = Snake(1, (5, 5), "right")
        snake.body = [(5, 5), (4, 5), (3, 5)]

        snake.move()

        self.assertEqual(snake.body, [(6, 5), (5, 5), (4, 5)])

    def test_move_with_growing_keeps_tail(self):
        snake = Snake(1, (5, 5), "right")
        snake.body = [(5, 5), (4, 5), (3, 5)]

        snake.move(grow=True)

        self.assertEqual(snake.body, [(6, 5), (5, 5), (4, 5), (3, 5)])

    def test_queue_direction_rejects_reverse_turn(self):
        snake = Snake(1, (5, 5), "right")

        snake.queue_direction("left")

        self.assertEqual(snake.input_queue, [])
        self.assertEqual(snake.get_next_head(), (6, 5))

    def test_get_next_head_uses_first_valid_queued_turn_without_consuming_it(self):
        snake = Snake(1, (5, 5), "right")
        snake.queue_direction("up")

        self.assertEqual(snake.get_next_head(), (5, 4))
        self.assertEqual(snake.input_queue, ["up"])

    def test_process_input_marks_recent_direction_change(self):
        snake = Snake(1, (5, 5), "right")
        snake.queue_direction("up")

        snake.process_input()

        self.assertEqual(snake.next_direction, "up")
        self.assertTrue(snake.changed_direction_last_move)

    def test_queue_direction_limits_buffer_to_three_inputs(self):
        snake = Snake(1, (5, 5), "up")

        snake.queue_direction("left")
        snake.queue_direction("down")
        snake.queue_direction("left")
        snake.queue_direction("down")

        self.assertEqual(snake.input_queue, ["down", "left", "down"])


if __name__ == "__main__":
    unittest.main()
