#!/usr/bin/env python3
"""
Full Game Random Walk Test

Tests the HTTP server by playing through a full game with random actions.
Supports all screen types: combat, map, events, rewards, shops, rest sites, etc.

Setup:
    1. Configure Communication Mod to launch: python -m spirecomm.http_server
       (Edit: SlayTheSpire/mods/CommunicationMod/config.properties)
    2. Start Slay the Spire - this will auto-launch the HTTP server
    3. Navigate to the main menu (or start playing)
    4. Run this script: python full_game_test.py [--port 8080] [--verbose]
    5. The script will:
       - Detect the game connection
       - Start a new game if at main menu
       - OR continue playing if already in a run

Usage:
    python full_game_test.py [--port 8080] [--verbose] [--character IRONCLAD] [--ascension 0]

Note: The game MUST be running and at the main menu before starting this test.
"""

import argparse
import random
import sys
import time

from spirecomm.http_client import SpireHttpClient


class FullGameClient:
    """HTTP client that plays a full game of Slay the Spire randomly"""

    def __init__(self, host="127.0.0.1", port=8080, verbose=False):
        self.client = SpireHttpClient(host=host, port=port)
        self.verbose = verbose
        self.actions_taken = 0
        self.floors_completed = 0
        self.leave_shop_flag = False  # Flag to leave shop on next opportunity, required for shop room handling

    def log(self, message):
        if self.verbose:
            print(f"[CLIENT] {message}", flush=True)

    def print(self, message):
        """Always print important messages"""
        print(message, flush=True)

    def dump_state(self, state, label="STATE_DUMP"):
        """Dump full state JSON for debugging"""
        import json
        self.log(f"\n{label}:")
        self.log(json.dumps(state, indent=2)[:2000])  # First 2000 chars

    def get_state(self):
        """Get current game state"""
        return self.client.get_state()

    def send_action(self, action_data):
        """Send action to server (for generic actions)"""
        self.log(f"Sending: {action_data}")
        success = self.client.send_action(action_data)
        if success:
            self.actions_taken += 1
        else:
            self.print(f"Action failed: {action_data}")
        return success

    def handle_combat(self, state):
        """Handle combat screen with random actions"""
        game_state = state['game_state']

        combat_state = game_state.get('combat_state', None)
        if not combat_state:
            return False

        # Check available commands
        available_commands = state.get('available_commands', [])

        # Get hand and monsters
        hand = combat_state.get('hand', [])
        monsters = combat_state.get('monsters', [])

        # 5% chance to end turn if available
        if 'end' in available_commands and random.random() < 0.05:
            self.print("  -> Ending turn")
            success = self.client.end_turn()
            if success:
                self.actions_taken += 1
            return success

        # Try to play a random playable card
        if 'play' in available_commands and hand:
            playable_cards = [i for i, card in enumerate(hand) if card.get('is_playable', False)]

            if playable_cards:
                card_index = random.choice(playable_cards)
                card = hand[card_index]

                # If card has target, pick a random alive monster
                # CRITICAL FIX: target_index must be index in original monsters array, not filtered list
                if card.get('has_target', False):
                    # Get indices of alive monsters in the original monsters array
                    alive_indices = [
                        i for i, m in enumerate(monsters)
                        if not m.get('is_gone', False) and not m.get('half_dead', False)
                    ]

                    if alive_indices:
                        target_index = random.choice(alive_indices)
                        self.print(f"  -> Playing card {card_index}: {card.get('name', '?')} targeting monster {target_index}")
                        success = self.client.play_card(card_index, target_index)
                        if success:
                            self.actions_taken += 1
                        return success
                    else:
                        # No valid targets, end turn instead
                        self.print("  -> No valid targets, ending turn")
                        success = self.client.end_turn()
                        if success:
                            self.actions_taken += 1
                        return success
                else:
                    self.print(f"  -> Playing card {card_index}: {card.get('name', '?')}")
                    success = self.client.play_card(card_index)
                    if success:
                        self.actions_taken += 1
                    return success

        # If we can't play cards, end turn
        if 'end' in available_commands:
            self.print("  -> Ending turn (no playable cards)")
            success = self.client.end_turn()
            if success:
                self.actions_taken += 1
            return success

        return False

    def handle_map(self, state):
        """Handle map screen"""
        game_state = state['game_state']
        screen = game_state.get('screen', {})

        next_nodes = screen.get('next_nodes', [])
        boss_available = screen.get('boss_available', False)

        # Small chance to go to boss if available
        if boss_available and random.random() < 0.1:
            self.print("  -> Choosing boss node")
            success = self.client.choose_map_boss()
            if success:
                self.actions_taken += 1
            return success

        # Choose random next node from available nodes
        if next_nodes:
            choice_index = random.randint(0, len(next_nodes) - 1)
            node = next_nodes[choice_index]
            self.print(f"  -> Choosing map node {choice_index} to {node.get('symbol', '?')}")
            success = self.client.choose(choice_index)
            if success:
                self.actions_taken += 1
            return success

        return False

    def handle_card_reward(self, state):
        """Handle card reward screen"""
        game_state = state['game_state']
        screen = game_state.get('screen', {})

        cards = screen.get('cards', [])
        can_bowl = screen.get('can_bowl', False)
        can_skip = screen.get('can_skip', False)

        # 20% chance to use bowl if available
        if can_bowl and random.random() < 0.2:
            self.print("  -> Using Singing Bowl")
            success = self.client.card_reward(bowl=True)
            if success:
                self.actions_taken += 1
            return success

        # 30% chance to skip if available
        if can_skip and random.random() < 0.3:
            self.print("  -> Skipping card reward")
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success

        # Choose random card
        if cards:
            card = random.choice(cards)
            card_name = card['name']
            self.print(f"  -> Choosing card: {card_name}")
            success = self.client.card_reward(card_name)
            if success:
                self.actions_taken += 1
            return success

        return False

    def handle_combat_reward(self, state):
        """Handle combat reward screen"""
        game_state = state['game_state']
        screen = game_state.get('screen', {})

        rewards = screen.get('rewards', [])

        if not rewards:
            # No rewards left, proceed
            self.print("  -> No rewards left, proceeding")
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success

        # Choose random reward
        reward_index = random.randint(0, len(rewards) - 1)
        reward = rewards[reward_index]
        reward_type = reward['reward_type']

        self.print(f"  -> Choosing reward {reward_index}: {reward_type}")
        success = self.client.combat_reward(reward_index)
        if success:
            self.actions_taken += 1
        return success

    def handle_boss_reward(self, state):
        """Handle boss reward screen"""
        game_state = state['game_state']
        screen = game_state.get('screen', {})

        relics = screen.get('relics', [])

        if relics:
            relic = random.choice(relics)
            relic_name = relic['name']
            self.print(f"  -> Choosing boss relic: {relic_name}")
            success = self.client.boss_reward(relic_name)
            if success:
                self.actions_taken += 1
            return success

        return False

    def handle_rest(self, state):
        """Handle rest site"""
        game_state = state['game_state']
        screen = game_state.get('screen', {})

        rest_options = screen.get('rest_options', [])
        has_rested = screen.get('has_rested', False)

        if has_rested or not rest_options:
            # Already rested, proceed to leave
            self.print("  -> Already rested, proceeding to MAP")
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success

        # Choose random rest option
        option = random.choice(rest_options)
        self.print(f"  -> Choosing rest option: {option}")
        success = self.client.rest(option)
        if success:
            self.actions_taken += 1
        return success

    def handle_shop_room(self, state):
        """Handle shop room (outside the shop)"""
        if self.leave_shop_flag:
            self.print("  -> Leaving shop")
            self.leave_shop_flag = False
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success
        self.print("  -> Entering shop")
        success = self.client.choose(name="shop")
        if success:
            self.actions_taken += 1
        return success

    def handle_shop(self, state):
        """Handle shop screen"""

        def _leave_shop():
            self.leave_shop_flag = True
            success = self.client.cancel()
            if success:
                self.actions_taken += 1
            return success

        game_state = state['game_state']
        screen = game_state.get('screen', {})

        cards = screen.get('cards', [])
        relics = screen.get('relics', [])
        potions = screen.get('potions', [])
        purge_available = screen.get('purge_available', False)

        gold = game_state.get('gold', 0)

        # 50% chance to leave immediately
        if random.random() < 0.5:
            self.print("  -> Leaving shop")
            return _leave_shop()

        # Try to buy something random
        buyable_items = []

        for card in cards:
            if card['price'] <= gold:
                buyable_items.append(('card', card))

        for relic in relics:
            if relic['price'] <= gold:
                buyable_items.append(('relic', relic))

        for potion in potions:
            if potion['price'] <= gold:
                buyable_items.append(('potion', potion))

        if purge_available:
            purge_cost = screen.get('purge_cost', 75)
            if purge_cost <= gold:
                buyable_items.append(('purge', {'price': purge_cost}))

        if buyable_items:
            item_type, item = random.choice(buyable_items)

            if item_type == 'card':
                self.print(f"  -> Buying card: {item['name']} for {item['price']} gold")
                success = self.client.buy_card(item['name'])
                if success:
                    self.actions_taken += 1
                return success
            elif item_type == 'relic':
                self.print(f"  -> Buying relic: {item['name']} for {item['price']} gold")
                success = self.client.buy_relic(item['name'])
                if success:
                    self.actions_taken += 1
                return success
            elif item_type == 'potion':
                self.print(f"  -> Buying potion: {item['name']} for {item['price']} gold")
                success = self.client.buy_potion(item['name'])
                if success:
                    self.actions_taken += 1
                return success
            elif item_type == 'purge':
                self.print(f"  -> Buying purge for {item['price']} gold")
                success = self.client.buy_purge()
                if success:
                    self.actions_taken += 1
                return success
        else:
            # Can't afford anything, leave
            self.print("  -> Can't afford anything, leaving shop")
            return _leave_shop()

    def handle_event(self, state):
        """Handle event screen"""
        game_state = state['game_state']
        screen = game_state.get('screen', {})

        options = screen.get('options', [])
        event_name = screen.get('event_name', 'Unknown Event')
        room_type = game_state.get('room_type', 'Unknown')

        # DIAGNOSTICS: Log full event state
        self.log("EVENT DIAGNOSTICS:")
        self.log(f"  event_name: {event_name}")
        self.log(f"  room_type: {room_type}")
        self.log(f"  num_options: {len(options)}")
        for i, opt in enumerate(options):
            self.log(f"  option[{i}]: choice_index={opt.get('choice_index')}, "
                    f"disabled={opt.get('disabled')}, label={opt.get('label', '?')[:40]}")

        # Filter out disabled options and track their array indices
        enabled_option_indices = [
            i for i, opt in enumerate(options)
            if not opt.get('disabled', False)
        ]

        if enabled_option_indices:
            # Choose a random enabled option by its array index
            array_index = random.choice(enabled_option_indices)
            option = options[array_index]

            # Use the option's choice_index if set, otherwise use array index
            choice_index = option.get('choice_index')
            if choice_index is None:
                choice_index = array_index

            label = option.get('label', '?')
            self.print(f"  -> Event '{event_name}': choosing option {choice_index} ({label})")
            success = self.client.event_option(choice_index)
            if success:
                self.actions_taken += 1
            return success

        # No enabled options, try to proceed
        self.print(f"  -> Event '{event_name}': no options available, proceeding")
        success = self.client.proceed()
        if success:
            self.actions_taken += 1
        return success

    def handle_chest(self, state):
        """Handle chest screen"""
        game_state = state['game_state']
        screen = game_state.get('screen', {})

        chest_open = screen.get('chest_open', False)

        if chest_open:
            # Chest already open, proceed
            self.print("  -> Chest already open, proceeding")
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success
        else:
            # Open the chest
            self.print("  -> Opening chest")
            success = self.client.open_chest()
            if success:
                self.actions_taken += 1
            return success

    def handle_grid_select(self, state):
        """Handle grid/hand select screen"""
        game_state = state['game_state']

        # Check if choice is available
        if not game_state.get('choice_available', False):
            self.print("  -> Grid: no choice available, proceeding")
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success

        screen = game_state.get('screen', {})
        cards = screen.get('cards', [])

        if not cards:
            self.print("  -> Grid: no cards available, proceeding")
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success

        selected_cards = screen.get('selected_cards', [])
        num_cards = screen.get('num_cards', 1)
        any_number = screen.get('any_number', False)
        can_pick_zero = screen.get('can_pick_zero', False)

        num_selected = len(selected_cards)
        num_remaining = num_cards - num_selected

        # Log what kind of selection this is
        context = []
        if screen.get('for_upgrade'):
            context.append('upgrade')
        if screen.get('for_purge'):
            context.append('remove')
        if screen.get('for_transform'):
            context.append('transform')
        context_str = '/'.join(context) if context else 'select'

        # If we've selected enough, or randomly choose to skip
        if num_remaining <= 0 or (can_pick_zero and random.random() < 0.3):
            self.print(f"  -> Grid ({context_str}): confirming selection")
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success

        # Select random cards
        available_cards = [c for c in cards if c not in selected_cards]

        if not available_cards:
            self.print(f"  -> Grid ({context_str}): no more cards available, confirming")
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success

        # Select 1 to num_remaining cards
        if any_number:
            num_to_select = random.randint(1, min(num_remaining, len(available_cards)))
        else:
            num_to_select = min(num_remaining, len(available_cards))

        selected = random.sample(available_cards, num_to_select)
        card_names = [c['name'] for c in selected]

        self.print(f"  -> Grid ({context_str}): selecting {len(card_names)} cards: {', '.join(card_names)}")
        success = self.client.card_select(card_names)
        if success:
            self.actions_taken += 1
        return success

    def handle_hand_select(self, state):
        """Handle hand select screen"""
        # Hand select uses same logic as grid select
        return self.handle_grid_select(state)

    def handle_state(self, state):
        """Handle current game state and take action"""
        if not state:
            self.log("handle_state: no state")
            return False

        in_game = state.get('in_game', False)
        if not in_game:
            self.log("handle_state: not in_game")
            return False

        if not state.get('ready_for_command'):
            self.log("handle_state: not ready_for_command")
            return False

        game_state = state.get('game_state')
        screen_type = game_state.get('screen_type', 'NONE') if game_state else 'NONE'
        room_type = game_state.get('room_type', 'Unknown') if game_state else 'Unknown'
        phase = game_state.get('room_phase', 'INCOMPLETE') if game_state else 'INCOMPLETE'
        floor = game_state.get('floor', 0) if game_state else 0
        act = game_state.get('act', 0) if game_state else 0
        current_hp = game_state.get('current_hp', 0) if game_state else 0
        max_hp = game_state.get('max_hp', 0) if game_state else 0
        gold = game_state.get('gold', 0) if game_state else 0

        # Track floor progression
        if floor > self.floors_completed:
            self.floors_completed = floor
            self.print(f"\n{'='*60}")
            self.print(f"Floor {floor} | Act {act} | HP: {current_hp}/{max_hp} | Gold: {gold}")
            self.print(f"Screen: {screen_type} | Room: {room_type} | Phase: {phase}")
            self.print(f"{'='*60}")

        # Handle based on screen type
        if screen_type == 'GAME_OVER':
            game_screen = game_state.get('screen', {})
            victory = game_screen.get('victory', False)
            score = game_screen.get('score', 0)
            self.print(f"\n{'='*60}")
            self.print(f"GAME OVER - {'VICTORY!' if victory else 'Defeat'}")
            self.print(f"Score: {score}")
            self.print(f"Actions taken: {self.actions_taken}")
            self.print(f"Floors completed: {self.floors_completed}")
            self.print(f"{'='*60}")
            return False  # End the test

        elif screen_type == 'COMPLETE':
            self.print("\nRun complete!")
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success

        elif screen_type == 'MAP':
            return self.handle_map(state)

        elif screen_type == 'CARD_REWARD':
            return self.handle_card_reward(state)

        elif screen_type == 'COMBAT_REWARD':
            return self.handle_combat_reward(state)

        elif screen_type == 'BOSS_REWARD':
            return self.handle_boss_reward(state)

        elif screen_type == 'REST':
            return self.handle_rest(state)

        elif screen_type == 'SHOP_ROOM':
            return self.handle_shop_room(state)

        elif screen_type == 'SHOP_SCREEN':
            return self.handle_shop(state)

        elif screen_type == 'EVENT':
            return self.handle_event(state)

        elif screen_type == 'CHEST':
            return self.handle_chest(state)

        elif screen_type == 'GRID':
            return self.handle_grid_select(state)

        elif screen_type == 'HAND_SELECT':
            return self.handle_hand_select(state)

        elif room_type in ['Monster', 'MonsterElite', 'Boss'] and phase == 'COMBAT':
            return self.handle_combat(state)

        else:
            # Unknown screen, log and try proceed
            self.log(f"Unknown screen: {screen_type}, room: {room_type}, phase: {phase}")
            if state.get('available_commands', []):
                self.log(f"  Available commands: {state['available_commands']}")
            success = self.client.proceed()
            if success:
                self.actions_taken += 1
            return success

    def start_game(self, character="IRONCLAD", ascension=0):
        """Start a new game"""
        self.print(f"Starting new game as {character} (Ascension {ascension})...")
        success = self.client.start_game(character, ascension)
        if success:
            self.actions_taken += 1
        return success

    def get_health(self):
        """Get server health status"""
        return self.client.get_health()

    def run(self, character="IRONCLAD", ascension=0):
        """Main game loop"""
        self.print("="*60)
        self.print("Full Game Random Walk Test")
        self.print("="*60)

        # Step 1: Check if server is alive
        self.print("Checking server connection...")
        for attempt in range(10):
            health = self.get_health()
            if health is not None:
                self.print(f"Server is alive! Status: {health.get('status', 'unknown')}")
                break
            time.sleep(1)
        else:
            self.print("ERROR: Could not connect to server at /health")
            return False

        # Step 2: Check current game state
        self.print("\nChecking current game state...")
        time.sleep(1)

        state = self.get_state()
        if state and state.get('in_game'):
            # Already in a game, continue from current state
            game_state = state.get('game_state')
            char = game_state.get('character', 'Unknown')
            floor = game_state.get('floor', 0)
            screen = game_state.get('screen_type', 'Unknown')
            self.print(f"Game already in progress! Character: {char}, Floor: {floor}, Screen: {screen}")
            self.print("Continuing from current state...")
        else:
            # Not in game, start a new one
            self.print(f"\nStarting new {character} run at Ascension {ascension}...")
            if not self.start_game(character, ascension):
                self.print("ERROR: Failed to send start_game command")
                return False

            # Wait for game to start
            self.print("Waiting for game to start...")
            time.sleep(3)

            # Verify game started
            for attempt in range(10):
                state = self.get_state()
                if state and state.get('in_game'):
                    game_state = state.get('game_state')
                    char = game_state.get('character', 'Unknown') if game_state else 'Unknown'
                    self.print(f"Game started! Playing as {char}")
                    break
                time.sleep(1)
            else:
                self.print("WARNING: Game may not have started properly, but continuing anyway...")

        # Main game loop
        consecutive_failures = 0
        max_failures = 100
        last_action_time = time.time()

        while consecutive_failures < max_failures:
            state = self.get_state()

            if state is None:
                time.sleep(0.1)
                continue

            # Check if we've been stuck for too long
            if time.time() - last_action_time > 30:
                self.print("\nWARNING: No successful actions for 30 seconds")
                if self.verbose:
                    self.dump_state(state, "STUCK_STATE")
                last_action_time = time.time()

            # Check for game over
            if state.get('in_game'):
                game_state = state.get('game_state')
                screen_type = game_state.get('screen_type') if game_state else None

                if screen_type == 'GAME_OVER':
                    # Handle final screen
                    self.handle_state(state)
                    break

            # Try to take an action
            if state.get('ready_for_command'):
                if self.handle_state(state):
                    consecutive_failures = 0
                    last_action_time = time.time()
                    time.sleep(0.2)  # Small delay between actions
                else:
                    consecutive_failures += 1
                    time.sleep(0.5)
            else:
                time.sleep(0.1)

        if consecutive_failures >= max_failures:
            self.print(f"\nERROR: {max_failures} consecutive action failures, stopping test")
            return False

        self.print("\nTest completed successfully!")
        return True


def main():
    parser = argparse.ArgumentParser(description='Full Game Random Walk Test')
    parser.add_argument('--port', type=int, default=8080,
                        help='HTTP server port (default: 8080)')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='HTTP server host (default: 127.0.0.1)')
    parser.add_argument('--verbose', action='store_true',
                        help='Enable verbose logging')
    parser.add_argument('--character', type=str, default='IRONCLAD',
                        choices=['IRONCLAD', 'THE_SILENT', 'DEFECT', 'WATCHER'],
                        help='Character to play (default: IRONCLAD)')
    parser.add_argument('--ascension', type=int, default=0,
                        help='Ascension level (default: 0)')

    args = parser.parse_args()

    client = FullGameClient(host=args.host, port=args.port, verbose=args.verbose)
    success = client.run(character=args.character, ascension=args.ascension)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
