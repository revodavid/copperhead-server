#!/usr/bin/env python3
"""
Tests for observer room switching across tournament rollovers.
"""

import asyncio
import json
import os
import sys
import unittest


SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SERVER_DIR not in sys.path:
    sys.path.insert(0, SERVER_DIR)

import main


class FakeObserverWebSocket:
    def __init__(self, room_id: int):
        self.query_params = {"room": str(room_id)}
        self.sent_messages = []
        self._incoming_messages = asyncio.Queue()

    async def accept(self):
        return None

    async def send_json(self, data):
        self.sent_messages.append(data)

    async def receive_text(self):
        next_message = await self._incoming_messages.get()
        if isinstance(next_message, Exception):
            raise next_message
        return next_message

    def queue_text(self, message: str):
        self._incoming_messages.put_nowait(message)

    def queue_disconnect(self, code: int = 1000):
        self._incoming_messages.put_nowait(main.WebSocketDisconnect(code=code))


class ObserverRoomSwitchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_room_manager = main.room_manager
        self.original_competition = main.competition
        main.room_manager = main.RoomManager()
        main.competition = main.Competition()

    async def asyncTearDown(self):
        main.room_manager = self.original_room_manager
        main.competition = self.original_competition

    async def wait_for(self, predicate, timeout=1):
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if predicate():
                return
            await asyncio.sleep(0)
        self.fail("Timed out waiting for observer state update")

    def make_active_room(self, room_id: int, player1: str, player2: str):
        room = main.GameRoom(room_id)
        room.connections = {1: object(), 2: object()}
        room.names = {1: player1, 2: player2}
        room.game.running = True
        return room

    async def test_switch_room_removes_observer_from_auto_joined_room_after_rollover(self):
        old_room = self.make_active_room(99, "Old A", "Old B")
        main.room_manager.rooms = {99: old_room}

        websocket = FakeObserverWebSocket(99)
        observe_task = asyncio.create_task(main.observe_game(websocket))

        await self.wait_for(lambda: any(
            message.get("type") == "observer_joined" and message.get("room_id") == 99
            for message in websocket.sent_messages
        ))
        self.assertIn(websocket, old_room.observers)

        main.room_manager.clear_all_rooms()
        self.assertIn(websocket, main.room_manager.lobby_observers)

        first_new_room = self.make_active_room(1, "Alpha", "Beta")
        second_new_room = self.make_active_room(2, "Gamma", "Delta")
        main.room_manager.rooms = {1: first_new_room, 2: second_new_room}

        await main.room_manager.broadcast_room_list_to_all_observers()

        await self.wait_for(lambda: any(
            message.get("type") == "observer_joined" and message.get("room_id") == 1
            for message in websocket.sent_messages
        ))
        self.assertIn(websocket, first_new_room.observers)
        self.assertNotIn(websocket, second_new_room.observers)

        websocket.queue_text(json.dumps({"action": "switch_room", "room_id": 2}))

        await self.wait_for(lambda: any(
            message.get("type") == "observer_joined" and message.get("room_id") == 2
            for message in websocket.sent_messages
        ))
        self.assertNotIn(websocket, first_new_room.observers)
        self.assertIn(websocket, second_new_room.observers)

        websocket.queue_disconnect()
        await observe_task


if __name__ == "__main__":
    unittest.main()
