/**
 * Full Game Random Walk Test for SpireComm C++ Client
 *
 * Tests the HTTP API by playing through a full game with random actions.
 * Supports all screen types: combat, map, events, rewards, shops, rest sites, etc.
 *
 * This version mirrors the Python full_game_test.py structure with a
 * dedicated FullGameClient class for cleaner separation of concerns.
 *
 * Usage:
 *   ./full_game_test [--port 8080] [--host 127.0.0.1] [--verbose] [--character IRONCLAD] [--ascension 0]
 */

#include <spirecomm/client.hpp>
#include <nlohmann/json.hpp>
#include <iostream>
#include <thread>
#include <chrono>
#include <random>
#include <vector>
#include <string>
#include <algorithm>

namespace {
using json = nlohmann::json;
using namespace spirecomm;

// Random number generator
std::random_device rd;
std::mt19937 rng(rd());

template<typename T>
const T& random_choice(const std::vector<T>& vec) {
    std::uniform_int_distribution<size_t> dist(0, vec.size() - 1);
    return vec[dist(rng)];
}

int random_int(int min, int max) {
    std::uniform_int_distribution<int> dist(min, max);
    return dist(rng);
}

double random_float() {
    std::uniform_real_distribution<double> dist(0.0, 1.0);
    return dist(rng);
}

} // anonymous namespace


/**
 * Full Game Client - Plays Slay the Spire randomly
 * Mirrors the Python FullGameClient class structure
 */
class FullGameClient {
public:
    FullGameClient(const std::string& host = "127.0.0.1", int port = 8080, bool verbose = false)
        : client_([&]() {
            ClientConfig cfg;
            cfg.host = host;
            cfg.port = port;
            cfg.debug = verbose;
            return cfg;
        }()),
          verbose_(verbose),
          actions_taken_(0),
          floors_completed_(0),
          leave_shop_flag_(false) {}

    void log(const std::string& message) {
        if (verbose_) {
            std::cout << "[CLIENT] " << message << std::endl;
        }
    }

    void print(const std::string& message) {
        std::cout << message << std::endl;
    }

    bool initialize() {
        print(std::string(60, '='));
        print("Full Game Random Walk Test (C++)");
        print(std::string(60, '='));
        print("Connecting to server...");
        
        if (!client_.connect()) {
            std::cerr << "Failed to connect: " << client_.getLastError() << std::endl;
            return false;
        }

        print("Server connected!");
        return true;
    }

    std::optional<json> getState() {
        return client_.getState();
    }

    bool startGame(const std::string& character = "IRONCLAD", int ascension = 0) {
        print("Starting new game as " + character + " (Ascension " + std::to_string(ascension) + ")...");
        bool success = client_.startGame(character, ascension);
        if (success) actions_taken_++;
        return success;
    }

    bool handleCombat(const json& state) {
        auto game_state = state["game_state"];
        
        // Check for combat_state instead of in_combat
        if (!game_state.contains("combat_state")) {
            return false;
        }
        auto combat_state = game_state["combat_state"];

        auto commands = client_.getAvailableCommands();
        auto hand = combat_state.value("hand", json::array());
        auto monsters = combat_state.value("monsters", json::array());

        // Filter alive monsters
        std::vector<int> alive_monster_indices;
        for (size_t i = 0; i < monsters.size(); i++) {
            auto m = monsters[i];
            if (!m.value("is_gone", false) && !m.value("half_dead", false)) {
                alive_monster_indices.push_back(i);
            }
        }

        // 10% chance to end turn
        if (hasCommand(commands, "end") && random_float() < 0.1) {
            print("  -> Ending turn");
            bool success = client_.endTurn();
            if (success) actions_taken_++;
            return success;
        }

        // Try to play a random playable card
        if (hasCommand(commands, "play") && !hand.empty()) {
            std::vector<int> playable_indices;
            for (size_t i = 0; i < hand.size(); i++) {
                if (hand[i].value("is_playable", false)) {
                    playable_indices.push_back(i);
                }
            }

            if (!playable_indices.empty()) {
                int card_index = random_choice(playable_indices);
                auto card = hand[card_index];
                std::string card_name = card.value("name", "?");

                if (card.value("has_target", false) && !alive_monster_indices.empty()) {
                    int target_index = random_choice(alive_monster_indices);
                    print("  -> Playing " + card_name + " targeting monster " + std::to_string(target_index));
                    bool success = client_.playCard(card_index, target_index);
                    if (success) actions_taken_++;
                    return success;
                } else {
                    print("  -> Playing " + card_name);
                    bool success = client_.playCard(card_index);
                    if (success) actions_taken_++;
                    return success;
                }
            }
        }

        // Can't play cards, end turn
        if (hasCommand(commands, "end")) {
            print("  -> Ending turn (no playable cards)");
            bool success = client_.endTurn();
            if (success) actions_taken_++;
            return success;
        }

        return false;
    }

