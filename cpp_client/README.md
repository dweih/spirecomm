# SpireComm C++ Client

C++ client library for interfacing with Slay the Spire via the SpireComm HTTP bridge.

## Overview

The C++ client provides a high-level API for connecting to the SpireComm HTTP bridge, querying game state, and sending actions. Features include:

- **Header-only dependencies**: cpp-httplib and nlohmann/json (auto-downloaded via CMake)
- **PIMPL design**: Clean public interface, hidden implementation details
- **Synchronous API**: Simple poll-based architecture (no threading complexity)
- **Error handling**: Automatic retry logic with failure tracking
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

```bash
# Linux/Mac
./build/bin/example_ai

# Windows
.\build\bin\Release\example_ai.exe
```

Make sure the HTTP bridge is running first! See [../http_bridge/README.md](../http_bridge/README.md).

### 3. Minimal Example

```cpp
#include <spirecomm/client.hpp>
#include <iostream>
#include <thread>

int main() {
    spirecomm::ClientConfig config;
    config.port = 8080;
    config.debug = false;

    spirecomm::SpireCommClient client(config);

    // Connect to bridge
    if (!client.connect()) {
        std::cerr << "Failed to connect: " << client.getLastError() << std::endl;
        return 1;
    }

    // Wait for game to start
    if (!client.waitForReady(30000)) {
        std::cerr << "Timeout: " << client.getLastError() << std::endl;
        return 1;
    }

    // Main game loop
    while (true) {
        auto state = client.getState();

        if (state && client.isReadyForCommand()) {
            // Make decision
            auto screen = client.getScreenType();
            if (screen == "COMBAT") {
                client.sendAction("end");  // End turn
            } else if (screen == "MAP") {
                client.sendAction("choose", 0);  // Pick first node
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
    std::string host = "127.0.0.1";  // Bridge host
    int port = 8080;                  // Bridge port
    int timeout_ms = 5000;            // HTTP request timeout
    int poll_interval_ms = 50;        // Recommended polling interval
    int max_consecutive_failures = 10; // Max failures before disconnect
    bool debug = false;               // Enable debug logging
};
```

### SpireCommClient

Main client class for communicating with the bridge.

#### Constructor

```cpp
SpireCommClient(const ClientConfig& config = ClientConfig());
```

#### Connection Methods

```cpp
// Check bridge health and connectivity
bool connect();

// Wait for first game state (timeout in ms)
bool waitForReady(int timeout_ms = 30000);
```

#### State Methods

```cpp
// Get latest game state (returns nlohmann::json)
std::optional<nlohmann::json> getState();

// Check if state has been updated since last getState()
bool hasNewState();
```

#### Action Methods

```cpp
// Send action command (e.g., "end", "proceed")
bool sendAction(const std::string& command);

// Send action with one argument (e.g., "play 1", "choose 0")
bool sendAction(const std::string& command, int arg);

// Send action with two arguments (e.g., "play 2 0" = play card 2 target monster 0)
bool sendAction(const std::string& command, int arg1, int arg2);
```

**Common Actions:**
- `sendAction("end")` - End turn
- `sendAction("proceed")` - Proceed to next screen
- `sendAction("play", 1)` - Play card at hand position 1 (1-indexed!)
- `sendAction("play", 2, 0)` - Play card 2, target monster 0 (0-indexed)
- `sendAction("choose", 0)` - Choose option 0
- `sendAction("potion use", 0)` - Use potion at slot 0

#### Status Methods

```cpp
// Get current connection status
ConnectionStatus getStatus() const;

// Get count of consecutive HTTP failures
int getConsecutiveFailures() const;

// Get last error message
std::string getLastError() const;
```

#### Helper Methods

Convenience methods that parse common fields from cached state:

```cpp
bool isInGame() const;                       // Parse "in_game" field
bool isReadyForCommand() const;              // Parse "ready_for_command" field
std::optional<std::string> getScreenType() const; // Parse "game_state.screen_type"
std::optional<int> getCurrentHP() const;     // Parse "game_state.current_hp"
std::optional<int> getMaxHP() const;         // Parse "game_state.max_hp"
std::optional<int> getFloor() const;         // Parse "game_state.floor"
std::optional<int> getAct() const;           // Parse "game_state.act"
```

## State JSON Structure

The `getState()` method returns a `nlohmann::json` object with the following structure:

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
          "move_base_damage": 11
        }
      ],
      "hand": [...],
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
        std::cout << "Monster: " << monster["name"]
                  << " HP: " << monster["current_hp"] << std::endl;
    }

    // Access hand
    auto hand = state["game_state"]["combat_state"]["hand"];
    for (const auto& card : hand) {
        std::cout << "Card: " << card["name"]
                  << " Cost: " << card["cost"] << std::endl;
    }
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
    src/mcts.cpp
)

