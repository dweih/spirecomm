# SpireComm C++ Client

C++ client library for interfacing with Slay the Spire via the SpireComm HTTP server.

## Overview

The C++ client provides a high-level API for connecting to `spirecomm/http_server.py`, querying game state, and sending actions. Features include:

- **Type-safe action methods**: `playCard()`, `endTurn()`, `usePotion()`, etc.
- **Raw JSON state access**: Direct access to full game state via nlohmann/json
- **Header-only dependencies**: cpp-httplib and nlohmann/json (auto-downloaded via CMake)
- **PIMPL design**: Clean public interface, hidden implementation details
- **Synchronous API**: Simple poll-based architecture (no threading complexity)
- **Cross-platform**: Windows, Linux, macOS support

## Requirements

- C++17 compiler (GCC 7+, Clang 5+, MSVC 2017+)
- CMake 3.14+
- Internet connection (for first build to download dependencies)

## Quick Start

### 1. Build the Library

```bash
cd cpp_client
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

**Windows (Visual Studio):**
```cmd
cd cpp_client
cmake -B build
cmake --build build --config Release
```

Dependencies (cpp-httplib and nlohmann/json) are automatically downloaded during CMake configuration.

### 2. Run Example AI

First, make sure you have the HTTP server running. See the main README for setup instructions.

```bash
# Linux/Mac
./build/bin/simple_ai

# Windows
.\build\bin\Release\simple_ai.exe
```

### 3. Minimal Example

```cpp
#include <spirecomm/client.hpp>
#include <iostream>
#include <thread>
#include <chrono>

int main() {
    spirecomm::ClientConfig config;
    config.port = 8080;
    config.debug = false;

    spirecomm::SpireCommClient client(config);

    // Connect to server
    if (!client.connect()) {
        std::cerr << "Failed to connect: " << client.getLastError() << std::endl;
        return 1;
    }

    // Main game loop
    while (true) {
        auto state = client.getState();

        if (state && client.isReadyForCommand()) {
            // Access game state
            auto game_state = (*state)["game_state"];
            int hp = game_state["current_hp"];
            std::string screen_type = game_state["screen_type"];

            std::cout << "HP: " << hp << ", Screen: " << screen_type << std::endl;

            // Make decisions
            auto commands = client.getAvailableCommands();
            bool has_end = false;
            for (const auto& cmd : commands) {
                if (cmd == "end") {
                    has_end = true;
                    break;
                }
            }

            if (has_end) {
                client.endTurn();
            } else {
                client.proceed();
            }
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(50));
    }

    return 0;
}
```

## API Reference

### ClientConfig

Configuration for SpireCommClient:

```cpp
struct ClientConfig {
    std::string host = "127.0.0.1";  // Server host
    int port = 8080;                  // Server port
    int timeout_ms = 5000;            // HTTP request timeout
    bool debug = false;               // Enable debug logging
};
```

### SpireCommClient

Main client class for communicating with the HTTP server.

#### Constructor

```cpp
SpireCommClient(const ClientConfig& config = ClientConfig());
```

#### Connection Methods

```cpp
// Connect to server and verify it's responding
bool connect();

// Check if connected to server
bool isConnected() const;

// Get last error message
std::string getLastError() const;
```

#### State Methods

```cpp
// Get latest game state (returns nlohmann::json)
std::optional<nlohmann::json> getState();

// Check if currently in game
bool isInGame() const;

// Check if game is ready for command
bool isReadyForCommand() const;

// Get list of available commands
std::vector<std::string> getAvailableCommands() const;
```

#### Action Methods

```cpp
// Play a card from hand (no target required)
bool playCard(int card_index);

// Play a card from hand targeting a monster
bool playCard(int card_index, int target_index);

// End the current turn
bool endTurn();

// Use a potion (no target required)
bool usePotion(int potion_index);

// Use a potion targeting a monster
bool usePotion(int potion_index, int target_index);

// Discard a potion
bool discardPotion(int potion_index);

