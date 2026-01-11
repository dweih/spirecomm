# SpireComm HTTP Bridge

Language-agnostic HTTP bridge for interfacing with Slay the Spire via Communication Mod.

## Overview

The HTTP Bridge translates Communication Mod's stdin/stdout protocol to a simple REST API, enabling any programming language to build Slay the Spire AI agents. The bridge is ~300 lines of pure Python (no dependencies!) and exposes HTTP endpoints for state queries and action execution.

```
Slay the Spire + Communication Mod
    ↓ stdin/stdout (JSON lines)
Python HTTP Bridge
    ↓ HTTP REST (localhost:8080)
Your AI (any language!)
```

## Features

- **Zero Dependencies**: Pure Python 3.5+ standard library
- **Auto-Ready Handshake**: Automatically responds to Communication Mod within 30s timeout
- **Raw JSON Forwarding**: No parsing overhead, clients get exact game state
- **Fixture Recording**: Record gameplay for testing without the game
- **Fixture Replay**: Test your AI against recorded sessions
- **Thread-Safe**: Concurrent HTTP requests supported
- **Debug Mode**: Verbose logging for troubleshooting

## Installation

No installation required! Just Python 3.5+:

```bash
python3 bridge.py
```

## Quick Start

### 1. Configure Communication Mod

Add to Communication Mod's configuration (in-game or config file):

```json
{
  "command": "python /path/to/spirecomm/http_bridge/bridge.py",
  "runAtGameStart": true
}
```

### 2. Start the Game

Launch Slay the Spire. The bridge starts automatically and listens on `http://localhost:8080`.

### 3. Connect Your AI

```bash
# Check if bridge is running
curl http://localhost:8080/health

# Get current game state
curl http://localhost:8080/state

# Send an action
curl -X POST http://localhost:8080/action \\
  -H "Content-Type: application/json" \\
  -d '{"command": "end"}'
```

## API Reference

### `GET /health`

Check bridge status.

**Response:**
```json
{
  "status": "ready",
  "has_state": true,
  "last_update": 1234567890.123,
  "ready_sent": true
}
```

- `has_state`: Whether any game state has been received
- `last_update`: Unix timestamp of last state update
- `ready_sent`: Whether ready handshake completed

### `GET /state`

Get the latest game state.

**Response (200):**
```json
{
  "state": "{\"in_game\": true, \"ready_for_command\": true, \"game_state\": {...}, \"available_commands\": [...]}",
  "timestamp": 1234567890.123
}
```

**Response (204):** No state available yet (game not started)

**State Format** (JSON string, parse it!):
```json
{
  "in_game": true,
  "ready_for_command": true,
  "error": null,
  "game_state": {
    "current_hp": 45,
    "max_hp": 70,
    "floor": 15,
    "act": 2,
    "gold": 250,
    "class": "IRONCLAD",
    "screen_type": "COMBAT",
    "combat_state": {
      "player": {...},
      "monsters": [...],
      "hand": [...],
      ...
    },
    ...
  },
  "available_commands": ["play", "end", "potion", "proceed"]
}
```

### `POST /action`

Send an action to Communication Mod.

**Request:**
```json
{
  "command": "end"
}
```

**Common Commands:**
- `"end"` - End turn
- `"proceed"` - Proceed to next screen
- `"play 1"` - Play card at hand position 1 (1-indexed!)
- `"play 2 0"` - Play card 2, target monster 0 (0-indexed)
- `"potion use 0"` - Use potion at slot 0
- `"potion discard 1"` - Discard potion at slot 1
- `"choose 0"` - Choose option 0
- `"choose shop"` - Choose by name

**Response:**
```json
{
  "status": "sent",
  "command": "end"
}
```

**Important:** Card hand positions are **1-indexed** when sending commands but stored as 0-indexed in state!

### `GET /ready`

Manually trigger ready handshake (usually auto-handled).

**Response:**
```json
{
  "ready": true
}
```

## Environment Variables

- `SPIRECOMM_BRIDGE_PORT`: HTTP server port (default: `8080`)
- `SPIRECOMM_BRIDGE_HOST`: HTTP server host (default: `127.0.0.1`)
- `SPIRECOMM_BRIDGE_DEBUG`: Enable debug logging (values: `1`, `true`, `yes`)

**Example:**
```bash
SPIRECOMM_BRIDGE_PORT=9000 SPIRECOMM_BRIDGE_DEBUG=1 python bridge.py
```

## Command-Line Arguments

