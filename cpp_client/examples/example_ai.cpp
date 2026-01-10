/**
 * Simple AI Example for SpireComm C++ Client
 *
 * Demonstrates how to use SpireCommClient to interface with Slay the Spire.
 * This AI implements basic logic: always end turn in combat, skip events,
 * and choose the first available option.
 *
 * Usage:
 *   1. Start the game with Communication Mod configured to run http_bridge
 *   2. Run this executable: ./example_ai
 *   3. Watch the AI play!
 */

#include <spirecomm/client.hpp>
#include <nlohmann/json.hpp>
#include <iostream>
#include <thread>
#include <chrono>

using json = nlohmann::json;
using namespace spirecomm;

class SimpleAI {
public:
    SimpleAI(const ClientConfig& config) : client(config) {}

    bool initialize() {
        std::cout << "Connecting to bridge..." << std::endl;
        if (!client.connect()) {
            std::cerr << "Failed to connect: " << client.getLastError() << std::endl;
            return false;
        }

        std::cout << "Waiting for game to start..." << std::endl;
        if (!client.waitForReady(30000)) {
            std::cerr << "Timeout waiting for game: " << client.getLastError() << std::endl;
            return false;
        }

        std::cout << "Connected and ready!" << std::endl;
        return true;
    }

    void run() {
        while (true) {
            // Get latest state
            auto state_opt = client.getState();

            if (!state_opt) {
                // No state available, wait briefly
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                continue;
            }

            // Check if game is ready for command
            if (!client.isReadyForCommand()) {
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                continue;
            }

            // Get state
            auto state = *state_opt;

            // Log current status
            auto screen_type = client.getScreenType();
            auto floor = client.getFloor();
            auto hp = client.getCurrentHP();

            if (screen_type && floor && hp) {
                std::cout << "Floor " << *floor << " | " << *screen_type
                          << " | HP: " << *hp << "/" << *client.getMaxHP() << std::endl;
            }

            // Make decision based on available commands
            if (!state.contains("available_commands")) {
                std::this_thread::sleep_for(std::chrono::milliseconds(50));
                continue;
            }

            auto commands = state["available_commands"];

            // Simple decision logic
            if (hasCommand(commands, "end")) {
                // In combat: end turn
                std::cout << "  -> Ending turn" << std::endl;
                client.sendAction("end");

            } else if (hasCommand(commands, "proceed") || hasCommand(commands, "confirm")) {
                // Proceed to next screen
                std::cout << "  -> Proceeding" << std::endl;
                client.sendAction("proceed");

            } else if (hasCommand(commands, "choose")) {
                // Choose first option (works for events, map, etc.)
                std::cout << "  -> Choosing option 0" << std::endl;
                client.sendAction("choose", 0);

            } else if (hasCommand(commands, "skip")) {
                // Skip (e.g., card rewards)
                std::cout << "  -> Skipping" << std::endl;
                client.sendAction("skip");

            } else if (hasCommand(commands, "leave") || hasCommand(commands, "return")) {
                // Leave/return (e.g., from shop)
                std::cout << "  -> Leaving" << std::endl;
                client.sendAction("leave");

            } else {
                // No known command available
                std::cout << "  -> No known command, waiting..." << std::endl;
            }

            // Wait before next decision
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

private:
    SpireCommClient client;

    bool hasCommand(const json& commands, const std::string& cmd) {
        for (const auto& command : commands) {
            if (command.get<std::string>() == cmd) {
                return true;
            }
        }
        return false;
    }
};

int main(int argc, char* argv[]) {
    // Parse command-line arguments (optional)
    ClientConfig config;
    config.debug = false;  // Set to true for verbose logging

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--debug") {
            config.debug = true;
        } else if (arg == "--port" && i + 1 < argc) {
            config.port = std::stoi(argv[++i]);
        } else if (arg == "--host" && i + 1 < argc) {
            config.host = argv[++i];
        } else if (arg == "--help" || arg == "-h") {
            std::cout << "Usage: " << argv[0] << " [OPTIONS]\n"
                      << "\nOptions:\n"
                      << "  --host HOST    Bridge host (default: 127.0.0.1)\n"
                      << "  --port PORT    Bridge port (default: 8080)\n"
                      << "  --debug        Enable debug logging\n"
                      << "  --help, -h     Show this help message\n";
            return 0;
        }
    }

    std::cout << "SpireComm Simple AI Example\n"
              << "============================\n"
              << "Connecting to " << config.host << ":" << config.port << "\n\n";

    SimpleAI ai(config);

    if (!ai.initialize()) {
        return 1;
    }

    try {
        ai.run();
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }

    return 0;
}
