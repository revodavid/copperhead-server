#!/usr/bin/env python3
"""
Launch N bots on a CopperHead game server.

By default, selects bots randomly from CopperBot and the bots in bot-library/,
with random difficulty levels (1-10). You can restrict to a specific bot type
and/or difficulty level.

Useful for:
  - Testing a bot in a tournament setting with many competitors
  - Stress-testing tournaments with many players
  - Quickly filling a lobby for development

Usage examples:
  python launch_bots.py 8                          # Launch 8 random bots
  python launch_bots.py 4 --bot copperbot          # Launch 4 CopperBots
  python launch_bots.py 6 --difficulty 10           # Launch 6 random bots, all difficulty 10
  python launch_bots.py 8 --bot shybot -d 3        # Launch 8 ShyBots at difficulty 3
  python launch_bots.py 8 -s ws://myserver:8765/ws/ # Launch 8 bots on a remote server
"""

import argparse
import os
import random
import signal
import subprocess
import sys
import time

# ---------------------------------------------------------------------------
# Bot registry
# Each entry maps a short name to its script path (relative to the project
# root, i.e. one level up from this tests/ directory) and a display label
# used when printing launch messages.
# To add a new bot, just add an entry here.
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

BOT_REGISTRY = {
    "copperbot": {
        "path": os.path.join(PROJECT_DIR, "copperbot.py"),
        "label": "CopperBot",
    },
    "murderbot": {
        "path": os.path.join(PROJECT_DIR, "bot-library", "murderbot.py"),
        "label": "MurderBot",
    },
    "shybot": {
        "path": os.path.join(PROJECT_DIR, "bot-library", "shybot.py"),
        "label": "ShyBot",
    },
    "sleepy_snake": {
        "path": os.path.join(PROJECT_DIR, "bot-library", "sleepy_snake.py"),
        "label": "Sleepy Snake",
    },
    "ultrabot": {
        "path": os.path.join(PROJECT_DIR, "bot-library", "ultrabot.py"),
        "label": "UltraBot",
    },
}

# Delay between launching each bot (seconds) to avoid overwhelming the server
LAUNCH_DELAY = 0.2


def parse_args():
    bot_names = ", ".join(sorted(BOT_REGISTRY.keys()))
    parser = argparse.ArgumentParser(
        description="Launch N bots on a CopperHead game server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"Available bot types: {bot_names}",
    )
    parser.add_argument(
        "count",
        type=int,
        help="Number of bots to launch",
    )
    parser.add_argument(
        "--server", "-s",
        default="ws://localhost:8765/ws/",
        help="Server WebSocket URL (default: ws://localhost:8765/ws/)",
    )
    parser.add_argument(
        "--bot", "-b",
        choices=sorted(BOT_REGISTRY.keys()),
        default=None,
        help="Restrict to a specific bot type (default: random)",
    )
    parser.add_argument(
        "--difficulty", "-d",
        type=int,
        default=None,
        help="Difficulty level 1-10 for all bots (default: random)",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress output from launched bots",
    )
    args = parser.parse_args()

    # Validate inputs
    if args.count < 1:
        parser.error("count must be at least 1")
    if args.difficulty is not None and not (1 <= args.difficulty <= 10):
        parser.error("difficulty must be between 1 and 10")

    return args


def launch_bots(args):
    """Launch the requested bots and return the list of processes."""
    processes = []
    bot_names = list(BOT_REGISTRY.keys())

    for i in range(args.count):
        # Pick bot type
        bot_key = args.bot if args.bot else random.choice(bot_names)
        bot_info = BOT_REGISTRY[bot_key]

        # Pick difficulty
        difficulty = args.difficulty if args.difficulty is not None else random.randint(1, 10)

        # Build a unique display name with index suffix
        name = f"{bot_info['label']} L{difficulty} #{i + 1}"

        # Build the command
        cmd = [
            sys.executable,
            bot_info["path"],
            "--server", args.server,
            "--difficulty", str(difficulty),
            "--name", name,
        ]
        if args.quiet:
            cmd.append("--quiet")

        # Launch the bot
        try:
            proc = subprocess.Popen(cmd, cwd=SCRIPT_DIR)
            processes.append(proc)
            print(f"  🤖 #{i + 1}: {name} (PID {proc.pid})")
        except Exception as e:
            print(f"  ❌ #{i + 1}: Failed to launch {bot_info['label']}: {e}")

        # Small delay between launches to avoid thundering herd
        if i < args.count - 1:
            time.sleep(LAUNCH_DELAY)

    return processes


def wait_for_bots(processes):
    """Wait for all bot processes to finish. Ctrl+C terminates them all."""
    try:
        while True:
            # Check if any are still running
            alive = [p for p in processes if p.poll() is None]
            if not alive:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n⏹️  Stopping {len([p for p in processes if p.poll() is None])} bot(s)...")
        for proc in processes:
            if proc.poll() is None:
                proc.terminate()
        # Give bots a moment to shut down gracefully
        for proc in processes:
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
        print("All bots stopped.")


def main():
    args = parse_args()

    # Summary of what we're launching
    bot_desc = BOT_REGISTRY[args.bot]["label"] if args.bot else "random"
    diff_desc = f"L{args.difficulty}" if args.difficulty else "random"
    print(f"Launching {args.count} bot(s) on {args.server}")
    print(f"  Bot type: {bot_desc} | Difficulty: {diff_desc}")
    print()

    processes = launch_bots(args)
    launched = len(processes)

    if launched == 0:
        print("\nNo bots were launched.")
        sys.exit(1)

    print(f"\n✅ {launched} bot(s) launched. Press Ctrl+C to stop them all.")
    wait_for_bots(processes)


if __name__ == "__main__":
    main()
