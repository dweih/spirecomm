#!/usr/bin/env python3
"""
SpireComm Bridge Test Fixture Replay

Replays recorded game states through the bridge for testing without the game.
Reads fixtures/*.jsonl and feeds them to bridge stdin, allowing HTTP clients
to connect and test against recorded gameplay.
"""

import sys
import os
import json
import subprocess
import time
import argparse
from pathlib import Path


def replay_fixtures(fixture_dir, port=8080, delay_ms=100, debug=False):
    """
    Replay recorded fixtures through the bridge.

    Args:
        fixture_dir: Directory containing states.jsonl fixture file
        port: Port for bridge HTTP server
        delay_ms: Milliseconds to wait between state updates
        debug: Enable debug logging
    """
    fixture_path = Path(fixture_dir) / 'states.jsonl'

    if not fixture_path.exists():
        print(f"Error: Fixture file not found: {fixture_path}", file=sys.stderr)
        return 1

    # Read all fixtures
    fixtures = []
    with open(fixture_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                fixture = json.loads(line)
                fixtures.append(fixture)
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping malformed JSON at line {line_num}: {e}", file=sys.stderr)

    if not fixtures:
        print(f"Error: No valid fixtures found in {fixture_path}", file=sys.stderr)
        return 1

    print(f"Loaded {len(fixtures)} fixtures from {fixture_path}")
    print(f"Ready to replay. Press Ctrl+C to stop.\n")

    # Prepare bridge command
    bridge_script = Path(__file__).parent / 'bridge.py'
    bridge_cmd = [sys.executable, str(bridge_script), '--port', str(port)]
    if debug:
        bridge_cmd.append('--debug')

    # Start bridge as subprocess
    bridge_proc = subprocess.Popen(
        bridge_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,
        text=True,
        bufsize=1  # Line buffered
    )

    try:
        # Wait for bridge to start
        time.sleep(0.5)

        # Send initial ready handshake
        ready_msg = json.dumps({"ready": True})
        print(f"[REPLAY] Sending ready handshake...")
        bridge_proc.stdin.write(ready_msg + '\n')
        bridge_proc.stdin.flush()

        # Read ready response
        response = bridge_proc.stdout.readline()
        if response:
            print(f"[REPLAY] Bridge responded: {response.strip()}")

        time.sleep(0.5)

        # Replay fixtures
        delay_sec = delay_ms / 1000.0

        for i, fixture in enumerate(fixtures, 1):
            state = fixture['state']
            screen_type = fixture.get('screen_type', 'UNKNOWN')

            print(f"[REPLAY] {i}/{len(fixtures)}: {screen_type} (seq={fixture.get('sequence', -1)})")

            # Send state to bridge
            state_json = json.dumps(state)
            bridge_proc.stdin.write(state_json + '\n')
            bridge_proc.stdin.flush()

            # Wait before next state
            time.sleep(delay_sec)

        print(f"\n[REPLAY] Finished replaying {len(fixtures)} fixtures.")
        print("[REPLAY] Bridge still running. Press Ctrl+C to stop.")

        # Keep bridge running
        bridge_proc.wait()

    except KeyboardInterrupt:
        print("\n[REPLAY] Interrupted, shutting down bridge...")
    finally:
        bridge_proc.terminate()
        try:
            bridge_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            bridge_proc.kill()

    return 0


def create_sample_fixture(output_dir):
    """Create a sample fixture for testing purposes"""
    os.makedirs(output_dir, exist_ok=True)

    # Sample game states
    sample_states = [
        {
            'sequence': 0,
            'timestamp': time.time(),
            'screen_type': 'MAP',
            'state': {
                'in_game': True,
                'ready_for_command': True,
                'game_state': {
                    'current_hp': 70,
                    'max_hp': 70,
                    'floor': 1,
                    'act': 1,
                    'gold': 99,
                    'class': 'IRONCLAD',
                    'screen_type': 'MAP',
                    'room_phase': 'INCOMPLETE'
                },
                'available_commands': ['choose', 'proceed']
            }
        },
        {
            'sequence': 1,
            'timestamp': time.time(),
            'screen_type': 'COMBAT',
            'state': {
                'in_game': True,
                'ready_for_command': True,
                'game_state': {
                    'current_hp': 70,
                    'max_hp': 70,
                    'floor': 2,
                    'act': 1,
                    'gold': 99,
                    'class': 'IRONCLAD',
                    'screen_type': 'COMBAT',
                    'room_phase': 'COMBAT',
                    'combat_state': {
                        'player': {
                            'current_hp': 70,
                            'block': 0,
                            'energy': 3,
                            'powers': []
                        },
                        'monsters': [
                            {
                                'name': 'Jaw Worm',
                                'current_hp': 42,
                                'max_hp': 42,
                                'block': 0,
                                'intent': 'ATTACK',
                                'move_base_damage': 11
                            }
                        ],
                        'hand': [],
                        'draw_pile': [],
                        'discard_pile': [],
                        'turn': 1
                    }
                },
                'available_commands': ['play', 'end', 'potion']
            }
        },
        {
            'sequence': 2,
            'timestamp': time.time(),
            'screen_type': 'COMBAT_REWARD',
            'state': {
                'in_game': True,
                'ready_for_command': True,
                'game_state': {
                    'current_hp': 55,
                    'max_hp': 70,
                    'floor': 2,
                    'act': 1,
                    'gold': 115,
                    'class': 'IRONCLAD',
                    'screen_type': 'COMBAT_REWARD',
                    'room_phase': 'COMPLETE'
                },
                'available_commands': ['proceed']
            }
        }
    ]

    # Write to fixture file
    fixture_path = Path(output_dir) / 'states.jsonl'
    with open(fixture_path, 'w') as f:
        for state in sample_states:
            f.write(json.dumps(state) + '\n')

    print(f"Created sample fixture with {len(sample_states)} states at {fixture_path}")
    return output_dir


def main():
    parser = argparse.ArgumentParser(description='Replay SpireComm fixtures through bridge')
    parser.add_argument('fixture_dir', nargs='?', help='Directory containing states.jsonl')
    parser.add_argument('--port', type=int, default=8080, help='Bridge port (default: 8080)')
    parser.add_argument('--delay-ms', type=int, default=100,
                        help='Delay between states in milliseconds (default: 100)')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--create-sample', type=str, metavar='DIR',
                        help='Create sample fixture in specified directory and exit')

    args = parser.parse_args()

    if args.create_sample:
        create_sample_fixture(args.create_sample)
        return 0

    if not args.fixture_dir:
        parser.print_help()
        print("\nError: fixture_dir is required (or use --create-sample)", file=sys.stderr)
        return 1

    return replay_fixtures(args.fixture_dir, args.port, args.delay_ms, args.debug)


if __name__ == '__main__':
    sys.exit(main())
