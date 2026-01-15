#pragma once

#include <memory>
#include <string>
#include <optional>
#include <vector>
#include <nlohmann/json.hpp>

namespace spirecomm {

/**
 * Configuration for SpireCommClient
 */
struct ClientConfig {
    std::string host = "127.0.0.1";  // Server host
    int port = 8080;                  // Server port
    int timeout_ms = 5000;            // HTTP request timeout
    bool debug = false;               // Enable debug logging
};

/**
 * SpireComm HTTP Client
 *
 * Connects to spirecomm/http_server.py and provides high-level API
 * for querying game state and sending actions.
 *
 * Usage:
 *   ClientConfig config;
 *   config.port = 8080;
 *   config.debug = true;
 *
 *   SpireCommClient client(config);
 *
 *   if (client.connect()) {
 *       while (true) {
 *           auto state = client.getState();
 *           if (state && client.isReadyForCommand()) {
 *               client.endTurn();
 *           }
 *           std::this_thread::sleep_for(std::chrono::milliseconds(50));
 *       }
 *   }
 */
class SpireCommClient {
public:
    /**
     * Create client with configuration
     */
    explicit SpireCommClient(const ClientConfig& config = ClientConfig());

    /**
     * Destructor
     */
    ~SpireCommClient();

    // Disable copy (use move if needed)
    SpireCommClient(const SpireCommClient&) = delete;
    SpireCommClient& operator=(const SpireCommClient&) = delete;

    // Enable move
    SpireCommClient(SpireCommClient&&) noexcept;
    SpireCommClient& operator=(SpireCommClient&&) noexcept;

    /**
     * Connect to server and verify it's responding
     * @return true if server is reachable and healthy
     */
    bool connect();

    /**
     * Check if connected to server
     * @return true if last connection attempt succeeded
     */
    bool isConnected() const;

    /**
     * Get last error message
     * @return Error message from last failed operation
     */
    std::string getLastError() const;

    /**
     * Get current game state
     * Returns the full JSON state object from the server.
     * @return Game state JSON if available, empty optional otherwise
     */
    std::optional<nlohmann::json> getState();

    /**
     * Check if currently in game
     * Parses cached state for "in_game" field.
     * @return true if in an active game
     */
    bool isInGame() const;

    /**
     * Check if game is ready for command
     * Parses cached state for "ready_for_command" field.
     * @return true if ready to accept actions
     */
    bool isReadyForCommand() const;

    /**
     * Get list of available commands
     * Parses cached state for "available_commands" field.
     * @return Vector of command names (e.g., ["play", "end", "proceed"])
     */
    std::vector<std::string> getAvailableCommands() const;

    // Type-safe action methods

    /**
     * Play a card from hand (no target required)
     * @param card_index Index of card in hand (0-indexed)
     * @return true if action sent successfully
     */
    bool playCard(int card_index);

    /**
     * Play a card from hand targeting a monster
     * @param card_index Index of card in hand (0-indexed)
     * @param target_index Index of target monster (0-indexed)
     * @return true if action sent successfully
     */
    bool playCard(int card_index, int target_index);

    /**
     * End the current turn
     * @return true if action sent successfully
     */
    bool endTurn();

    /**
     * Use a potion (no target required)
     * @param potion_index Index of potion slot (0-indexed)
     * @return true if action sent successfully
     */
    bool usePotion(int potion_index);

    /**
     * Use a potion targeting a monster
     * @param potion_index Index of potion slot (0-indexed)
     * @param target_index Index of target monster (0-indexed)
     * @return true if action sent successfully
     */
    bool usePotion(int potion_index, int target_index);

    /**
     * Discard a potion
     * @param potion_index Index of potion slot (0-indexed)
     * @return true if action sent successfully
     */
    bool discardPotion(int potion_index);

    /**
     * Proceed to next screen (use for rewards, events, etc.)
     * @return true if action sent successfully
     */
    bool proceed();

    /**
     * Cancel current action or go back
     * @return true if action sent successfully
     */
    bool cancel();

    /**
     * Make a generic choice by index or name
     * @param choice_index Index of choice (0-indexed)
     * @return true if action sent successfully
     */
    bool choose(int choice_index);

    /**
     * Make a generic choice by name
     * @param name Name of choice
     * @return true if action sent successfully
     */
    bool chooseByName(const std::string& name);

    /**
     * Choose a rest site option
     * @param option Rest option ("rest", "smith", "dig", "lift", "recall", "toke")
     * @return true if action sent successfully
     */
    bool rest(const std::string& option);

    /**
     * Choose a card reward or use Singing Bowl
     * @param card_name Name of card to choose (empty to skip)
     * @param bowl If true, use Singing Bowl
     * @return true if action sent successfully
     */
    bool cardReward(const std::string& card_name = "", bool bowl = false);

    /**
     * Choose a combat reward
     * @param reward_index Index into rewards array (0-indexed)
     * @return true if action sent successfully
     */
    bool combatReward(int reward_index);

    /**
     * Choose a boss relic
     * @param relic_name Name of relic to choose
     * @return true if action sent successfully
     */
    bool bossReward(const std::string& relic_name);

    /**
     * Buy a card from the shop
     * @param card_name Name of card to buy
     * @return true if action sent successfully
     */
    bool buyCard(const std::string& card_name);

    /**
     * Buy a relic from the shop
     * @param relic_name Name of relic to buy
     * @return true if action sent successfully
     */
    bool buyRelic(const std::string& relic_name);

    /**
     * Buy a potion from the shop
     * @param potion_name Name of potion to buy
     * @return true if action sent successfully
     */
    bool buyPotion(const std::string& potion_name);

    /**
     * Buy card removal from the shop
     * @param card_name Optional name of card to remove
     * @return true if action sent successfully
     */
    bool buyPurge(const std::string& card_name = "");

    /**
     * Select cards from hand or grid
     * @param card_names List of card names to select
     * @return true if action sent successfully
     */
    bool cardSelect(const std::vector<std::string>& card_names);

    /**
     * Choose a map node by coordinates
     * @param x Node X coordinate
     * @param y Node Y coordinate
     * @return true if action sent successfully
     */
    bool chooseMapNode(int x, int y);

    /**
     * Go to the boss node
     * @return true if action sent successfully
     */
    bool chooseMapBoss();

    /**
     * Open a chest
     * @return true if action sent successfully
     */
    bool openChest();

    /**
     * Choose an event option
     * @param choice_index Index of event option
     * @return true if action sent successfully
     */
    bool eventOption(int choice_index);

    /**
     * Start a new game
     * @param character Character name ("IRONCLAD", "THE_SILENT", "DEFECT", "WATCHER")
     * @param ascension Ascension level (default: 0)
     * @param seed Optional seed string
     * @return true if action sent successfully
     */
    bool startGame(const std::string& character, int ascension = 0, const std::string& seed = "");

private:
    // PIMPL idiom to hide implementation details
    struct Impl;
    std::unique_ptr<Impl> pImpl;
};

} // namespace spirecomm
