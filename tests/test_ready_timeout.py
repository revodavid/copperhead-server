#!/usr/bin/env python3
"""
Unit tests for ready timeout behavior in competition matches.

Usage:
    python tests/test_ready_timeout.py
"""

import asyncio
import os
import sys
import unittest
from unittest.mock import AsyncMock


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import main


class ReadyTimeoutTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_game_timeout = main.config.game_timeout

    async def asyncTearDown(self):
        main.config.game_timeout = self.original_game_timeout

    async def test_ready_timeout_disconnects_idle_player(self):
        main.config.game_timeout = 0
        room = main.GameRoom(1)
        ready_player_ws = AsyncMock()
        idle_player_ws = AsyncMock()

        room.connections = {1: ready_player_ws, 2: idle_player_ws}
        room.ready = {1}
        room.names = {1: "Ready Player", 2: "Idle Player"}
        room.disconnect_player = AsyncMock()

        room._start_ready_timeout()
        await asyncio.sleep(0)
        await asyncio.sleep(0)

        room.disconnect_player.assert_awaited_once_with(2)
        idle_player_ws.send_json.assert_awaited_once()
        idle_player_ws.close.assert_awaited_once()
        ready_player_ws.send_json.assert_not_awaited()
        ready_player_ws.close.assert_not_awaited()
        self.assertIsNone(room.ready_timeout_task)

    async def test_ready_timeout_is_not_started_when_everyone_is_ready(self):
        main.config.game_timeout = 0
        room = main.GameRoom(1)
        player_one_ws = AsyncMock()
        player_two_ws = AsyncMock()

        room.connections = {1: player_one_ws, 2: player_two_ws}
        room.ready = {1, 2}
        room.disconnect_player = AsyncMock()

        room._start_ready_timeout()
        await asyncio.sleep(0)

        room.disconnect_player.assert_not_awaited()
        player_one_ws.send_json.assert_not_awaited()
        player_two_ws.send_json.assert_not_awaited()
        self.assertIsNone(room.ready_timeout_task)

    async def test_cancel_ready_timeout_does_not_cancel_current_task(self):
        room = main.GameRoom(1)
        room.ready_timeout_task = asyncio.current_task()

        room._cancel_ready_timeout()
        await asyncio.sleep(0)

        self.assertIsNone(room.ready_timeout_task)


class GameTimeoutConfigTests(unittest.TestCase):
    def setUp(self):
        self.original_game_timeout = main.config.game_timeout

    def tearDown(self):
        main.config.game_timeout = self.original_game_timeout

    def test_apply_spec_uses_game_timeout_name(self):
        main.apply_spec_to_config({"game-timeout": 12})

        self.assertEqual(main.config.game_timeout, 12)

    def test_validate_spec_accepts_legacy_kick_time_names(self):
        legacy_hyphen_spec = {
            "arenas": 1,
            "points_to_win": 1,
            "reset_delay": 0,
            "kick-time": 30,
            "grid_size": "5x5",
            "speed": 0.1,
            "bots": 0,
        }
        legacy_snake_case_spec = {
            "arenas": 1,
            "points_to_win": 1,
            "reset_delay": 0,
            "kick_time": 30,
            "grid_size": "5x5",
            "speed": 0.1,
            "bots": 0,
        }

        self.assertTrue(main.validate_spec(legacy_hyphen_spec))
        self.assertTrue(main.validate_spec(legacy_snake_case_spec))


if __name__ == "__main__":
    unittest.main()
