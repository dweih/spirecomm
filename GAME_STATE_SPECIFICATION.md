# Slay the Spire Communication Mod - State Machine Specification

## State Indicators

### Top-Level Flags
- `in_game`: boolean - True when a run is active, False at main menu or after run ends
- `ready_for_command`: boolean - True when the game can accept an action
- `game_state`: object or null - Game state data (null when no state available)

### Screen Identification
- `screen_type`: string - Primary screen identifier (see Screen States below)
- `room_type`: string - Current room type (e.g., "MonsterRoom", "MonsterRoomBoss", "RestRoom", "ShopRoom", "TreasureRoom", "EventRoom", "NeowRoom")
- `room_phase`: string - Room phase (e.g., "COMBAT", "OUT_OF_COMBAT")

### Available Command Flags
- `play_available`: boolean - Can play cards
- `end_available`: boolean - Can end turn
- `proceed_available`: boolean - Can proceed/continue
- `cancel_available`: boolean - Can cancel/go back
- `potion_available`: boolean - Can use potions
- `choice_available`: boolean - A choice must be made on current screen

### Combat State Indicators
- `combat_state.hand`: array - Cards in hand
- `combat_state.monsters`: array - Enemy monsters
- Card properties: `is_playable`, `has_target`, `cost`
- Monster properties: `is_gone`, `half_dead`, `current_hp`

## Screen States

### OUT_OF_GAME (Main Menu)
**Indicators:**
- `in_game`: false
- `screen_type`: "NONE" or absent

**Valid Actions:**
- `start_game`: Start a new run

**Transition:** → NEOW_ROOM or MAP (depending on game state)

---

### NEOW_ROOM (Neow's Blessing)
**Indicators:**
- `in_game`: true
- `room_type`: "NeowRoom"
- `screen_type`: "EVENT"
- `choice_available`: true

**State Data:**
- `game_state.screen.event_name`: "Neow Event"
- `game_state.screen.options`: array of EventOption objects
  - Each option has: `choice_index`, `label`, `disabled`

**Valid Actions:**
- `event_option`: Choose a Neow blessing

**Transition:** → MAP

---

### MAP
**Indicators:**
- `screen_type`: "MAP"
- `choice_available`: true

**State Data:**
- `game_state.screen.current_node`: Current map position (x, y, symbol)
- `game_state.screen.next_nodes`: Array of available next nodes
- `game_state.screen.boss_available`: boolean
- `game_state.choice_list`: Array of available node indices (legacy)

**Valid Actions:**
- `choose`: Select node by index (from `choice_list`)
- `choose_map_node`: Select node by x,y coordinates (not in action_factory)
- `choose_map_boss`: Go to boss (when `boss_available` is true)

**Transition:** → Room type based on node symbol (M=MonsterRoom, $=ShopRoom, T=TreasureRoom, ?=EventRoom, R=RestRoom, BOSS=MonsterRoomBoss)

---

### COMBAT (Monster Encounters)
**Indicators:**
- `room_type`: "MonsterRoom" or "MonsterRoomBoss"
- `phase`: "COMBAT"
- `play_available`: true (when can play cards)
- `end_available`: true (when can end turn)
- `potion_available`: true (when can use potions)

**State Data:**
- `game_state.combat_state.hand`: Cards in hand
- `game_state.combat_state.monsters`: Enemy state
- `game_state.combat_state.draw_pile`: Cards remaining in draw pile
- `game_state.combat_state.discard_pile`: Discarded cards
- `game_state.current_hp`, `game_state.max_hp`: Player health
- `game_state.player.block`: Current block

**Valid Actions:**
- `play_card`: Play a card from hand
  - Requires: `card_index` (0-based)
  - Optional: `target_index` (when card has_target is true)
- `end_turn`: End the current turn
- `use_potion`: Use a potion
  - Requires: `potion_index`
  - Optional: `target_index` (for targeted potions)
- `discard_potion`: Discard a potion
  - Requires: `potion_index`

**Transition:**
- Victory → COMBAT_REWARD or BOSS_REWARD (if boss)
- Defeat → GAME_OVER
- Card selection effects → HAND_SELECT or GRID

---

### COMBAT_REWARD
**Indicators:**
- `screen_type`: "COMBAT_REWARD"
- `choice_available`: true or `proceed_available`: true

**State Data:**
- `game_state.screen.rewards`: Array of reward objects
  - Each reward has: `reward_type` (CARD, GOLD, RELIC, POTION, STOLEN_GOLD, EMERALD_KEY, SAPPHIRE_KEY)
  - Type-specific fields: `gold`, `relic`, `potion`, `link`

**Valid Actions:**
- `combat_reward`: Claim a reward
  - Requires: `reward_index`