target_link_libraries(my_ai PRIVATE spirecomm)
```

## Advanced Usage

### Accessing Raw JSON State

```cpp
auto state_opt = client.getState();
if (state_opt) {
    auto state = *state_opt;

    // Full JSON access with nlohmann/json
    if (state.contains("game_state") &&
        state["game_state"].contains("combat_state")) {

        auto combat = state["game_state"]["combat_state"];

        // Iterate monsters
        for (const auto& monster : combat["monsters"]) {
            if (!monster["is_gone"] && monster["current_hp"] > 0) {
                std::cout << monster["name"] << ": "
                          << monster["current_hp"] << " HP, "
                          << "Intent: " << monster["intent"] << std::endl;
            }
        }

        // Check player state
        auto player = combat["player"];
        std::cout << "Player: " << player["current_hp"] << " HP, "
                  << player["energy"] << " energy, "
                  << player["block"] << " block" << std::endl;
    }
}
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
        // Check failure count
        if (client.getConsecutiveFailures() >= 5) {
            std::cerr << "Too many failures, reconnecting..." << std::endl;
            if (!client.connect()) {
                std::cerr << "Reconnection failed!" << std::endl;
                break;
            }
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        continue;
    }

    // Process state...
}
```

### Custom Polling Loop

```cpp
#include <chrono>

auto last_poll = std::chrono::steady_clock::now();
const auto poll_interval = std::chrono::milliseconds(50);

while (true) {
    auto now = std::chrono::steady_clock::now();

    if (now - last_poll >= poll_interval) {
        auto state = client.getState();
        // Process state...

        last_poll = now;
    }

    // Do other work (MCTS, neural network inference, etc.)
    compute_next_move();
}
```

## Testing

### Test Against Fixtures

Use the bridge's fixture replay for testing without the game:

```bash
# Terminal 1: Start fixture replay
cd ../http_bridge
python test_bridge.py fixtures/sample --delay-ms 100

# Terminal 2: Run your AI
cd cpp_client/build/bin
./example_ai
```

### Unit Tests

Enable tests during build:

```bash
cmake -B build -DBUILD_TESTS=ON
cmake --build build
cd build && ctest
```

## Platform-Specific Notes

### Windows

- Winsock libraries (ws2_32, crypt32) are automatically linked
- Use Visual Studio 2017+ or MinGW-w64
- Paths use backslashes: `.\\build\\bin\\Release\\example_ai.exe`

### Linux

- Install build tools: `sudo apt install build-essential cmake`
- Requires pthreads (usually available by default)

### macOS

- Install Xcode Command Line Tools: `xcode-select --install`
- Or use Homebrew for CMake: `brew install cmake`

## Troubleshooting

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
cd include
wget https://raw.githubusercontent.com/yhirose/cpp-httplib/v0.14.3/httplib.h
wget https://github.com/nlohmann/json/releases/download/v3.11.3/json.hpp
```

### Can't connect to bridge

**Problem:** Connection refused
**Solution:**
1. Ensure bridge is running: `curl http://localhost:8080/health`
2. Check port matches: `--port 8080`
3. Enable debug logging: `config.debug = true`

### State is always empty

**Problem:** `getState()` returns `std::nullopt`
**Solution:**
1. Game must be started (not at main menu)
2. Wait for ready: `client.waitForReady(30000)`
3. Check bridge has state: `curl http://localhost:8080/state`

## Performance

- **HTTP latency**: 1-3ms per request
- **JSON parsing**: 0.1-1ms per state
- **Recommended poll rate**: 50ms (20 Hz)
- **CPU usage**: Minimal (<1% when idle)

## Dependencies

Auto-downloaded via CMake FetchContent:

- **cpp-httplib** v0.14.3 ([GitHub](https://github.com/yhirose/cpp-httplib)) - MIT License
- **nlohmann/json** v3.11.3 ([GitHub](https://github.com/nlohmann/json)) - MIT License

## Contributing

Found a bug? Have a feature request? Please open an issue or submit a pull request!

## License

Same as SpireComm (MIT License)

## See Also

- [HTTP Bridge](../http_bridge/README.md) - Python bridge documentation
- [Communication Mod](https://github.com/ForgottenArbiter/CommunicationMod) - The underlying mod
- [SpireComm](https://github.com/ForgottenArbiter/spirecomm) - Original Python library
