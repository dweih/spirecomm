# spirecomm
A package for using Communication Mod with Slay the Spire, plus a simple AI

## Communication Mod

Communication Mod is a mod that allows communication between Slay the Spire and an external process. It can be found here:

https://github.com/ForgottenArbiter/CommunicationMod

The spirecomm package facilitates communicating with Slay the Spire through Communication Mod and accessing the state of the game.

## Requirements:

- Python 3.5+
- kivy, only for the example GUI for Communication Mod, found in utilities

## Usage:

### Option 1: Running the AI (Python stdin/stdout)

To run the included simple Slay the Spire AI, configure Communication Mod to run main.py

### Option 2: HTTP Server (REST API)

To run the HTTP server for external control via REST API:

```bash
python -m spirecomm.http_server
```

The HTTP server provides endpoints for querying game state and sending actions. See [HTTP_API.md](HTTP_API.md) for complete documentation.

**Quick Example:**
```bash
# Start server with debug logging
python -m spirecomm.http_server --debug --port 8080

# Check status
curl http://localhost:8080/health

# Get game state
curl http://localhost:8080/state

# Send an action
curl -X POST http://localhost:8080/action \
  -H "Content-Type: application/json" \
  -d '{"type": "end_turn"}'
```

## Installing spirecomm:

Run `python setup.py install` from the distribution root directory

## Documentation

- [HTTP_API.md](HTTP_API.md) - HTTP Server REST API documentation
- [GAME_STATE_SPECIFICATION.md](GAME_STATE_SPECIFICATION.md) - Game state structure and action format