- `proceed`: Skip remaining rewards and continue

**Transition:**
- After CARD reward → CARD_REWARD
- After all rewards taken → MAP

---

### CARD_REWARD
**Indicators:**
- `screen_type`: "CARD_REWARD"
- `choice_available`: true

**State Data:**
- `game_state.screen.cards`: Available card options
- `game_state.screen.can_bowl`: boolean (Singing Bowl available)
- `game_state.screen.can_skip`: boolean (Can skip without choosing)

**Valid Actions:**
- `card_reward`: Choose a card
  - Requires: `card_name`
- `card_reward`: Use Singing Bowl
  - Requires: `bowl: true`
- `proceed`: Skip (when `can_skip` is true)
- `cancel`: Skip (alternative)

**Transition:** → COMBAT_REWARD (if from combat) or MAP

---

### BOSS_REWARD
**Indicators:**
- `screen_type`: "BOSS_REWARD"
- `choice_available`: true

**State Data:**
- `game_state.screen.relics`: Array of 3 boss relics to choose from

**Valid Actions:**
- `boss_reward`: Choose a boss relic
  - Requires: `relic_name`

**Transition:** → MAP (next act) or COMPLETE (if Act 3 boss defeated)

---

### EVENT
**Indicators:**
- `screen_type`: "EVENT"
- `choice_available`: true

**State Data:**
- `game_state.screen.event_name`: Event name
- `game_state.screen.event_id`: Event ID
- `game_state.screen.body_text`: Event description
- `game_state.screen.options`: Array of EventOption objects
  - Each option has: `choice_index`, `label`, `text`, `disabled`

**Valid Actions:**
- `event_option`: Choose an event option
  - Requires: `choice_index`
- `choose`: Choose by index (legacy)
- `proceed`: Continue (when no choice needed)

**Transition:** Variable (MAP, COMBAT, GRID, HAND_SELECT, or same screen with updated options)

---

### CHEST
**Indicators:**
- `screen_type`: "CHEST"
- `choice_available`: true

**State Data:**
- `game_state.screen.chest_type`: "SMALL", "MEDIUM", "LARGE", "BOSS"
- `game_state.screen.chest_open`: boolean

**Valid Actions:**
- `open_chest`: Open the chest (when `chest_open` is false)
- `choose`: With name="open" (legacy)
- `proceed`: Leave (when `chest_open` is true or after opening)

**Transition:** → COMBAT_REWARD (chest contents) or MAP

---

### REST
**Indicators:**
- `screen_type`: "REST"
- `choice_available`: true

**State Data:**
- `game_state.screen.rest_options`: Array of available options (REST, SMITH, DIG, LIFT, RECALL, TOKE)
- `game_state.screen.has_rested`: boolean

**Valid Actions:**
- `rest`: Choose a rest option
  - Requires: `option` (one of: "rest", "smith", "dig", "lift", "recall", "toke")
- `choose`: By index (legacy)
- `proceed`: Leave (when `has_rested` is true)

**Transition:** → GRID (if SMITH chosen) or MAP

---

### SHOP_ROOM
**Indicators:**
- `screen_type`: "SHOP_ROOM"
- `choice_available`: true

**Valid Actions:**
- `choose`: With name="shop" to open shop screen

**Transition:** → SHOP_SCREEN

---

### SHOP_SCREEN
**Indicators:**
- `screen_type`: "SHOP_SCREEN"
- `choice_available`: true
- `cancel_available`: true

**State Data:**
- `game_state.screen.cards`: Available cards with `price`
- `game_state.screen.relics`: Available relics with `price`
- `game_state.screen.potions`: Available potions with `price`
- `game_state.screen.purge_available`: boolean
- `game_state.screen.purge_cost`: integer
- `game_state.gold`: Player's current gold

**Valid Actions:**
- `buy_card`: Purchase a card
  - Requires: `card_name`
- `buy_relic`: Purchase a relic
  - Requires: `relic_name`
- `buy_potion`: Purchase a potion
  - Requires: `potion_name`
- `buy_purge`: Purchase card removal
  - Optional: `card_name` (if not specified, triggers GRID selection)
- `choose`: With name="purge" (legacy)
- `cancel`: Leave shop
- `proceed`: Leave shop

**Transition:** → GRID (if purge without card specified) or MAP

---

### GRID (Card Selection Screen)
**Indicators:**
- `screen_type`: "GRID"
- `choice_available`: true

**State Data:**
- `game_state.screen.cards`: Available cards to select from
- `game_state.screen.selected_cards`: Already selected cards
- `game_state.screen.num_cards`: Number of cards to select
- `game_state.screen.any_number`: boolean (can select fewer than num_cards)
- `game_state.screen.confirm_up`: boolean (confirm button available)
- `game_state.screen.for_upgrade`: boolean
- `game_state.screen.for_transform`: boolean
- `game_state.screen.for_purge`: boolean