// Proceed to next screen (use for rewards, events, etc.)
bool proceed();
```

**Important:** All indices are 0-based (card index 0 = first card in hand, monster index 0 = first monster).

## Game State JSON Structure

The `getState()` method returns a `nlohmann::json` object with the following structure:

```json
{
  "in_game": true,
  "ready_for_command": true,
  "game_state": {
    "current_hp": 45,
    "max_hp": 70,
    "floor": 15,
    "act": 2,
    "gold": 250,
    "character": "IRONCLAD",
    "screen_type": "COMBAT",
    "room_phase": "COMBAT",
    "relics": [...],
    "deck": [...],
    "potions": [...],
    "combat_state": {
      "player": {
        "current_hp": 45,
        "block": 15,
        "energy": 3,
        "powers": [...]
      },
      "monsters": [
        {
          "name": "Jaw Worm",
          "current_hp": 30,
          "max_hp": 42,
          "intent": "ATTACK",
          "move_base_damage": 11,
          "is_gone": false
        }
      ],
      "hand": [
        {
          "name": "Strike",
          "cost": 1,
          "type": "ATTACK",
          "is_playable": true,
          "has_target": true
        }
      ],
      "draw_pile": [...],
      "discard_pile": [...],
      "turn": 5
    }
  },
  "available_commands": ["play", "end", "potion"]
}
```

Access fields using nlohmann/json API:

```cpp
auto state = *client.getState();

// Check if in combat
if (state["game_state"]["screen_type"] == "COMBAT") {
    // Access combat state
    auto monsters = state["game_state"]["combat_state"]["monsters"];
    for (const auto& monster : monsters) {
        if (!monster["is_gone"]) {
            std::cout << "Monster: " << monster["name"]
                      << " HP: " << monster["current_hp"] << std::endl;
        }
    }

    // Access hand
    auto hand = state["game_state"]["combat_state"]["hand"];
    for (size_t i = 0; i < hand.size(); ++i) {
        std::cout << "Card " << i << ": " << hand[i]["name"]
                  << " Cost: " << hand[i]["cost"]
                  << " Playable: " << hand[i]["is_playable"] << std::endl;
    }
}
```

## Example Usage Patterns

### Making Combat Decisions

```cpp
auto state = client.getState();
if (!state || !client.isReadyForCommand()) {
    return;
}

auto commands = client.getAvailableCommands();
bool can_play = false;
for (const auto& cmd : commands) {
    if (cmd == "play") {
        can_play = true;
        break;
    }
}

if (can_play) {
    // Play a card
    auto hand = (*state)["game_state"]["combat_state"]["hand"];
    for (size_t i = 0; i < hand.size(); ++i) {
        if (hand[i]["is_playable"]) {
            if (hand[i]["has_target"]) {
                // Target first alive monster
                auto monsters = (*state)["game_state"]["combat_state"]["monsters"];
                for (size_t j = 0; j < monsters.size(); ++j) {
                    if (!monsters[j]["is_gone"] && monsters[j]["current_hp"] > 0) {
                        client.playCard(i, j);
                        return;
                    }
                }
            } else {
                client.playCard(i);
                return;
            }
        }
    }
}

// If can't play, end turn
client.endTurn();
```

### Error Handling

```cpp
spirecomm::SpireCommClient client(config);

if (!client.connect()) {
    std::cerr << "Connection failed: " << client.getLastError() << std::endl;
    return 1;
}

while (true) {
    auto state = client.getState();
    if (!state) {
        std::cerr << "Failed to get state: " << client.getLastError() << std::endl;
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        continue;
    }

    // Process state...
}
```

## Building Your AI

### Integrate into Your Project

**Option 1: Add as subdirectory**

```cmake
# In your CMakeLists.txt
add_subdirectory(external/spirecomm_cpp_client)
target_link_libraries(your_ai PRIVATE spirecomm)
```

**Option 2: Install and use find_package**

```bash
cd cpp_client/build
cmake --install . --prefix /usr/local
```

```cmake
# In your CMakeLists.txt
find_package(spirecomm REQUIRED)
target_link_libraries(your_ai PRIVATE spirecomm)
```

### Example CMakeLists.txt

```cmake
cmake_minimum_required(VERSION 3.14)
project(my_spire_ai)

