"""
Action Factory - Deserialize JSON to Action objects

Supports all SpireComm action types for complete game interaction.
"""

from spirecomm.communication.action import (
    PlayCardAction,
    EndTurnAction,
    PotionAction,
    ProceedAction,
    CancelAction,
    ChooseAction,
    RestAction,
    CardRewardAction,
    CombatRewardAction,
    BossRewardAction,
    BuyCardAction,
    BuyRelicAction,
    BuyPotionAction,
    BuyPurgeAction,
    CardSelectAction,
    ChooseMapNodeAction,
    ChooseMapBossAction,
    StartGameAction,
    OpenChestAction,
    EventOptionAction
)
from spirecomm.spire.screen import RestOption
from spirecomm.spire.character import PlayerClass


def action_from_json(action_data):
    """
    Convert JSON action to Action object.

    Args:
        action_data: dict with 'type' and action-specific parameters

    Returns:
        Action instance

    Raises:
        ValueError: Invalid action type or parameters
    """
    action_type = action_data.get("type")

    # Combat actions
    if action_type == "play_card":
        card_index = action_data.get("card_index")
        target_index = action_data.get("target_index")
        if card_index is None:
            raise ValueError("play_card requires card_index")
        return PlayCardAction(card_index=card_index, target_index=target_index)

    elif action_type == "end_turn":
        return EndTurnAction()

    elif action_type == "use_potion":
        potion_index = action_data.get("potion_index")
        target_index = action_data.get("target_index")
        if potion_index is None:
            raise ValueError("use_potion requires potion_index")
        return PotionAction(use=True, potion_index=potion_index, target_index=target_index)

    elif action_type == "discard_potion":
        potion_index = action_data.get("potion_index")
        if potion_index is None:
            raise ValueError("discard_potion requires potion_index")
        return PotionAction(use=False, potion_index=potion_index)

    # Navigation actions
    elif action_type == "proceed":
        return ProceedAction()

    elif action_type == "cancel":
        return CancelAction()

    # Generic choice action
    elif action_type == "choose":
        choice_index = action_data.get("choice_index")
        name = action_data.get("name")
        if choice_index is None and name is None:
            raise ValueError("choose requires either choice_index or name")
        return ChooseAction(choice_index=choice_index if choice_index is not None else 0, name=name)

    # Rest site actions
    elif action_type == "rest":
        option = action_data.get("option")
        if option is None:
            raise ValueError("rest requires option (rest, smith, dig, lift, recall, toke)")
        try:
            rest_option = RestOption[option.upper()]
        except KeyError:
            raise ValueError(f"Invalid rest option: {option}. Must be one of: rest, smith, dig, lift, recall, toke")
        return RestAction(rest_option)

    # Reward actions
    elif action_type == "card_reward":
        card_name = action_data.get("card_name")
        bowl = action_data.get("bowl", False)
        if not bowl and card_name is None:
            raise ValueError("card_reward requires card_name or bowl=true")
        # Create a minimal card-like object with just a name
        if bowl:
            return CardRewardAction(bowl=True)
        else:
            class CardStub:
                def __init__(self, name):
                    self.name = name
            return CardRewardAction(card=CardStub(card_name))

    elif action_type == "combat_reward":
        reward_index = action_data.get("reward_index")
        if reward_index is None:
            raise ValueError("combat_reward requires reward_index")
        # This action needs access to coordinator to get the actual reward object
        # We'll use a special action that defers the lookup
        return _CombatRewardIndexAction(reward_index)

    elif action_type == "boss_reward":
        relic_name = action_data.get("relic_name")
        if relic_name is None:
            raise ValueError("boss_reward requires relic_name")
        class RelicStub:
            def __init__(self, name):
                self.name = name
        return BossRewardAction(RelicStub(relic_name))

    # Shop actions
    elif action_type == "buy_card":
        card_name = action_data.get("card_name")
        if card_name is None:
            raise ValueError("buy_card requires card_name")
        class CardStub:
            def __init__(self, name):
                self.name = name
        return BuyCardAction(CardStub(card_name))

    elif action_type == "buy_relic":
        relic_name = action_data.get("relic_name")
        if relic_name is None:
            raise ValueError("buy_relic requires relic_name")
        class RelicStub:
            def __init__(self, name):
                self.name = name
        return BuyRelicAction(RelicStub(relic_name))

    elif action_type == "buy_potion":
        potion_name = action_data.get("potion_name")
        if potion_name is None:
            raise ValueError("buy_potion requires potion_name")
        class PotionStub:
            def __init__(self, name):
                self.name = name
        return BuyPotionAction(PotionStub(potion_name))

    elif action_type == "buy_purge":
        card_name = action_data.get("card_name")
        if card_name is None:
            # Buy purge without specifying a card (will prompt for selection)
            return BuyPurgeAction()
        else:
            class CardStub:
                def __init__(self, name):
                    self.name = name
            return BuyPurgeAction(CardStub(card_name))

    # Card selection actions
    elif action_type == "card_select":
        card_names = action_data.get("card_names")
        if card_names is None or not isinstance(card_names, list):
            raise ValueError("card_select requires card_names as a list")
        class CardStub:
            def __init__(self, name):
                self.name = name
        card_stubs = [CardStub(name) for name in card_names]
        return _CardSelectNameAction(card_stubs)

    # Map actions
    elif action_type == "choose_map_node":
        x = action_data.get("x")
        y = action_data.get("y")
        if x is None or y is None:
            raise ValueError("choose_map_node requires x and y coordinates")
        # This action needs access to coordinator to get the actual node object
        return _ChooseMapNodeXYAction(x, y)

    elif action_type == "choose_map_boss":
        return ChooseMapBossAction()

    # Chest action
    elif action_type == "open_chest":
        return OpenChestAction()

    # Event action
    elif action_type == "event_option":
        choice_index = action_data.get("choice_index")
        if choice_index is None:
            raise ValueError("event_option requires choice_index")
        class EventOptionStub:
            def __init__(self, choice_index):
                self.choice_index = choice_index
        return EventOptionAction(EventOptionStub(choice_index))

    # Game start action
    elif action_type == "start_game":
        character = action_data.get("character")
        ascension = action_data.get("ascension", 0)
        seed = action_data.get("seed")
        if character is None:
            raise ValueError("start_game requires character (IRONCLAD, THE_SILENT, DEFECT, WATCHER)")
        try:
            player_class = PlayerClass[character.upper()]
        except KeyError:
            raise ValueError(f"Invalid character: {character}. Must be one of: IRONCLAD, THE_SILENT, DEFECT, WATCHER")
        return StartGameAction(player_class, ascension, seed)

    else:
        raise ValueError(f"Unknown action type: {action_type}")


