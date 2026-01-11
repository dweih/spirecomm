#!/usr/bin/env python3
"""
Combat Test Client

Simple Python client that makes random combat decisions.
Tests the HTTP server with high-level actions.

IMPORTANT: Start this client AFTER you've started a run in Slay the Spire.
The client will wait for you to enter combat, then take over and play randomly.

Setup:
    1. Configure Communication Mod to run the HTTP server
    2. Start Slay the Spire and begin a run
    3. Run this script: python combat_test_client.py [--port 8080] [--verbose]
    4. Navigate to any combat encounter
    5. The client will detect combat and start playing

Usage:
    python combat_test_client.py [--port 8080] [--verbose]
"""

import sys
import time
import random
import argparse

# Try requests first, fall back to urllib
try:
    import requests
    USE_REQUESTS = True
except ImportError:
    print("Note: requests library not found, using urllib")
    import urllib.request
    import urllib.parse
    USE_REQUESTS = False


class CombatClient:
    """Simple HTTP client for SpireComm"""

    def __init__(self, host="127.0.0.1", port=8080, verbose=False):
        self.base_url = f"http://{host}:{port}"
        self.verbose = verbose

    def log(self, message):
        if self.verbose:
            print(f"[CLIENT] {message}", flush=True)

    def get_state(self):
        """Get current game state"""
        try:
            if USE_REQUESTS:
                resp = requests.get(f"{self.base_url}/state", timeout=5)
                if resp.status_code == 204:
                    return None
                if resp.status_code == 200:
                    return resp.json()
            else:
                try:
                    with urllib.request.urlopen(f"{self.base_url}/state", timeout=5) as resp:
                        import json
                        return json.loads(resp.read().decode('utf-8'))
                except urllib.error.HTTPError as e:
                    if e.code == 204:
                        return None
                    raise
        except Exception as e:
            self.log(f"Get state failed: {e}")
            return None

    def send_action(self, action_data):
        """Send action to server"""
        try:
            import json
            action_json = json.dumps(action_data)
            self.log(f"Sending: {action_data}")

            if USE_REQUESTS:
                resp = requests.post(
                    f"{self.base_url}/action",
                    data=action_json,
                    headers={"Content-Type": "application/json"},
                    timeout=5
                )
                return resp.status_code == 200
            else:
                req = urllib.request.Request(
                    f"{self.base_url}/action",
                    data=action_json.encode('utf-8'),
                    headers={"Content-Type": "application/json"}
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return resp.status == 200
        except Exception as e:
            self.log(f"Send action failed: {e}")
            return False


class RandomCombatAI:
    """Makes random combat decisions"""

    def __init__(self, client, verbose=False):
        self.client = client
        self.verbose = verbose
        self.turn_count = 0

    def log(self, message):
        print(f"[AI] {message}", flush=True)

    def wait_for_game(self, timeout=60):
        """Wait for game to start"""
        print("=" * 60)
        print("Waiting for Slay the Spire to be in-game...")
        print("Please start a run and navigate to any combat encounter.")
        print("=" * 60)

        start = time.time()
        last_status = None

        while time.time() - start < timeout:
            state = self.client.get_state()

            if state is None:
                status = "No state from server (waiting for Communication Mod...)"
                if status != last_status:
                    print(f"[STATUS] {status}")
                    last_status = status
                time.sleep(1)
                continue

            # Check if we have the expected properties
            in_game = state.get('in_game')
            ready = state.get('ready_for_command')
            game_state = state.get('game_state')

            # Diagnostic info
            if self.verbose:
                print(f"\n[DEBUG] State keys: {list(state.keys())}")
                print(f"[DEBUG] in_game: {in_game}, ready: {ready}, has_game_state: {game_state is not None}")
                if game_state:
                    print(f"[DEBUG] screen_type: {game_state.get('screen_type')}")
                    print(f"[DEBUG] floor: {game_state.get('floor')}")
                    print(f"[DEBUG] has combat_state: {'combat_state' in game_state}")

            # Success condition: in_game flag is True
            if in_game:
                print(f"[SUCCESS] Game detected! Floor {game_state.get('floor', '?')}")
                return True

            # Alternative detection: we have a valid combat state
            # (in case in_game flag isn't being set correctly)
            if game_state and 'combat_state' in game_state:
                print(f"[SUCCESS] Combat detected (without in_game flag)! Floor {game_state.get('floor', '?')}")
                return True

            # Status message
            if game_state:
                screen_type = game_state.get('screen_type', 'UNKNOWN')
                status = f"Game state received but not in combat (screen: {screen_type})"
            else:
                status = "Waiting for game state..."

            if status != last_status:
                print(f"[STATUS] {status}")
                last_status = status

            time.sleep(0.5)

        print(f"[ERROR] Timeout after {timeout}s waiting for game")
        print("\nTroubleshooting:")
        print("  1. Is Slay the Spire running with Communication Mod?")
        print("  2. Is the HTTP server script configured in Communication Mod settings?")
        print("  3. Have you started a run and entered combat?")
        print("  4. Try running with --verbose to see more details")
        return False

    def make_combat_decision(self, state):
        """Make a random combat decision"""
        if not state.get('ready_for_command'):
            return None

        game_state = state.get('game_state', {})
        commands = state.get('available_commands', [])

        # Display current state
        floor = game_state.get('floor', '?')
        hp = game_state.get('current_hp', '?')
        max_hp = game_state.get('max_hp', '?')
        screen_type = game_state.get('screen_type', 'UNKNOWN')

        self.log(f"Floor {floor} | {screen_type} | HP: {hp}/{max_hp}")
        self.log(f"  Available: {commands}")

        # Handle combat
        if 'play' in commands:
            combat_state = game_state.get('combat_state', {})
            hand = combat_state.get('hand', [])

            # 70% chance to play a card
            if hand and random.random() < 0.7:
                # Pick random playable card
                playable_cards = [i for i, card in enumerate(hand) if card.get('is_playable', False)]

                if playable_cards:
                    card_index = random.choice(playable_cards)
                    card = hand[card_index]
                    card_name = card.get('name', 'Unknown')

                    # Check if card needs target
                    if card.get('has_target'):
                        monsters = combat_state.get('monsters', [])
                        # Filter alive monsters
                        alive_monsters = [
                            i for i, m in enumerate(monsters)
                            if not m.get('is_gone') and m.get('current_hp', 0) > 0
                        ]

                        if alive_monsters:
                            target_index = random.choice(alive_monsters)
                            self.log(f"  -> Playing {card_name} (#{card_index}) -> Monster {target_index}")
                            return {"type": "play_card", "card_index": card_index, "target_index": target_index}
                        else:
                            # No valid targets, end turn instead
                            self.log("  -> No valid targets, ending turn")
                            return {"type": "end_turn"}
                    else:
                        self.log(f"  -> Playing {card_name} (#{card_index})")
                        return {"type": "play_card", "card_index": card_index}

        # End turn if we didn't play a card (or if only 'end' is available)
        if 'end' in commands:
            self.log("  -> Ending turn")
            return {"type": "end_turn"}

        # Handle proceed
        if 'proceed' in commands:
            self.log("  -> Proceeding")
            return {"type": "proceed"}

        return None

    def run(self):
        """Main loop"""
        if not self.wait_for_game():
            return False

        self.log("Starting combat AI...")

        while True:
            state = self.client.get_state()

            if not state:
                time.sleep(0.1)
                continue

            # Check if game ended
            if not state.get('in_game'):
                self.log("Game ended!")
                break

            # Make decision
            action = self.make_combat_decision(state)
            if action:
                self.client.send_action(action)

            time.sleep(0.1)

        return True


def main():
    parser = argparse.ArgumentParser(description='Combat Test Client')
    parser.add_argument('--host', default='127.0.0.1',
                        help='Server host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8080,
                        help='Server port (default: 8080)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("SpireComm Combat Test Client")
    print("=" * 60)
    print(f"Server: http://{args.host}:{args.port}")
    print(f"Verbose: {args.verbose}")
    print()
    print("This client will:")
    print("  1. Wait for you to enter combat in Slay the Spire")
    print("  2. Detect when combat starts")
    print("  3. Make random combat decisions (play cards, end turn)")
    print("  4. Continue until the game ends")
    print()
    print("Make sure you have:")
    print("  - Slay the Spire running with Communication Mod")
    print("  - HTTP server configured in Communication Mod settings")
    print("  - Started a run (but don't need to be in combat yet)")
    print("=" * 60)
    print()

    client = CombatClient(host=args.host, port=args.port, verbose=args.verbose)
    ai = RandomCombatAI(client, verbose=args.verbose)

    try:
        success = ai.run()
        if success:
            print("\n[AI] Run completed successfully!")
        else:
            print("\n[AI] Run ended (failed to start or timeout)")
    except KeyboardInterrupt:
        print("\n[AI] Interrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()

    return 0


if __name__ == '__main__':
    sys.exit(main())