**Valid Actions:**
- `card_select`: Select cards
  - Requires: `card_names` (array of card names)
- `choose`: Select by index (queued internally by CardSelectAction)
- `proceed`: Confirm selection (when `confirm_up` is true or selection complete)

**Transition:** → Previous screen (REST, SHOP_SCREEN, COMBAT, EVENT) or MAP

---

### HAND_SELECT (Choose from Hand)
**Indicators:**
- `screen_type`: "HAND_SELECT"
- `choice_available`: true

**State Data:**
- `game_state.screen.cards`: Cards available to select (from hand)
- `game_state.screen.selected_cards`: Already selected cards
- `game_state.screen.num_cards`: Maximum cards to select
- `game_state.screen.can_pick_zero`: boolean

**Valid Actions:**
- `card_select`: Select cards from hand
  - Requires: `card_names` (array of card names)
- `proceed`: Confirm selection

**Transition:** → COMBAT or EVENT (depending on triggering effect)

---

### GAME_OVER
**Indicators:**
- `screen_type`: "GAME_OVER"
- `in_game`: may transition to false

**State Data:**
- `game_state.screen.victory`: boolean
- `game_state.screen.score`: integer

**Valid Actions:**
- None (terminal state)

**Transition:** → OUT_OF_GAME

---

### COMPLETE
**Indicators:**
- `screen_type`: "COMPLETE"
- `in_game`: may transition to false

**Valid Actions:**
- `proceed`: Return to main menu

**Transition:** → OUT_OF_GAME

---

## Action Format (JSON)

All actions are JSON objects with a `type` field and type-specific parameters:

```json
{"type": "start_game", "character": "IRONCLAD", "ascension": 0}
{"type": "play_card", "card_index": 0, "target_index": 1}
{"type": "end_turn"}
{"type": "use_potion", "potion_index": 0, "target_index": 0}
{"type": "discard_potion", "potion_index": 1}
{"type": "proceed"}
{"type": "cancel"}
{"type": "choose", "choice_index": 0}
{"type": "rest", "option": "smith"}
{"type": "card_reward", "card_name": "Strike"}
{"type": "card_reward", "bowl": true}
{"type": "combat_reward", "reward_index": 0}
{"type": "boss_reward", "relic_name": "Runic Dome"}
{"type": "buy_card", "card_name": "Defend"}
{"type": "buy_relic", "relic_name": "Bag of Preparation"}
{"type": "buy_potion", "potion_name": "Fire Potion"}
{"type": "buy_purge"}
{"type": "card_select", "card_names": ["Strike", "Defend"]}
{"type": "choose_map_boss"}
{"type": "open_chest"}
{"type": "event_option", "choice_index": 0}
```

## Common Patterns

### Card Targeting
When `card.has_target` is true, `play_card` requires `target_index`. Target indices refer to positions in `combat_state.monsters` array. Filter out monsters with `is_gone: true` or `half_dead: true`.

### Card Selection
`card_select` actions internally queue multiple `choose` actions (one per card) followed by optional `proceed`. The client should send a single `card_select` action, not individual `choose` actions.

### Multi-Step Actions
Some actions trigger screen transitions that require additional actions:
- Shop purge without card_name → GRID selection → choose card
- Combat rewards with CARD type → CARD_REWARD screen → choose card
- Some events → HAND_SELECT or GRID → choose cards

### State Synchronization
Actions should only be sent when `ready_for_command` is true. The coordinator will queue actions and execute them sequentially when the game is ready.

### Proceed Action Patterns

The `proceed` action is used to advance from screens that have completed their purpose. The `proceed_available` flag indicates when this action is valid.

#### When Proceed is REQUIRED:
- **COMBAT_REWARD**: After collecting all desired rewards, must `proceed` to return to MAP
- **REST**: After choosing a rest option and `has_rested` becomes true, must `proceed` to leave
- **CHEST**: After `chest_open` is true, must `proceed` to continue to rewards or MAP
- **GRID/HAND_SELECT**: After selecting required number of cards, must `proceed` to confirm
- **COMPLETE**: After Act 3 victory, must `proceed` to return to main menu
- **EVENT**: After event sequence completes (all choices made), must `proceed` to continue
- **CARD_REWARD**: When `can_skip` is true and choosing to skip, use `proceed` or `cancel`

#### When Proceed is OPTIONAL (Alternative to Other Actions):
- **SHOP_SCREEN**: Can use `proceed` or `cancel` to leave (equivalent)
- **COMBAT_REWARD**: Can use `proceed` to skip remaining rewards instead of claiming them one-by-one

