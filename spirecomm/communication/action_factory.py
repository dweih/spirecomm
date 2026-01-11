"""
Action Factory - Deserialize JSON to Action objects

Minimal implementation for combat testing. Supports:
- play_card
- end_turn
- use_potion
- proceed
"""

from spirecomm.communication.action import (
    PlayCardAction,
    EndTurnAction,
    PotionAction,
    ProceedAction
)


def action_from_json(action_data):
    """
    Convert JSON action to Action object.

    Args:
        action_data: dict with 'type' and action-specific parameters
            Examples:
                {"type": "play_card", "card_index": 0}
                {"type": "play_card", "card_index": 0, "target_index": 1}
                {"type": "end_turn"}
                {"type": "use_potion", "potion_index": 0}
                {"type": "use_potion", "potion_index": 0, "target_index": 1}
                {"type": "proceed"}

    Returns:
        Action instance

    Raises:
        ValueError: Invalid action type or parameters
    """
    action_type = action_data.get("type")

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

    elif action_type == "proceed":
        return ProceedAction()

    else:
        raise ValueError(f"Unknown or unsupported action type: {action_type}")