set(CMAKE_CXX_STANDARD 17)

# Add spirecomm client
add_subdirectory(external/spirecomm_cpp_client)

# Your AI executable
add_executable(my_ai
    src/main.cpp
    src/strategy.cpp
)

target_link_libraries(my_ai PRIVATE spirecomm)
```

## Platform-Specific Notes

### Windows

- Winsock libraries (ws2_32, crypt32) are automatically linked
- Use Visual Studio 2017+ or MinGW-w64
- Paths use backslashes: `.\\build\\bin\\Release\\simple_ai.exe`
- Run from Command Prompt or PowerShell

### Linux

- Install build tools: `sudo apt install build-essential cmake`
- Requires pthreads (usually available by default)

### macOS

- Install Xcode Command Line Tools: `xcode-select --install`
- Or use Homebrew for CMake: `brew install cmake`

## Troubleshooting

### Action queue stuck or not processing

**Problem:** Commands are queued but not executing, or `queue_size` keeps growing
**Symptoms:**
- Health endpoint shows increasing `queue_size`
- `game_ready` remains `false` for extended periods
- Server log shows actions queued but not executed

**Cause:** Invalid or malformed commands can cause Communication Mod to hang, preventing subsequent commands from executing.

**Solution:** Clear the action queue using the `/clear` endpoint:

```bash
# Check queue status
curl http://localhost:8080/health

# Clear stuck queue
curl -X POST http://localhost:8080/clear

# Verify queue cleared
curl http://localhost:8080/health
```

This is primarily a development/debugging tool. In production, validate all commands before sending to avoid queue blocking.

### Linker errors on Windows

**Problem:** Undefined reference to Winsock functions
**Solution:** CMakeLists.txt should link ws2_32 and crypt32 automatically. If not, add:

```cmake
target_link_libraries(your_target PRIVATE ws2_32 crypt32)
```

### CMake can't fetch dependencies

**Problem:** Git or network issues preventing FetchContent
**Solution:** Download headers manually and disable FetchContent:

```bash
cd include/spirecomm
wget https://raw.githubusercontent.com/yhirose/cpp-httplib/v0.14.3/httplib.h
cd ../..
wget https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp
```

### Can't connect to server

**Problem:** Connection refused
**Solution:**
1. Ensure http_server.py is running: `python spirecomm/http_server.py`
2. Check health endpoint: `curl http://localhost:8080/health`
3. Check port matches: `--port 8080`
4. Enable debug logging: `config.debug = true`

### State is always empty

**Problem:** `getState()` returns `std::nullopt`
**Solution:**
1. Game must be started (not at main menu)
2. Check server has state: `curl http://localhost:8080/state`
3. Verify Communication Mod is configured correctly

## Performance

- **HTTP latency**: 1-3ms per request
- **JSON parsing**: 0.1-1ms per state
- **Recommended poll rate**: 50-100ms (10-20 Hz)
- **CPU usage**: Minimal (<1% when idle)

## Dependencies

Auto-downloaded via CMake FetchContent:

- **cpp-httplib** v0.14.3 ([GitHub](https://github.com/yhirose/cpp-httplib)) - MIT License
- **nlohmann/json** v3.11.3 ([GitHub](https://github.com/nlohmann/json)) - MIT License

## See Also

- [HTTP_API.md](../HTTP_API.md) - Complete HTTP API documentation (endpoints, logging, recovery)
- [GAME_STATE_SPECIFICATION.md](../GAME_STATE_SPECIFICATION.md) - Game state structure and action format
- [HTTP Server](../spirecomm/http_server.py) - Python HTTP server implementation
- [Python Client Example](../examples/combat_test_client.py) - Python reference implementation
- [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod) - The underlying mod
- [SpireComm](https://github.com/ForgottenArbiter/spirecomm) - Original Python library

## License

Same as SpireComm (MIT License)