    bool handleMap(const json& state) {
        auto game_state = state["game_state"];
        auto screen = game_state.value("screen", json::object());
        auto next_nodes = screen.value("next_nodes", json::array());
        bool boss_available = screen.value("boss_available", false);

        // Small chance to go to boss
        if (boss_available && random_float() < 0.2) {
            print("  -> Choosing boss node");
            bool success = client_.chooseMapBoss();
            if (success) actions_taken_++;
            return success;
        }

        // Choose random next node
        if (!next_nodes.empty()) {
            int choice_index = random_int(0, next_nodes.size() - 1);
            auto node = next_nodes[choice_index];
            std::string symbol = node.value("symbol", "?");
            print("  -> Choosing map node " + std::to_string(choice_index) + " to " + symbol);
            bool success = client_.choose(choice_index);
            if (success) actions_taken_++;
            return success;
        }

        return false;
    }

    bool handleCardReward(const json& state) {
        auto game_state = state["game_state"];
        auto screen = game_state.value("screen", json::object());
        auto cards = screen.value("cards", json::array());
        bool can_bowl = screen.value("can_bowl", false);
        bool can_skip = screen.value("can_skip", false);

        // 20% chance to use bowl
        if (can_bowl && random_float() < 0.2) {
            print("  -> Using Singing Bowl");
            bool success = client_.cardReward("", true);
            if (success) actions_taken_++;
            return success;
        }

        // 30% chance to skip
        if (can_skip && random_float() < 0.3) {
            print("  -> Skipping card reward");
            bool success = client_.proceed();
            if (success) actions_taken_++;
            return success;
        }

        // Choose random card
        if (!cards.empty()) {
            std::vector<json> cards_vec(cards.begin(), cards.end());
            auto card = random_choice(cards_vec);
            std::string card_name = card["name"];
            print("  -> Choosing card: " + card_name);
            bool success = client_.cardReward(card_name);
            if (success) actions_taken_++;
            return success;
        }

        return false;
    }

    bool handleCombatReward(const json& state) {
        auto game_state = state["game_state"];
        auto screen = game_state.value("screen", json::object());
        auto rewards = screen.value("rewards", json::array());

        if (rewards.empty()) {
            print("  -> No rewards left, proceeding");
            bool success = client_.proceed();
            if (success) actions_taken_++;
            return success;
        }

        int reward_index = random_int(0, rewards.size() - 1);
        auto reward = rewards[reward_index];
        std::string reward_type = reward["reward_type"];
        print("  -> Choosing reward " + std::to_string(reward_index) + ": " + reward_type);
        bool success = client_.combatReward(reward_index);
        if (success) actions_taken_++;
        return success;
    }

    bool handleBossReward(const json& state) {
        auto game_state = state["game_state"];
        auto screen = game_state.value("screen", json::object());
        auto relics = screen.value("relics", json::array());

        if (!relics.empty()) {
            std::vector<json> relics_vec(relics.begin(), relics.end());
            auto relic = random_choice(relics_vec);
            std::string relic_name = relic["name"];
            print("  -> Choosing boss relic: " + relic_name);
            bool success = client_.bossReward(relic_name);
            if (success) actions_taken_++;
            return success;
        }

        return false;
    }

    bool handleRest(const json& state) {
        auto game_state = state["game_state"];
        auto screen = game_state.value("screen", json::object());
        auto rest_options = screen.value("rest_options", json::array());
        bool has_rested = screen.value("has_rested", false);

        if (has_rested || rest_options.empty()) {
            print("  -> Already rested, proceeding");
            bool success = client_.proceed();
            if (success) actions_taken_++;
            return success;
        }

        // Choose random rest option
        std::vector<std::string> options_vec;
        for (const auto& opt : rest_options) {
            options_vec.push_back(opt.get<std::string>());
        }
        std::string option = random_choice(options_vec);
        std::transform(option.begin(), option.end(), option.begin(), ::tolower);
        print("  -> Choosing rest option: " + option);
        bool success = client_.rest(option);
        if (success) actions_taken_++;
        return success;
    }

