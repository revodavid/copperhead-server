#!/usr/bin/env python3
"""
Unit tests for clearing paused tournament state between competition runs.
"""

import os
import sys
import unittest
from unittest.mock import AsyncMock, patch


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import main


class CompetitionPauseResetTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_auto_start = main.config.auto_start
        self.original_tournament_countdown = main.config.tournament_countdown
        self.original_bots = main.config.bots

        main.config.auto_start = "always"
        main.config.tournament_countdown = 0
        main.config.bots = 0

    async def asyncTearDown(self):
        main.config.auto_start = self.original_auto_start
        main.config.tournament_countdown = self.original_tournament_countdown
        main.config.bots = self.original_bots

    async def test_cancelled_paused_tournament_starts_new_competition_unpaused(self):
        competition = main.Competition()
        competition.state = main.CompetitionState.IN_PROGRESS
        competition.players = {
            "P1": main.PlayerInfo("P1", "Player 1", None),
            "P2": main.PlayerInfo("P2", "Player 2", None),
        }

        with patch.object(main.room_manager, "clear_all_rooms"), \
             patch.object(competition, "_broadcast_competition_status", AsyncMock()), \
             patch.object(competition, "_create_round_matches", AsyncMock()):
            paused_ok, _ = await competition.pause()
            self.assertTrue(paused_ok)
            self.assertFalse(competition._pause_event.is_set())

            cancelled_ok, _ = await competition.cancel()
            self.assertTrue(cancelled_ok)
            self.assertEqual(competition.state, main.CompetitionState.WAITING_FOR_PLAYERS)
            self.assertTrue(competition._pause_event.is_set())

            competition.players = {
                "P1": main.PlayerInfo("P1", "Player 1", None),
                "P2": main.PlayerInfo("P2", "Player 2", None),
            }
            await competition._start_competition()

        self.assertEqual(competition.state, main.CompetitionState.IN_PROGRESS)
        self.assertTrue(competition._pause_event.is_set())

    async def test_start_waiting_clears_leftover_pause_state(self):
        competition = main.Competition()
        competition._pause_event.clear()

        with patch.object(main.room_manager, "clear_all_rooms"):
            await competition.start_waiting()

        self.assertEqual(competition.state, main.CompetitionState.WAITING_FOR_PLAYERS)
        self.assertTrue(competition._pause_event.is_set())


if __name__ == "__main__":
    unittest.main()