```
usage: bridge.py [-h] [--port PORT] [--host HOST] [--debug]
                 [--record-fixtures DIR]

optional arguments:
  --port PORT              HTTP server port (default: 8080)
  --host HOST              HTTP server host (default: 127.0.0.1)
  --debug                  Enable debug logging
  --record-fixtures DIR    Record game states to fixture directory
```

## Fixture Recording & Replay

### Recording Gameplay

Record game states for testing without running the game:

```bash
python bridge.py --record-fixtures fixtures/my_session
```

Play the game normally. All states are saved to `fixtures/my_session/states.jsonl`.

### Replaying Fixtures

Test your AI against recorded gameplay:

```bash
# Replay with 100ms delay between states
python test_bridge.py fixtures/my_session --delay-ms 100
```

The bridge starts and feeds recorded states. Your AI connects to `http://localhost:8080` as usual.

### Creating Sample Fixtures

Generate sample fixtures for quick testing:

```bash
python test_bridge.py --create-sample fixtures/sample
python test_bridge.py fixtures/sample
```

## Example Clients

### Fuzz Test Client (Python)

A complete Python example client that makes random decisions:

```bash
cd examples
python fuzz_test.py --verbose
```

See [examples/fuzz_test.py](examples/fuzz_test.py) for full source code and [examples/README.md](examples/README.md) for more examples.

### Minimal Python Example

```python
import requests
import json
import time

BRIDGE_URL = "http://localhost:8080"

def main():
    # Wait for game to start
    while True:
        resp = requests.get(f"{BRIDGE_URL}/state")
        if resp.status_code == 200:
            break
        time.sleep(0.5)

    # Main game loop
    while True:
        resp = requests.get(f"{BRIDGE_URL}/state")
        if resp.status_code != 200:
            break

        state = resp.json()
        game_state = json.loads(state["state"])  # Parse JSON string

        if not game_state.get("ready_for_command"):
            time.sleep(0.05)
            continue

        # Simple AI logic
        commands = game_state.get("available_commands", [])
        if "end" in commands:
            requests.post(f"{BRIDGE_URL}/action",
                         json={"command": "end"})
        elif "proceed" in commands:
            requests.post(f"{BRIDGE_URL}/action",
                         json={"command": "proceed"})

        time.sleep(0.1)

if __name__ == "__main__":
    main()
```

## Architecture

### Threading Model

- **Main Thread**: HTTP server (handles GET/POST requests)
- **Background Thread**: stdin reader (reads from Communication Mod)

### State Management

- Stores **latest state only** (turn-based game, acceptable)
- Thread-safe with lock protection
- Raw JSON strings (no parsing overhead)

### Ready Handshake

The bridge automatically detects `{"ready": true}` from Communication Mod and responds immediately. This completes the required 30-second handshake without client intervention.

## Troubleshooting

### Bridge doesn't start

**Problem:** Port 8080 already in use
**Solution:** Use different port: `python bridge.py --port 9000`

### No state available (204 response)

**Problem:** Game not started or Communication Mod not configured
**Solution:**
1. Check Communication Mod config points to bridge.py
2. Start a new run in game
3. Check bridge logs with `--debug`
4. For file logging: `python bridge.py --debug > bridge.log 2>&1`

### Actions not working

**Problem:** Commands not reaching game
**Solution:**
1. Verify state shows `"ready_for_command": true`
2. Check command format matches API reference
3. Remember: card indices are 1-indexed!
4. Enable debug mode: `python bridge.py --debug`

### State Loss

**Problem:** Missing intermediate states
**Solution:** This is expected! Bridge stores latest state only. For turn-based game, missing animation frames doesn't affect logic. If you need history, modify `BridgeState` to store `state_history = []`.

## Performance

- **HTTP Latency**: 1-3ms per request
- **Poll Interval**: 50ms recommended for clients
- **Total Overhead**: ~50-100ms per decision
- **Acceptable**: AI computation (MCTS/ML) typically dominates at 10-1000ms

## Security

**Warning:** The bridge listens on `127.0.0.1` by default (localhost only). Only expose to external network if you understand the security implications. No authentication is provided.

## Client Libraries

- **C++**: See `../cpp_client/` for full-featured C++ client library
- **Other Languages**: HTTP client + JSON parser is all you need!

## Contributing

Found a bug? Have a feature request? Please open an issue or submit a pull request!

## License

Same as SpireComm (MIT License)

## See Also

- [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod) - The underlying mod
- [SpireComm](https://github.com/ForgottenArbiter/spirecomm) - Original Python library
- [C++ Client](../cpp_client/README.md) - Full-featured C++ wrapper
