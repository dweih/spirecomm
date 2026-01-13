/**
 * Simple AI Example for SpireComm C++ Client
 *
 * Demonstrates how to use SpireCommClient to interface with Slay the Spire.
 * This AI implements basic random combat logic: randomly plays playable cards
 * or ends turn, and proceeds through other screens.
 *
 * Usage:
 *   1. Start Slay the Spire with Communication Mod configured to run http_server.py
 *   2. Run this executable: ./simple_ai
 *   3. Start a run in the game
 *   4. Watch the AI play!
 */

#include <spirecomm/client.hpp>
#include <nlohmann/json.hpp>
#include <iostream>
#include <thread>
#include <chrono>
#include <random>

namespace {
using json = nlohmann::json;
using namespace spirecomm;
} // anonymous namespace

class SimpleAI {
public:
    SimpleAI(const ClientConfig& config) : client(config), rng(std::random_device{}()) {}

    bool initialize() {
        std::cout << "Connecting to server..." << std::endl;
        if (!client.connect()) {
            std::cerr << "Failed to connect: " << client.getLastError() << std::endl;
            return false;
        }

        std::cout << "Connected! Waiting for game to start..." << std::endl;
        std::cout << "Please start a run in Slay the Spire." << std::endl;
        std::cout << std::string(60, '=') << std::endl;
        return true;
    }

    void run() {
        while (true) {
            // Get latest state
            auto state_opt = client.getState();

            if (!state_opt) {
                // No state available, wait briefly
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
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
            logStatus(state);

            // Make decision based on available commands
            auto commands = client.getAvailableCommands();

            if (hasCommand(commands, "play")) {
                // In combat - random card play
                if (makeRandomCombatDecision(state)) {
                    // Made a move, continue
                    std::this_thread::sleep_for(std::chrono::milliseconds(100));
                    continue;
                }
            }

            // Default actions for non-combat screens
            if (hasCommand(commands, "end")) {
                // End turn in combat
                std::cout << "  -> Ending turn" << std::endl;
                client.endTurn();

            } else if (hasCommand(commands, "proceed")) {
                // Proceed to next screen
                std::cout << "  -> Proceeding" << std::endl;
                client.proceed();

            } else {
                // No known command available, just wait
                std::cout << "  -> Waiting (no action available)" << std::endl;
            }

            // Wait before next decision
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
        }
    }

private:
    SpireCommClient client;
    std::mt19937 rng;

    void logStatus(const json& state) {
        try {
            if (state.contains("game_state")) {
                auto game_state = state["game_state"];
                int floor = game_state.value("floor", 0);
                int hp = game_state.value("current_hp", 0);
                int max_hp = game_state.value("max_hp", 0);
                std::string screen_type = game_state.value("screen_type", "UNKNOWN");

                std::cout << "Floor " << floor << " | " << screen_type
                          << " | HP: " << hp << "/" << max_hp << std::endl;
            }
        } catch (...) {
            // Ignore logging errors
        }
    }

    bool hasCommand(const std::vector<std::string>& commands, const std::string& cmd) {
        for (const auto& command : commands) {
            if (command == cmd) {
                return true;
            }
        }
        return false;
    }

    bool makeRandomCombatDecision(const json& state) {
        try {
            // Check if we have combat state
            if (!state.contains("game_state") ||
                !state["game_state"].contains("combat_state")) {
                return false;
            }

            auto combat_state = state["game_state"]["combat_state"];
            auto hand = combat_state["hand"];

            // 70% chance to play a card, 30% chance to end turn
            std::uniform_real_distribution<> dist(0.0, 1.0);
            if (dist(rng) > 0.7) {
                return false; // End turn instead
            }

            // Find playable cards
            std::vector<int> playable_indices;
            for (size_t i = 0; i < hand.size(); ++i) {
                if (hand[i].value("is_playable", false)) {
                    playable_indices.push_back(static_cast<int>(i));
                }
            }

            if (playable_indices.empty()) {
                return false; // No playable cards
            }

            // Pick random playable card
            std::uniform_int_distribution<> card_dist(0, static_cast<int>(playable_indices.size()) - 1);
            int card_index = playable_indices[card_dist(rng)];
            auto card = hand[card_index];
            std::string card_name = card.value("name", "Unknown");

            // Check if card needs target
            if (card.value("has_target", false)) {
                // Find alive monsters
                auto monsters = combat_state["monsters"];
                std::vector<int> alive_indices;

                for (size_t i = 0; i < monsters.size(); ++i) {
                    if (!monsters[i].value("is_gone", false) &&
                        monsters[i].value("current_hp", 0) > 0) {
                        alive_indices.push_back(static_cast<int>(i));
                    }
                }

                if (alive_indices.empty()) {
                    return false; // No valid targets
                }

                // Pick random target
                std::uniform_int_distribution<> target_dist(0, static_cast<int>(alive_indices.size()) - 1);
                int target_index = alive_indices[target_dist(rng)];

                std::cout << "  -> Playing " << card_name << " (card #" << card_index
                          << ") -> Monster " << target_index << std::endl;
                client.playCard(card_index, target_index);
                return true;

            } else {
                // No target needed
                std::cout << "  -> Playing " << card_name << " (card #" << card_index << ")" << std::endl;
                client.playCard(card_index);
                return true;
            }

        } catch (const json::exception& e) {
            std::cerr << "Error making combat decision: " << e.what() << std::endl;
            return false;
        }
    }
};

int main(int argc, char* argv[]) {
    // Parse command-line arguments
    ClientConfig config;
    config.debug = false;

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
                      << "  --host HOST    Server host (default: 127.0.0.1)\n"
                      << "  --port PORT    Server port (default: 8080)\n"
                      << "  --debug        Enable debug logging\n"
                      << "  --help, -h     Show this help message\n";
            return 0;
        }
    }

    std::cout << "\n" << std::string(60, '=') << "\n"
              << "SpireComm Simple AI Example\n"
              << std::string(60, '=') << "\n"
              << "Connecting to http://" << config.host << ":" << config.port << "\n"
              << std::string(60, '=') << "\n" << std::endl;

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
