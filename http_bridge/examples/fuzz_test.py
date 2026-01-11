#!/usr/bin/env python3
"""
SpireComm Fuzz Test Client

A simple Python client that connects to the HTTP bridge and makes random
decisions. Useful for testing the bridge and observing game behavior.

This demonstrates how to use the bridge API from Python (or any language
with HTTP support).

Usage:
    python fuzz_test.py [--port 8080] [--verbose]
"""

import sys
import time
import random
import argparse
import json

# Try to use requests library, fall back to urllib if not available
try:
    import requests
    USE_REQUESTS = True
except ImportError:
    print("Note: requests library not found, using urllib (slower)")
    import urllib.request
    import urllib.parse
    USE_REQUESTS = False


class BridgeClient:
    """Simple HTTP client for SpireComm bridge"""

    def __init__(self, host="127.0.0.1", port=8080, verbose=False):
        self.base_url = f"http://{host}:{port}"
        self.verbose = verbose
        self.state_cache = None

    def log(self, message):
        """Log message if verbose mode enabled"""
        if self.verbose:
            print(f"[CLIENT] {message}", flush=True)

    def check_health(self):
        """Check if bridge is healthy"""
        try:
            if USE_REQUESTS:
                resp = requests.get(f"{self.base_url}/health", timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    self.log(f"Health check: {data}")
                    return data
            else:
                with urllib.request.urlopen(f"{self.base_url}/health", timeout=55) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    self.log(f"Health check: {data}")
                    return data
        except Exception as e:
            self.log(f"Health check failed: {e}")
            return None

    def get_state(self):
        """Get current game state"""
        try:
            if USE_REQUESTS:
                resp = requests.get(f"{self.base_url}/state", timeout=5)
                if resp.status_code == 204:
                    self.log("No state available yet (204)")
                    return None
                if resp.status_code == 200:
                    data = resp.json()
                    # Parse the state string into JSON
                    state = json.loads(data["state"])
                    self.state_cache = state
                    return state
            else:
                try:
                    with urllib.request.urlopen(f"{self.base_url}/state", timeout=5) as resp:
                        data = json.loads(resp.read().decode('utf-8'))
                        state = json.loads(data["state"])
                        self.state_cache = state
                        return state
                except urllib.error.HTTPError as e:
                    if e.code == 204:
                        self.log("No state available yet (204)")
                        return None
                    raise
        except Exception as e:
            self.log(f"Get state failed: {e}")
            return None

    def send_action(self, command):
        """Send action to bridge"""
        try:
            action_data = json.dumps({"command": command})
            self.log(f"Sending action: {command}")

            if USE_REQUESTS:
                resp = requests.post(
                    f"{self.base_url}/action",
                    data=action_data,
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                return resp.status_code == 200
            else:
                req = urllib.request.Request(
                    f"{self.base_url}/action",
                    data=action_data.encode('utf-8'),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return resp.status == 200
        except Exception as e:
            self.log(f"Send action failed: {e}")
            return False


class FuzzTester:
    """Fuzz tester that makes random decisions"""

    def __init__(self, client, verbose=False):
        self.client = client
        self.verbose = verbose
        self.turn_count = 0
        self.action_count = 0

    def log(self, message):
        """Log message"""
        print(f"[FUZZ] {message}", flush=True)

    def wait_for_game(self, timeout=30):
        """Wait for game to start"""
        self.log("Waiting for game to start...")
        start = time.time()

        while time.time() - start < timeout:
            health = self.client.check_health()
            if health and health.get('has_state'):
                state = self.client.get_state()
                if state and state.get('in_game'):
                    self.log("Game started!")
                    return True
            time.sleep(0.5)

        self.log("Timeout waiting for game")
        return False

    def make_random_decision(self, state):
        """Make a random decision based on available commands"""
        if not state.get('ready_for_command'):
            return None

        commands = state.get('available_commands', [])
        if not commands:
            return None

        # Display current game state
        game_state = state.get('game_state', {})
        floor = game_state.get('floor', '?')
        hp = game_state.get('current_hp', '?')
        max_hp = game_state.get('max_hp', '?')
        screen = game_state.get('screen_type', 'UNKNOWN')

        self.log(f"Floor {floor} | {screen} | HP: {hp}/{max_hp}")
        self.log(f"Available: {commands}")

        # Randomly choose an action based on available commands
        action = None

        if 'play' in commands:
            # In combat - randomly play a card or end turn
            combat_state = game_state.get('combat_state', {})
            hand = combat_state.get('hand', [])

            if hand and random.random() < 0.7:  # 70% chance to play card
                # Pick random card from hand (1-indexed!)
                card_index = random.randint(1, len(hand))
                card = hand[card_index - 1]
                card_name = card.get('name', 'Unknown')

                # Check if card has target
                if card.get('has_target'):
                    monsters = combat_state.get('monsters', [])
                    # Filter out dead/gone monsters
                    alive_monsters = [
                        i for i, m in enumerate(monsters)
                        if not m.get('is_gone') and m.get('current_hp', 0) > 0
                    ]
                    if alive_monsters:
                        target = random.choice(alive_monsters)
                        action = f"play {card_index} {target}"
                        self.log(f"  -> Playing {card_name} (#{card_index}) targeting monster {target}")
                    else:
                        action = "end"
                        self.log("  -> No valid targets, ending turn")
                else:
                    action = f"play {card_index}"
                    self.log(f"  -> Playing {card_name} (#{card_index})")
            elif 'end' in commands:
                action = "end"
                self.log("  -> Ending turn")

        elif 'choose' in commands:
            # Choose from options (events, map, card rewards, etc.)
            screen_state = game_state.get('screen_state', {})

            # Try to determine number of choices
            num_choices = None
            if 'options' in screen_state:
                num_choices = len(screen_state['options'])
            elif 'cards' in screen_state:
                num_choices = len(screen_state['cards'])
            elif 'choice_list' in game_state:
                num_choices = len(game_state['choice_list'])

            if num_choices and num_choices > 0:
                choice = random.randint(0, num_choices - 1)
                action = f"choose {choice}"
                self.log(f"  -> Choosing option {choice} (of {num_choices})")
            else:
                # Just choose 0 as fallback
                action = "choose 0"
                self.log("  -> Choosing option 0 (unknown choices)")

        elif 'proceed' in commands or 'confirm' in commands:
            action = "proceed"
            self.log("  -> Proceeding")

        elif 'skip' in commands:
            # Randomly skip or not (50/50)
            if random.random() < 0.5:
                action = "skip"
                self.log("  -> Skipping")
            elif 'choose' in commands:
                action = "choose 0"
                self.log("  -> Not skipping, choosing option 0")
            else:
                action = "skip"
                self.log("  -> Skipping (no other option)")

        elif 'leave' in commands or 'return' in commands:
            action = "leave"
            self.log("  -> Leaving")

        elif 'cancel' in commands:
            action = "cancel"
            self.log("  -> Canceling")

        elif 'end' in commands:
            action = "end"
            self.log("  -> Ending turn")

        else:
            self.log("  -> No known command available")

        return action

    def run(self):
        """Main fuzz testing loop"""
        if not self.wait_for_game():
            return False

        self.log("Starting fuzz test (Ctrl+C to stop)...")

        try:
            while True:
                state = self.client.get_state()

                if not state:
                    time.sleep(0.1)
                    continue

                # Check if game ended
                if not state.get('in_game'):
                    self.log("Game ended!")
                    game_state = state.get('game_state', {})
                    screen_type = game_state.get('screen_type', '')
                    if screen_type == 'GAME_OVER':
                        victory = game_state.get('screen_state', {}).get('victory', False)
                        if victory:
                            self.log("VICTORY!")
                        else:
                            self.log("DEFEAT!")
                    break

                # Make decision
                action = self.make_random_decision(state)
                if action:
                    self.client.send_action(action)
                    self.action_count += 1

                # Brief delay between decisions
                time.sleep(0.1)

        except KeyboardInterrupt:
            self.log("\nInterrupted by user")

        self.log(f"Total actions taken: {self.action_count}")
        return True


def main():
    parser = argparse.ArgumentParser(description='SpireComm Fuzz Test Client')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Bridge host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8080,
                        help='Bridge port (default: 8080)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()

    print("SpireComm Fuzz Test Client")
    print("==========================")
    print(f"Connecting to {args.host}:{args.port}\n")

    # Create client
    client = BridgeClient(host=args.host, port=args.port, verbose=args.verbose)

    # Check connection
    health = client.check_health()
    if not health:
        print("ERROR: Cannot connect to bridge!", file=sys.stderr)
        print("Make sure the bridge is running:", file=sys.stderr)
        print(f"  python bridge.py --port {args.port}", file=sys.stderr)
        return 1

    print("Connected to bridge!")
    print(f"Bridge status: {health}\n")

    # Create and run fuzz tester
    tester = FuzzTester(client, verbose=args.verbose)
    tester.run()

    return 0


if __name__ == '__main__':
    sys.exit(main())