    bool handleShopRoom(const json& state) {
        if (leave_shop_flag_) {
            print("  -> Leaving shop");
            leave_shop_flag_ = false;
            bool success = client_.proceed();
            if (success) actions_taken_++;
            return success;
        }
        print("  -> Entering shop");
        bool success = client_.chooseByName("shop");
        if (success) actions_taken_++;
        return success;
    }

    bool handleShop(const json& state) {
        auto game_state = state["game_state"];
        auto screen = game_state.value("screen", json::object());
        int gold = game_state.value("gold", 0);

        // 50% chance to leave immediately
        if (random_float() < 0.5) {
            print("  -> Leaving shop");
            leave_shop_flag_ = true;
            bool success = client_.cancel();
            if (success) actions_taken_++;
            return success;
        }

        // Try to buy something
        std::vector<std::pair<std::string, json>> buyable_items;

        for (const auto& card : screen.value("cards", json::array())) {
            if (card.value("price", 999) <= gold) {
                buyable_items.push_back({"card", card});
            }
        }

        for (const auto& relic : screen.value("relics", json::array())) {
            if (relic.value("price", 999) <= gold) {
                buyable_items.push_back({"relic", relic});
            }
        }

        for (const auto& potion : screen.value("potions", json::array())) {
            if (potion.value("price", 999) <= gold) {
                buyable_items.push_back({"potion", potion});
            }
        }

        if (screen.value("purge_available", false)) {
            int purge_cost = screen.value("purge_cost", 75);
            if (purge_cost <= gold) {
                json purge_item = {{"price", purge_cost}};
                buyable_items.push_back({"purge", purge_item});
            }
        }

        if (!buyable_items.empty()) {
            auto [item_type, item] = random_choice(buyable_items);

            if (item_type == "card") {
                std::string name = item["name"];
                int price = item["price"];
                print("  -> Buying card: " + name + " for " + std::to_string(price) + " gold");
                bool success = client_.buyCard(name);
                if (success) actions_taken_++;
                return success;
            } else if (item_type == "relic") {
                std::string name = item["name"];
                int price = item["price"];
                print("  -> Buying relic: " + name + " for " + std::to_string(price) + " gold");
                bool success = client_.buyRelic(name);
                if (success) actions_taken_++;
                return success;
            } else if (item_type == "potion") {
                std::string name = item["name"];
                int price = item["price"];
                print("  -> Buying potion: " + name + " for " + std::to_string(price) + " gold");
                bool success = client_.buyPotion(name);
                if (success) actions_taken_++;
                return success;
            } else if (item_type == "purge") {
                int price = item["price"];
                print("  -> Buying card removal for " + std::to_string(price) + " gold");
                bool success = client_.buyPurge();
                if (success) actions_taken_++;
                return success;
            }
        } else {
            print("  -> Can't afford anything, leaving shop");
            leave_shop_flag_ = true;
            bool success = client_.cancel();
            if (success) actions_taken_++;
            return success;
        }

        return false;
    }

    bool handleEvent(const json& state) {
        auto game_state = state["game_state"];
        auto screen = game_state.value("screen", json::object());
        auto options = screen.value("options", json::array());
        std::string event_name = screen.value("event_name", "Unknown Event");

        // Filter enabled options
        std::vector<json> enabled_options;
        for (const auto& opt : options) {
            if (!opt.value("disabled", false)) {
                enabled_options.push_back(opt);
            }
        }

        if (!enabled_options.empty()) {
            auto option = random_choice(enabled_options);
            int choice_index = option.value("choice_index", 0);
            std::string label = option.value("label", "?");
            print("  -> Event '" + event_name + "': choosing option " + std::to_string(choice_index) + " (" + label + ")");
            bool success = client_.eventOption(choice_index);
            if (success) actions_taken_++;
            return success;
        }

        return false;
    }

    bool handleChest(const json& state) {
        auto game_state = state["game_state"];
        auto screen = game_state.value("screen", json::object());
        bool chest_open = screen.value("chest_open", false);

        if (chest_open) {
            print("  -> Chest already open, proceeding");
            bool success = client_.proceed();
            if (success) actions_taken_++;
            return success;
        } else {
            print("  -> Opening chest");
            bool success = client_.openChest();
            if (success) actions_taken_++;
            return success;
        }
    }

