"""
SpireComm HTTP Client - Type-safe Python client for the SpireComm HTTP API

Provides typed action methods and enum constants to eliminate error-prone string comparisons.

Usage:
    from spirecomm.http_client import SpireHttpClient, ScreenType, RoomType, RoomPhase

    client = SpireHttpClient(host='127.0.0.1', port=8080)
    state = client.get_state()

    if state and state.get('in_game'):
        game = state['game_state']
        if game.screen_type == ScreenType.MAP:
            client.choose(choice_index=0)
"""

import json
import requests

from spirecomm.spire.screen import ScreenType, RestOption, ChestType, RewardType
from spirecomm.spire.character import PlayerClass, Intent
from spirecomm.spire.game import RoomPhase, RoomType, Game

__all__ = [
    'SpireHttpClient',
    'ScreenType', 'RestOption', 'ChestType', 'RewardType',
    'PlayerClass', 'Intent', 'RoomPhase', 'RoomType'
]


class SpireHttpClient:
    """
    HTTP client for SpireComm server with typed action methods.

    Eliminates error-prone string comparisons by providing:
    - Typed action methods (e.g., play_card(), end_turn())
    - Enum constants (ScreenType, RoomType, RoomPhase, etc.)
    - Structured state responses with parsed Game objects

    All action methods return bool: True on success, False on failure.
    """

    def __init__(self, host='127.0.0.1', port=8080, timeout=5):
        """
        Initialize HTTP client.

        Args:
            host: Server host (default: 127.0.0.1)
            port: Server port (default: 8080)
            timeout: Request timeout in seconds (default: 5)
        """
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout

    # ==================== Generic HTTP Methods ====================

    def get_health(self):
        """
        Get server health status.

        Returns:
            dict: Health status with keys: status, in_game, game_ready, has_state, queue_size
            None: On error
        """
        try:
            resp = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            return None

    def get_state(self):
        """
        Get current game state.

        Returns:
            dict: Game state with keys:
                - 'raw': Raw JSON from server
                - 'in_game': bool
                - 'ready_for_command': bool
                - 'available_commands': list of str
                - 'game_state': Game object (parsed) or raw dict
            None: If no state available (204) or on error
        """
        try:
            resp = requests.get(f"{self.base_url}/state", timeout=self.timeout)
            if resp.status_code == 204:
                return None
            if resp.status_code == 200:
                return self._parse_state_response(resp.json())
        except Exception:
            return None

    def _parse_state_response(self, data):
        """Parse state response and add Game object"""
        try:
            # Parse game state using Game.from_json
            game_state_json = data.get('game_state')
            available_commands = data.get('available_commands', [])

            if game_state_json:
                # Parse to Game object
                game_obj = Game.from_json(game_state_json, available_commands)
                data['game_state'] = game_obj

            # Keep raw data accessible
            return data
        except Exception:
            # If parsing fails, return raw data
            return data

    def send_action(self, action_dict):
        """
        Send a generic action to the server.

        Args:
            action_dict: Action dictionary with 'type' and action-specific parameters

        Returns:
            bool: True on success (200), False on failure
        """
        try:
            resp = requests.post(
                f"{self.base_url}/action",
                json=action_dict,
                timeout=self.timeout
            )
            return resp.status_code == 200
        except Exception:
            return False

    # ==================== Combat Actions ====================

    def play_card(self, card_index, target_index=None):
        """
        Play a card from hand.

        Args:
            card_index: Index of card in hand (0-based)
            target_index: Optional target monster index (for targeted cards)

        Returns:
            bool: True on success, False on failure
        """
        action = {
            "type": "play_card",
            "card_index": card_index
        }
        if target_index is not None:
            action["target_index"] = target_index
        return self.send_action(action)

    def end_turn(self):
        """
        End the current turn in combat.

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({"type": "end_turn"})

    def use_potion(self, potion_index, target_index=None):
        """
        Use a potion.

        Args:
            potion_index: Index of potion (0-based)
            target_index: Optional target monster index (for targeted potions)

        Returns:
            bool: True on success, False on failure
        """
        action = {
            "type": "use_potion",
            "potion_index": potion_index
        }
        if target_index is not None:
            action["target_index"] = target_index
        return self.send_action(action)

    def discard_potion(self, potion_index):
        """
        Discard a potion.

        Args:
            potion_index: Index of potion (0-based)

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({
            "type": "discard_potion",
            "potion_index": potion_index
        })

    # ==================== Navigation Actions ====================

    def proceed(self):
        """
        Proceed/continue to next screen.

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({"type": "proceed"})

    def cancel(self):
        """
        Cancel current action or go back.

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({"type": "cancel"})

    # ==================== Choice Actions ====================

    def choose(self, choice_index=None, name=None):
        """
        Make a generic choice.

        Args:
            choice_index: Index of choice (0-based)
            name: Name of choice (alternative to index)

        Returns:
            bool: True on success, False on failure
        """
        action = {"type": "choose"}
        if choice_index is not None:
            action["choice_index"] = choice_index
        if name is not None:
            action["name"] = name
        return self.send_action(action)

    # ==================== Rest Site Actions ====================

    def rest(self, option):
        """
        Choose a rest site option.

        Args:
            option: Rest option string ('rest', 'smith', 'dig', 'lift', 'recall', 'toke')

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({
            "type": "rest",
            "option": option
        })

    # ==================== Reward Actions ====================

    def card_reward(self, card_name=None, bowl=False):
        """
        Choose a card reward or use Singing Bowl.

        Args:
            card_name: Name of card to choose
            bowl: If True, use Singing Bowl instead

        Returns:
            bool: True on success, False on failure
        """
        action = {"type": "card_reward"}
        if bowl:
            action["bowl"] = True
        elif card_name is not None:
            action["card_name"] = card_name
        return self.send_action(action)

    def combat_reward(self, reward_index):
        """
        Choose a combat reward.

        Args:
            reward_index: Index into rewards array (0-based)

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({
            "type": "combat_reward",
            "reward_index": reward_index
        })

    def boss_reward(self, relic_name):
        """
        Choose a boss relic.

        Args:
            relic_name: Name of relic to choose

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({
            "type": "boss_reward",
            "relic_name": relic_name
        })

    # ==================== Shop Actions ====================

    def buy_card(self, card_name):
        """
        Buy a card from the shop.

        Args:
            card_name: Name of card to buy

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({
            "type": "buy_card",
            "card_name": card_name
        })

    def buy_relic(self, relic_name):
        """
        Buy a relic from the shop.

        Args:
            relic_name: Name of relic to buy

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({
            "type": "buy_relic",
            "relic_name": relic_name
        })

    def buy_potion(self, potion_name):
        """
        Buy a potion from the shop.

        Args:
            potion_name: Name of potion to buy

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({
            "type": "buy_potion",
            "potion_name": potion_name
        })

    def buy_purge(self, card_name=None):
        """
        Buy card removal from the shop.

        Args:
            card_name: Optional name of card to remove

        Returns:
            bool: True on success, False on failure
        """
        action = {"type": "buy_purge"}
        if card_name is not None:
            action["card_name"] = card_name
        return self.send_action(action)

    # ==================== Card Selection Actions ====================

    def card_select(self, card_names):
        """
        Select cards from hand or grid.

        Args:
            card_names: List of card names to select

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({
            "type": "card_select",
            "card_names": card_names
        })

    # ==================== Map Actions ====================

    def choose_map_node(self, x, y):
        """
        Choose a map node by coordinates.

        Args:
            x: Node X coordinate
            y: Node Y coordinate

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({
            "type": "choose_map_node",
            "x": x,
            "y": y
        })

    def choose_map_boss(self):
        """
        Go to the boss node.

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({"type": "choose_map_boss"})

    # ==================== Chest Actions ====================

    def open_chest(self):
        """
        Open a chest.

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({"type": "open_chest"})

    # ==================== Event Actions ====================

    def event_option(self, choice_index):
        """
        Choose an event option.

        Args:
            choice_index: Index of event option

        Returns:
            bool: True on success, False on failure
        """
        return self.send_action({
            "type": "event_option",
            "choice_index": choice_index
        })

    # ==================== Game Control ====================

    def start_game(self, character, ascension=0, seed=None):
        """
        Start a new game.

        Args:
            character: Character name string ('IRONCLAD', 'THE_SILENT', 'DEFECT', 'WATCHER')
            ascension: Ascension level (default: 0)
            seed: Optional seed string

        Returns:
            bool: True on success, False on failure
        """
        action = {
            "type": "start_game",
            "character": character,
            "ascension": ascension
        }
        if seed is not None:
            action["seed"] = seed
        return self.send_action(action)