#### When Proceed is NOT Used (Auto-Transition):
- **MAP**: Choosing a node automatically transitions to that room
- **NEOW_ROOM**: Choosing a blessing automatically transitions to MAP
- **BOSS_REWARD**: Choosing a boss relic automatically transitions to next act or COMPLETE
- **CARD_REWARD**: Choosing a card (not skipping) automatically returns to previous screen
- **COMBAT**: Victory automatically transitions to rewards (no proceed needed)

#### Checking Proceed Availability:
Always check `proceed_available` flag before sending `proceed` action. The flag indicates:
- Screen is in a state where proceed makes sense
- Game is ready to transition to next screen
- No required choices remain

## Room Entry and Exit Flow

### Entering Rooms (from MAP)

All room entries follow this pattern:

1. **MAP screen** with `choice_available: true`
2. Client sends node selection action (`choose`, `choose_map_node`, or `choose_map_boss`)
3. **Automatic transition** to room (no proceed needed)
4. Room screen appears with `ready_for_command: true`

### Exiting Rooms (back to MAP)

Each room type has a specific exit flow:

#### COMBAT (MonsterRoom, MonsterRoomBoss)
```
COMBAT → (victory) → COMBAT_REWARD → proceed → MAP
                   → (defeat) → GAME_OVER
```
- Combat ends automatically when all monsters defeated or player dies
- COMBAT_REWARD appears with available rewards
- Claim rewards with `combat_reward` actions (may trigger CARD_REWARD)
- When done collecting rewards: `proceed` → MAP
- For boss fights: BOSS_REWARD instead of COMBAT_REWARD

#### EVENT (EventRoom, NeowRoom)
```
EVENT → event_option → (may repeat or trigger sub-screens) → proceed → MAP
     → event_option → COMBAT → ... → back to EVENT or MAP
     → event_option → GRID/HAND_SELECT → proceed → back to EVENT or MAP
```
- Make choices with `event_option`
- Event may present multiple sequential choices (screen updates with new options)
- Some events trigger combat or card selection
- When event complete and no options available: `proceed` → MAP

#### REST (RestRoom)
```
REST → rest (choose option) → GRID (if SMITH) → proceed → MAP
                            → MAP (if REST, DIG, LIFT, etc.)
```
- Choose rest option with `rest` action
- If SMITH chosen: GRID appears for card upgrade selection
- After rest action completes: `has_rested` becomes true
- When `has_rested` is true: `proceed` → MAP

#### SHOP (ShopRoom)
```
SHOP_ROOM → choose "shop" → SHOP_SCREEN → buy actions* → cancel/proceed → MAP
                                        → buy_purge → GRID → proceed → SHOP_SCREEN → cancel/proceed → MAP
```
- First screen is SHOP_ROOM (outside shop)
- Send `choose` with name="shop" to enter
- SHOP_SCREEN appears with purchaseable items
- Make purchases with `buy_card`, `buy_relic`, `buy_potion`, `buy_purge`
- When done shopping: `cancel` or `proceed` → MAP

#### CHEST (TreasureRoom)
```
CHEST → open_chest → COMBAT_REWARD (chest contents) → proceed → MAP
```
- CHEST screen shows `chest_open: false`
- Send `open_chest`
- Screen updates to `chest_open: true` or transitions to COMBAT_REWARD
- Claim rewards, then `proceed` → MAP

### Interrupt Screens (GRID, HAND_SELECT)

These screens interrupt normal flow for card selection effects:

```
(Triggering screen) → GRID/HAND_SELECT → card_select → proceed → (back to triggering screen or MAP)
```

Examples:
- REST with SMITH → GRID (upgrade) → proceed → MAP
- SHOP_SCREEN purge → GRID (remove card) → proceed → SHOP_SCREEN
- COMBAT card effect → HAND_SELECT (discard) → proceed → COMBAT
- EVENT card effect → GRID (transform) → proceed → EVENT

**Important**: After `card_select`, the game may still require `proceed` to confirm and return to previous screen. Check `confirm_up` flag on GRID screens.

### Complete Game Flow Example

```
OUT_OF_GAME
  → start_game
  → NEOW_ROOM
  → event_option (choose blessing)
  → MAP
  → choose (select node)
  → COMBAT
  → play_card, end_turn (repeat until victory)
  → COMBAT_REWARD
  → combat_reward (claim gold)
  → combat_reward (claim card reward)
  → CARD_REWARD
  → card_reward (pick card)
  → COMBAT_REWARD (back)
  → proceed
  → MAP
  → choose (select rest site)
  → REST
  → rest (smith)
  → GRID
  → card_select (choose card to upgrade)
  → proceed
  → MAP
  → ... (continue until victory or defeat)
```