    bool handleGridSelect(const json& state) {
        auto game_state = state["game_state"];
        auto screen = game_state.value("screen", json::object());
        auto cards = screen.value("cards", json::array());
        auto selected_cards = screen.value("selected_cards", json::array());
        int num_cards = screen.value("num_cards", 1);
        bool any_number = screen.value("any_number", false);
        bool can_pick_zero = screen.value("can_pick_zero", false);

        int num_selected = selected_cards.size();
        int num_remaining = num_cards - num_selected;

        // If enough selected, or randomly skip
        if (num_remaining <= 0 || (can_pick_zero && random_float() < 0.3)) {
            print("  -> Confirming card selection");
            bool success = client_.proceed();
            if (success) actions_taken_++;
            return success;
        }

        // Build list of available cards (not already selected)
        std::vector<json> available_cards;
        for (const auto& card : cards) {
            bool is_selected = false;
            for (const auto& sel : selected_cards) {
                if (card["name"] == sel["name"]) {
                    is_selected = true;
                    break;
                }
            }
            if (!is_selected) {
                available_cards.push_back(card);
            }
        }

        if (available_cards.empty()) {
            print("  -> No more cards available, confirming");
            bool success = client_.proceed();
            if (success) actions_taken_++;
            return success;
        }

        // Select 1 to num_remaining cards
        int num_to_select = any_number ?
            random_int(1, std::min(num_remaining, (int)available_cards.size())) :
            std::min(num_remaining, (int)available_cards.size());

        std::vector<std::string> card_names;
        std::shuffle(available_cards.begin(), available_cards.end(), rng);

        for (int i = 0; i < num_to_select && i < available_cards.size(); i++) {
            card_names.push_back(available_cards[i]["name"]);
        }

        print("  -> Selecting " + std::to_string(card_names.size()) + " cards");
        bool success = client_.cardSelect(card_names);
        if (success) actions_taken_++;
        return success;
    }

    bool run(const std::string& character = "IRONCLAD", int ascension = 0) {
        print("Checking server connection...");
        
        for (int attempt = 0; attempt < 10; attempt++) {
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
            auto state = getState();
            if (state) {
                print("Server is responsive!");
                break;
            }
            if (attempt == 9) {
                std::cerr << "Server not responding after 10 attempts" << std::endl;
                return false;
            }
        }

        print("\nChecking current game state...");
        std::this_thread::sleep_for(std::chrono::seconds(1));

        auto state = getState();
        if (state && state->value("in_game", false)) {
            print("Already in a game, continuing from current state...");
        } else {
            print("Not in game, starting new game...");
            if (!startGame(character, ascension)) {
                std::cerr << "Failed to start game" << std::endl;
                return false;
            }
            std::this_thread::sleep_for(std::chrono::seconds(2));
        }

        // Main game loop
        int consecutive_failures = 0;
        const int max_failures = 100;

        while (consecutive_failures < max_failures) {
            auto state_opt = getState();
            if (!state_opt) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                continue;
            }

            auto state = *state_opt;

            if (!state.value("ready_for_command", false)) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                continue;
            }

            if (!state.value("in_game", false)) {
                std::this_thread::sleep_for(std::chrono::milliseconds(100));
                continue;
            }

            auto game_state = state["game_state"];
            std::string screen_type = game_state.value("screen_type", "NONE");
            std::string room_type = game_state.value("room_type", "NONE");
            std::string room_phase = game_state.value("room_phase", "INCOMPLETE");

            // Track floor progression
            int floor = game_state.value("floor", 0);
            if (floor > floors_completed_) {
                floors_completed_ = floor;
                int act = game_state.value("act", 0);
                int current_hp = game_state.value("current_hp", 0);
                int max_hp = game_state.value("max_hp", 0);
                int gold = game_state.value("gold", 0);

                print("\n" + std::string(60, '='));
                print("Floor " + std::to_string(floor) + " | Act " + std::to_string(act) +
                      " | HP: " + std::to_string(current_hp) + "/" + std::to_string(max_hp) +
                      " | Gold: " + std::to_string(gold));
                print("Screen: " + screen_type +
                      " | Room: " + room_type + 
                      " | Phase: " + room_phase);
                print(std::string(60, '='));
            }