# Special action classes that defer object lookups to execution time

class _CombatRewardIndexAction(CombatRewardAction):
    """Combat reward action that uses an index instead of a reward object"""
    def __init__(self, reward_index):
        self.reward_index = reward_index
        # Don't call super().__init__ yet because we don't have the reward object
        self.command = "choose"
        self.requires_game_ready = True

    def execute(self, coordinator):
        # Look up the actual reward object at execution time
        from spirecomm.spire.screen import ScreenType
        if coordinator.last_game_state.screen_type != ScreenType.COMBAT_REWARD:
            raise Exception("CombatRewardAction is only available on a Combat Reward Screen.")
        reward_list = coordinator.last_game_state.screen.rewards
        if self.reward_index < 0 or self.reward_index >= len(reward_list):
            raise Exception(f"Invalid reward index: {self.reward_index}")
        self.combat_reward = reward_list[self.reward_index]
        # Now call parent's execute with the actual reward object
        super().execute(coordinator)


class _ChooseMapNodeXYAction(ChooseMapNodeAction):
    """Map node action that uses x,y coordinates instead of a node object"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.command = "choose"
        self.requires_game_ready = True

    def execute(self, coordinator):
        # Look up the actual node object at execution time
        from spirecomm.spire.screen import ScreenType
        if coordinator.last_game_state.screen_type != ScreenType.MAP:
            raise Exception("MapChoiceAction is only available on a Map Screen")
        next_nodes = coordinator.last_game_state.screen.next_nodes
        matching_node = None
        for node in next_nodes:
            if node.x == self.x and node.y == self.y:
                matching_node = node
                break
        if matching_node is None:
            raise Exception(f"No node available at position ({self.x}, {self.y})")
        self.node = matching_node
        # Now call parent's execute with the actual node object
        super().execute(coordinator)


class _CardSelectNameAction(CardSelectAction):
    """Card select action that validates card names at execution time"""
    def __init__(self, card_stubs):
        self.card_stubs = card_stubs
        super().__init__([])  # Empty list initially

    def execute(self, coordinator):
        # Match card names to actual card objects from the screen
        screen_type = coordinator.last_game_state.screen_type
        from spirecomm.spire.screen import ScreenType
        if screen_type not in [ScreenType.HAND_SELECT, ScreenType.GRID]:
            raise Exception("CardSelectAction is only available on a Hand Select or Grid Select Screen.")

        available_cards = coordinator.last_game_state.screen.cards
        matched_cards = []
        for stub in self.card_stubs:
            # Find matching card in available cards
            matching_card = None
            for card in available_cards:
                if card.name == stub.name and card not in matched_cards:
                    matching_card = card
                    break
            if matching_card is None:
                raise Exception(f"Card '{stub.name}' is not available for selection")
            matched_cards.append(matching_card)

        self.cards = matched_cards
        # Now call parent's execute with the actual card objects
        super().execute(coordinator)
