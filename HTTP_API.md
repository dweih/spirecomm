# SpireComm HTTP Server API

The SpireComm HTTP Server provides a REST API for controlling Slay the Spire through Communication Mod. It wraps the Python `Coordinator` class with an HTTP interface, allowing external programs to interact with the game using HTTP requests instead of stdin/stdout.

## Starting the Server

### Basic Usage

```bash
python -m spirecomm.http_server
```

This starts the HTTP server on `http://127.0.0.1:8080` with default settings.

### Command Line Options

```bash
python -m spirecomm.http_server [OPTIONS]
```

**Options:**

- `--host HOST` - Server host address (default: `127.0.0.1`)
- `--port PORT` - Server port number (default: `8080`)
- `--debug` - Enable debug logging (logs all HTTP requests, coordinator actions, and state updates)
- `--log-file FILE` - Log file path (default: `spirecomm_server_TIMESTAMP.log`)

**Examples:**

```bash
# Start on custom port
python -m spirecomm.http_server --port 3000

# Enable debug logging
python -m spirecomm.http_server --debug

# Custom host and port with debug logging
python -m spirecomm.http_server --host 0.0.0.0 --port 3000 --debug

# Custom log file location
python -m spirecomm.http_server --log-file my_server.log --debug
```

### Logging

The server logs to a file (not console by default) to avoid interfering with Communication Mod's stdin/stdout communication. Log files are created in the current working directory.

**Log Levels:**
- **Normal mode**: INFO level - logs server startup, actions sent to game, and errors
- **Debug mode** (`--debug`): DEBUG level - logs HTTP requests, action queue operations, coordinator state updates, and detailed execution flow

**Log Format:**
```
2026-01-12 18:38:52 [spirecomm.http_server] [INFO] HTTP server listening on http://127.0.0.1:8080
2026-01-12 18:38:53 [spirecomm.coordinator] [INFO] Sending to game: ready
2026-01-12 18:39:19 [spirecomm.http_server] [DEBUG] [HTTP] Received action: {'type': 'end_turn'}
```

## API Endpoints

All endpoints return JSON responses with appropriate HTTP status codes. CORS is enabled for all endpoints (`Access-Control-Allow-Origin: *`).

---

### GET `/health`

Health check endpoint that returns the current server status.

**Response (200 OK):**
```json
{
  "status": "ready",
  "in_game": true,
  "game_ready": true,
  "has_state": true,
  "queue_size": 0
}
```

**Response Fields:**
- `status`: Always `"ready"` (server is running)
- `in_game`: `true` if a game run is active, `false` at main menu
- `game_ready`: `true` if the game can accept a new action, `false` if waiting for response
- `has_state`: `true` if game state has been received at least once
- `queue_size`: Number of actions waiting in the queue to be executed

**Use Cases:**
- Monitor whether actions are backing up in the queue
- Check if the game is ready for new commands before sending them
- Detect if the queue is stuck (queue_size not decreasing over time)

---

### GET `/state`

Get the current game state and available commands.

**Response (200 OK) - When state is available:**
```json
{
  "in_game": true,
  "ready_for_command": true,
  "available_commands": ["play", "end", "potion"],
  "game_state": {
    "screen_type": "NONE",
    "room_type": "MonsterRoom",
    "room_phase": "COMBAT",
    "current_hp": 80,
    "max_hp": 80,
    "combat_state": {
      "hand": [...],
      "monsters": [...]
    }
  }
}
```

**Response (204 No Content) - When no state available:**

Returns HTTP 204 with empty JSON `{}`. This occurs when:
- Server just started and hasn't received state from Communication Mod yet
- Game has not sent any state updates

**Response Fields:**
- `in_game`: Whether a run is currently active
- `ready_for_command`: Whether the game can accept a new action
- `available_commands`: Array of command types currently available (e.g., `["play", "end", "proceed"]`)
- `game_state`: Full game state object (see [GAME_STATE_SPECIFICATION.md](GAME_STATE_SPECIFICATION.md) for structure)

**Use Cases:**
- Poll for game state updates
- Check what actions are currently valid
- Read current combat state, player stats, available cards, etc.

---

### POST `/action`

Queue an action to be executed by the game. Actions are executed sequentially when the game is ready.

**Request Body:**

JSON object with action type and parameters. See [GAME_STATE_SPECIFICATION.md](GAME_STATE_SPECIFICATION.md) for all action types.

**Examples:**
```json
{"type": "end_turn"}
```
```json
{"type": "play_card", "card_index": 0, "target_index": 1}
```
```json
{"type": "proceed"}
```
```json
{"type": "card_select", "card_names": ["Strike", "Defend"]}
```

**Response (200 OK):**
```json
{
  "status": "queued",
  "action": "end_turn"
}
```

**Error Response (400 Bad Request) - Invalid action:**
```json
{
  "status": "error",
  "error": "Invalid action type: invalid_action"
}
```

