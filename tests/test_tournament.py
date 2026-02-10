#!/usr/bin/env python3
"""
Tournament Integration Test

Launches the CopperHead server with server-settings.test.json,
observes the tournament to completion, and verifies that a champion
is declared with no anomalies.

Usage:
    python test_tournament.py
"""

import os
import subprocess
import sys
import time
import requests
import math
import signal

# Paths are relative to the server root (parent of tests/)
SERVER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER_URL = "http://localhost:8765"
SETTINGS_FILE = "server-settings.test.json"
POLL_INTERVAL = 2       # seconds between status checks
TIMEOUT = 300           # max seconds to wait for tournament to finish

def log(msg):
    print(f"[TEST] {msg}", flush=True)

def start_server():
    """Start the CopperHead server as a subprocess."""
    log(f"Starting server with {SETTINGS_FILE}...")
    proc = subprocess.Popen(
        [sys.executable, "-u", "main.py", SETTINGS_FILE],
        cwd=SERVER_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # Wait for server to be ready
    for _ in range(30):
        try:
            r = requests.get(f"{SERVER_URL}/status", timeout=2)
            if r.status_code == 200:
                log("Server is up.")
                return proc
        except requests.ConnectionError:
            pass
        time.sleep(1)
    proc.kill()
    raise RuntimeError("Server failed to start within 30 seconds")

def get_competition():
    """Fetch /competition endpoint with retries."""
    for attempt in range(5):
        try:
            return requests.get(f"{SERVER_URL}/competition", timeout=15).json()
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(2)
    raise RuntimeError("Failed to reach /competition after 5 retries")

def get_history():
    """Fetch /history endpoint with retries."""
    for attempt in range(5):
        try:
            return requests.get(f"{SERVER_URL}/history", timeout=15).json()
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(2)
    raise RuntimeError("Failed to reach /history after 5 retries")

def run_test():
    anomalies = []
    server_proc = None

    try:
        server_proc = start_server()

        comp = get_competition()
        arenas = comp["required"] // 2
        expected_players = comp["required"]
        expected_rounds = max(1, math.ceil(math.log2(expected_players)))

        log(f"Config: {arenas} arenas, {expected_players} players, "
            f"up to {expected_rounds} rounds, points_to_win={comp['points_to_win']}")

        # --- Phase 1: Wait for competition to start ---
        log("Waiting for competition to start...")
        start_wait = time.time()
        while time.time() - start_wait < TIMEOUT:
            comp = get_competition()
            if comp["state"] == "in_progress":
                break
            if comp["state"] == "complete":
                break
            time.sleep(POLL_INTERVAL)
        else:
            anomalies.append("TIMEOUT waiting for competition to start")

        if comp["state"] not in ("in_progress", "complete"):
            anomalies.append(f"Unexpected state after waiting: {comp['state']}")

        if comp["players"] != expected_players:
            anomalies.append(f"Expected {expected_players} players, got {comp['players']}")

        log(f"Competition started with {comp['players']} players. Round {comp['round']}.")

        # --- Phase 2: Observe rounds until completion ---
        prev_round = 0
        bye_seen = False

        while time.time() - start_wait < TIMEOUT:
            comp = get_competition()
            current_round = comp["round"]

            # Log round transitions
            if current_round != prev_round:
                log(f"Round {current_round}/{comp['total_rounds']} "
                    f"(state={comp['state']}, bye={comp.get('bye_player')})")
                prev_round = current_round

            # Track Bye usage
            if comp.get("bye_player"):
                bye_seen = True

            # Check for completion
            if comp["state"] == "complete":
                break

            # Anomaly: round number should not exceed expected rounds
            if current_round > expected_rounds:
                anomalies.append(f"Round {current_round} exceeds expected max of {expected_rounds}")

            time.sleep(POLL_INTERVAL)
        else:
            anomalies.append(f"TIMEOUT: tournament did not finish within {TIMEOUT}s")

        # --- Phase 3: Verify completion ---
        comp = get_competition()
        history = get_history()

        if comp["state"] != "complete":
            anomalies.append(f"Final state is '{comp['state']}', expected 'complete'")

        champion = comp.get("champion")
        if not champion:
            anomalies.append("No champion declared")
        else:
            log(f"Champion: {champion}")

        # Verify history recorded the championship
        championships = history.get("championships", [])
        if len(championships) == 0:
            anomalies.append("No championship recorded in /history")
        else:
            latest = championships[-1]
            if latest["champion"] != champion:
                anomalies.append(
                    f"History champion '{latest['champion']}' != "
                    f"competition champion '{champion}'"
                )
            if latest["players"] != expected_players:
                anomalies.append(
                    f"History player count {latest['players']} != expected {expected_players}"
                )

        # With 5 arenas (10 players), Round 2 has 5 winners → odd → Bye expected
        if arenas >= 3 and not bye_seen:
            anomalies.append("Expected a Bye in this tournament but none was observed")

    except Exception as e:
        anomalies.append(f"Exception: {e}")

    finally:
        if server_proc:
            log("Stopping server...")
            server_proc.kill()
            server_proc.wait(timeout=10)

    # --- Report ---
    print()
    if anomalies:
        print("=" * 50)
        print(f"FAIL - {len(anomalies)} anomaly(ies) detected:")
        for i, a in enumerate(anomalies, 1):
            print(f"  {i}. {a}")
        print("=" * 50)
        return 1
    else:
        print("=" * 50)
        print("PASS - Tournament completed successfully, no anomalies.")
        print("=" * 50)
        return 0

if __name__ == "__main__":
    sys.exit(run_test())
