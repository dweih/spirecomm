# HTTP Bridge Examples

Example clients and scripts for using the SpireComm HTTP bridge.

## Files

### `fuzz_test.py`

A Python client that makes random decisions in the game. Useful for:
- Testing the bridge API
- Observing game behavior
- Demonstrating how to use the bridge from Python
- Stress testing the communication flow

**Usage:**
```bash
# Make sure bridge is running first
cd ..
python bridge.py --debug &

# Run fuzz tester
cd examples
python fuzz_test.py

# With options
python fuzz_test.py --port 8080 --verbose
```

**Features:**
- Works with or without `requests` library (falls back to urllib)
- Randomly plays cards, chooses options, and makes decisions
- Logs game state (floor, HP, screen type)
- Shows available commands at each decision point
- Handles combat (card targeting), events, map navigation, rewards
- Displays game outcome (victory/defeat)

**Options:**
```
--host HOST     Bridge host (default: 127.0.0.1)
--port PORT     Bridge port (default: 8080)
--verbose, -v   Enable verbose logging
```

### `curl_examples.sh`

Bash script with curl commands demonstrating all bridge endpoints.

**Usage:**
```bash
chmod +x curl_examples.sh
./curl_examples.sh
```

**Note:** Requires `jq` for pretty JSON formatting (optional).

## Example: Simple Python Client

Minimal example showing how to connect and interact:

```python
import requests
import json
import time

BRIDGE_URL = "http://localhost:8080"

# Check health
health = requests.get(f"{BRIDGE_URL}/health").json()
print(f"Bridge status: {health}")

# Wait for game to start
while True:
    resp = requests.get(f"{BRIDGE_URL}/state")
    if resp.status_code == 200:
        data = resp.json()
        state = json.loads(data["state"])  # Parse JSON string
        break
    time.sleep(0.5)

# Main game loop
while True:
    # Get state
    resp = requests.get(f"{BRIDGE_URL}/state")
    if resp.status_code != 200:
        break

    data = resp.json()
    state = json.loads(data["state"])

    if not state.get("ready_for_command"):
        time.sleep(0.05)
        continue

    # Make decision
    commands = state.get("available_commands", [])

    if "end" in commands:
        requests.post(f"{BRIDGE_URL}/action",
                     json={"command": "end"})
    elif "proceed" in commands:
        requests.post(f"{BRIDGE_URL}/action",
                     json={"command": "proceed"})
    elif "choose" in commands:
        requests.post(f"{BRIDGE_URL}/action",
                     json={"command": "choose 0"})

    time.sleep(0.1)
```

## Example: JavaScript Client

Using fetch API:

```javascript
const BRIDGE_URL = "http://localhost:8080";

async function getState() {
    const resp = await fetch(`${BRIDGE_URL}/state`);
    if (resp.status === 200) {
        const data = await resp.json();
        return JSON.parse(data.state);
    }
    return null;
}

async function sendAction(command) {
    await fetch(`${BRIDGE_URL}/action`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({command})
    });
}

async function gameLoop() {
    while (true) {
        const state = await getState();
        if (!state || !state.ready_for_command) {
            await new Promise(r => setTimeout(r, 50));
            continue;
        }

        const commands = state.available_commands || [];

        if (commands.includes('end')) {
            await sendAction('end');
        } else if (commands.includes('proceed')) {
            await sendAction('proceed');
        }

        await new Promise(r => setTimeout(r, 100));
    }
}

gameLoop();
```

## Testing with Fixtures

You can test the fuzz client against recorded fixtures:

```bash
# Terminal 1: Replay fixtures
cd ..
python test_bridge.py fixtures/sample --delay-ms 100

# Terminal 2: Run fuzz tester
cd examples
python fuzz_test.py --verbose
```

This lets you test your client logic without running the game.

## Common Patterns

### Waiting for Game Start

```python
def wait_for_game(bridge_url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{bridge_url}/state")
        if resp.status_code == 200:
            data = resp.json()
            state = json.loads(data["state"])
            if state.get('in_game'):
                return True
        time.sleep(0.5)
    return False
```

### Parsing Combat State

```python
state = get_state()
game_state = state.get('game_state', {})
combat_state = game_state.get('combat_state', {})

# Player info
player = combat_state.get('player', {})
player_hp = player.get('current_hp', 0)
player_energy = player.get('energy', 0)
player_block = player.get('block', 0)

# Monsters
monsters = combat_state.get('monsters', [])
for i, monster in enumerate(monsters):
    if not monster.get('is_gone') and monster.get('current_hp', 0) > 0:
        print(f"Monster {i}: {monster['name']} - {monster['current_hp']} HP")

# Hand
hand = combat_state.get('hand', [])
for i, card in enumerate(hand):
    print(f"Card {i+1}: {card['name']} (Cost: {card['cost']})")
```

### Playing Cards with Targeting

```python
# Play card 1 (no target)
send_action("play 1")

# Play card 2 targeting monster 0
send_action("play 2 0")

# Note: Hand positions are 1-indexed!
# Monster positions are 0-indexed!
```

### Error Handling

```python
def safe_send_action(command, max_retries=3):
    for attempt in range(max_retries):
        try:
            resp = requests.post(
                f"{BRIDGE_URL}/action",
                json={"command": command},
                timeout=5
            )
            if resp.status_code == 200:
                return True
        except requests.RequestException as e:
            print(f"Attempt {attempt+1} failed: {e}")
            time.sleep(0.1)
    return False
```

## See Also

- [Bridge README](../README.md) - Full bridge documentation
- [C++ Client](../../cpp_client/README.md) - C++ client library
- [test_bridge.py](../test_bridge.py) - Fixture replay tool