            // Handle game over
            if (screen_type == "GAME_OVER") {
                auto screen = game_state.value("screen", json::object());
                bool victory = screen.value("victory", false);
                int score = screen.value("score", 0);

                print("\n" + std::string(60, '='));
                print("GAME OVER - " + std::string(victory ? "VICTORY!" : "Defeat"));
                print("Score: " + std::to_string(score));
                print("Actions taken: " + std::to_string(actions_taken_));
                print("Floors completed: " + std::to_string(floors_completed_));
                print(std::string(60, '='));
                break;
            }

            if (screen_type == "COMPLETE") {
                print("\nRun complete!");
                break;
            }

            // Handle screen
            bool success = false;

            // Check for combat using room_type and room_phase (like Python version)
            if ((room_type == "MonsterRoom" || room_type == "MonsterEliteRoom" || room_type == "MonsterBossRoom") 
                && room_phase == "COMBAT") {
                success = handleCombat(state);
            } else if (screen_type == "MAP") {
                success = handleMap(state);
            } else if (screen_type == "CARD_REWARD") {
                success = handleCardReward(state);
            } else if (screen_type == "COMBAT_REWARD") {
                success = handleCombatReward(state);
            } else if (screen_type == "BOSS_REWARD") {
                success = handleBossReward(state);
            } else if (screen_type == "REST") {
                success = handleRest(state);
            } else if (screen_type == "SHOP_ROOM") {
                success = handleShopRoom(state);
            } else if (screen_type == "SHOP_SCREEN") {
                success = handleShop(state);
            } else if (screen_type == "EVENT") {
                success = handleEvent(state);
            } else if (screen_type == "CHEST") {
                success = handleChest(state);
            } else if (screen_type == "GRID" || screen_type == "HAND_SELECT") {
                success = handleGridSelect(state);
            } else {
                log("Unknown screen type: " + screen_type);
            }

            if (success) {
                consecutive_failures = 0;
                std::this_thread::sleep_for(std::chrono::milliseconds(200));
            } else {
                consecutive_failures++;
                std::this_thread::sleep_for(std::chrono::milliseconds(500));
            }
        }

        if (consecutive_failures >= max_failures) {
            std::cerr << "\nERROR: " << max_failures << " consecutive action failures, stopping test" << std::endl;
            return false;
        }

        print("\nTest completed successfully!");
        return true;
    }

private:
    SpireCommClient client_;
    bool verbose_;
    int actions_taken_;
    int floors_completed_;
    bool leave_shop_flag_;

    bool hasCommand(const std::vector<std::string>& commands, const std::string& cmd) {
        return std::find(commands.begin(), commands.end(), cmd) != commands.end();
    }
};


int main(int argc, char* argv[]) {
    // Parse command-line arguments
    std::string host = "127.0.0.1";
    int port = 8080;
    bool verbose = false;
    std::string character = "IRONCLAD";
    int ascension = 0;

    for (int i = 1; i < argc; i++) {
        std::string arg = argv[i];
        if (arg == "--host" && i + 1 < argc) {
            host = argv[++i];
        } else if (arg == "--port" && i + 1 < argc) {
            port = std::stoi(argv[++i]);
        } else if (arg == "--verbose") {
            verbose = true;
        } else if (arg == "--character" && i + 1 < argc) {
            character = argv[++i];
        } else if (arg == "--ascension" && i + 1 < argc) {
            ascension = std::stoi(argv[++i]);
        } else if (arg == "--help" || arg == "-h") {
            std::cout << "Usage: " << argv[0] << " [OPTIONS]\n"
                      << "\nOptions:\n"
                      << "  --host HOST           Server host (default: 127.0.0.1)\n"
                      << "  --port PORT           Server port (default: 8080)\n"
                      << "  --verbose             Enable verbose logging\n"
                      << "  --character CHAR      Character (IRONCLAD, THE_SILENT, DEFECT, WATCHER)\n"
                      << "  --ascension LEVEL     Ascension level 0-20 (default: 0)\n"
                      << "  --help, -h            Show this help message\n";
            return 0;
        }
    }

    FullGameClient client(host, port, verbose);

    if (!client.initialize()) {
        return 1;
    }

    bool success = client.run(character, ascension);
    return success ? 0 : 1;
}