**Error Response (400 Bad Request) - Invalid JSON:**
```json
{
  "status": "error",
  "error": "Invalid JSON"
}
```

**Error Response (500 Internal Server Error):**
```json
{
  "status": "error",
  "error": "Unexpected error message"
}
```

**Behavior:**
- Actions are added to a FIFO queue
- Actions execute sequentially when `game_ready` is `true`
- Multiple actions can be queued; they will execute in order
- If the queue becomes stuck (invalid commands causing Communication Mod to hang), use `/clear` to reset

**Use Cases:**
- Send gameplay actions (play cards, end turn, make choices, etc.)
- Queue multiple actions at once for batch execution

---

### GET/POST `/clear`

Clear all pending actions from the action queue. Useful for recovering from stuck states during development.

**Methods:** Both GET and POST are supported for convenience. Use GET for browser access, POST for programmatic access.

**Request Body:** None required

**Response (200 OK):**
```json
{
  "status": "cleared",
  "queue_size": 0
}
```

**Behavior:**
- Immediately removes all pending actions from the queue
- Does NOT affect the current game state or actions already sent to Communication Mod
- Only clears actions waiting to be executed

**Usage Examples:**

```bash
# GET (browser-friendly, just type in address bar)
http://localhost:8080/clear

# GET (curl)
curl http://localhost:8080/clear

# POST (curl)
curl -X POST http://localhost:8080/clear
```

**Use Cases:**
- Recovery from stuck/blocked queues (e.g., when invalid commands prevent progress)
- Development/debugging: cancel queued actions that are no longer needed
- Reset state after testing a sequence of actions

**When to Use:**
- If `/health` shows `queue_size` growing without decreasing
- If `game_ready` stays `false` for an extended period (Communication Mod may be stuck)
- After sending incorrect commands that you want to cancel

---

## Common Workflows

### Basic Gameplay Loop

```python
import requests
import time

BASE_URL = "http://127.0.0.1:8080"

# 1. Wait for game to be ready
while True:
    health = requests.get(f"{BASE_URL}/health").json()
    if health["game_ready"] and health["has_state"]:
        break
    time.sleep(0.1)

# 2. Get current state
state = requests.get(f"{BASE_URL}/state").json()

# 3. Decide on action based on state
if "end" in state["available_commands"]:
    # End turn
    requests.post(f"{BASE_URL}/action", json={"type": "end_turn"})
```

### Monitoring Queue Health

```python
def is_queue_stuck(base_url, timeout=5):
    """Check if action queue appears stuck"""
    health1 = requests.get(f"{base_url}/health").json()

    if health1["queue_size"] == 0:
        return False

    time.sleep(timeout)
    health2 = requests.get(f"{base_url}/health").json()

    # Queue hasn't changed and game isn't ready
    return (health2["queue_size"] > 0 and
            health2["queue_size"] == health1["queue_size"] and
            not health2["game_ready"])

# Usage
if is_queue_stuck("http://127.0.0.1:8080"):
    print("Queue appears stuck, clearing...")
    requests.post("http://127.0.0.1:8080/clear")
```

### Error Recovery

```python
def send_action_with_retry(action, max_retries=3):
    """Send action with automatic retry and queue clearing on failure"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://127.0.0.1:8080/action",
                json=action,
                timeout=5
            )

            if response.status_code == 200:
                return response.json()

            # If error, clear queue and retry
            requests.post("http://127.0.0.1:8080/clear")
            time.sleep(1)

        except requests.RequestException as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(1)

    raise Exception("Action failed after all retries")
```

## Architecture Notes

### Threading Model

The HTTP server uses a multi-threaded architecture:

1. **Main Thread**: HTTP server (`ThreadingHTTPServer`)
2. **Coordinator Thread**: Background daemon thread that:
   - Polls stdin for Communication Mod updates
   - Executes queued actions when game is ready
   - Updates game state
3. **Request Handler Threads**: One per HTTP request (automatic via `ThreadingHTTPServer`)

### State Synchronization

- `game_is_ready` flag ensures actions are only sent when Communication Mod is ready
- After sending an action, `game_is_ready` becomes `false` until Communication Mod responds
- Actions in the queue wait for `game_is_ready` before executing

### Action Queue Behavior

**Normal Flow:**
```
POST /action → queue.append() → execute when ready → send to game → wait for response → execute next action
```

**Error Flow:**
```
Invalid action → Communication Mod error → queue.clear() → error callback
```

**Stuck Flow (requires manual intervention):**
```
Invalid/malformed action → Communication Mod hangs → queue stuck → manual POST /clear needed
```

## See Also

- [GAME_STATE_SPECIFICATION.md](GAME_STATE_SPECIFICATION.md) - Complete game state structure and action format
- [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod) - The underlying mod that enables game communication
