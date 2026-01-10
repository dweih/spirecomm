#pragma once

#include "types.hpp"
#include <memory>
#include <string>
#include <optional>

// Forward declare nlohmann::json to avoid exposing it in public header
namespace nlohmann {
    template<typename T = void, typename SFINAE = void>
    class basic_json;
    using json = basic_json<>;
}

namespace spirecomm {

/**
 * SpireComm HTTP Client
 *
 * Connects to the SpireComm HTTP bridge and provides high-level API
 * for querying game state and sending actions.
 *
 * Usage:
 *   ClientConfig config;
 *   config.port = 8080;
 *   SpireCommClient client(config);
 *
 *   if (client.connect()) {
 *       client.waitForReady(30000);
 *       while (true) {
 *           auto state = client.getState();
 *           if (state && client.isReadyForCommand()) {
 *               client.sendAction("end");
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
     * Check bridge health and connectivity
     * @return true if bridge is reachable and healthy
     */
    bool connect();

    /**
     * Wait for first game state to be available
     * @param timeout_ms Maximum time to wait in milliseconds
     * @return true if state became available within timeout
     */
    bool waitForReady(int timeout_ms = 30000);

    /**
     * Poll for latest game state
     * Returns cached state if timestamp unchanged since last call.
     * @return Game state JSON if available, empty optional otherwise
     */
    std::optional<nlohmann::json> getState();

    /**
     * Check if new state is available (timestamp changed)
     * @return true if state has been updated since last getState()
     */
    bool hasNewState();

    /**
     * Send action command to bridge
     * @param command Action command string (e.g., "end", "proceed")
     * @return true if action sent successfully
     */
    bool sendAction(const std::string& command);

    /**
     * Send action with one integer argument
     * @param command Command string (e.g., "play", "choose")
     * @param arg Integer argument (e.g., card index, choice index)
     * @return true if action sent successfully
     */
    bool sendAction(const std::string& command, int arg);

    /**
     * Send action with two integer arguments
     * @param command Command string (e.g., "play", "potion use")
     * @param arg1 First integer argument
     * @param arg2 Second integer argument
     * @return true if action sent successfully
     */
    bool sendAction(const std::string& command, int arg1, int arg2);

    /**
     * Get current connection status
     */
    ConnectionStatus getStatus() const;

    /**
     * Get count of consecutive HTTP failures
     */
    int getConsecutiveFailures() const;

    /**
     * Get last error message
     */
    std::string getLastError() const;

    // Convenience helpers (parse common fields from cached state)

    /**
     * Check if currently in game
     * Parses cached state for "in_game" field.
     */
    bool isInGame() const;

    /**
     * Check if game is ready for command
     * Parses cached state for "ready_for_command" field.
     */
    bool isReadyForCommand() const;

    /**
     * Get current screen type (e.g., "COMBAT", "EVENT", "MAP")
     * Parses cached state for "game_state.screen_type" field.
     */
    std::optional<std::string> getScreenType() const;

    /**
     * Get current HP
     * Parses cached state for "game_state.current_hp" field.
     */
    std::optional<int> getCurrentHP() const;

    /**
     * Get maximum HP
     * Parses cached state for "game_state.max_hp" field.
     */
    std::optional<int> getMaxHP() const;

    /**
     * Get current floor
     * Parses cached state for "game_state.floor" field.
     */
    std::optional<int> getFloor() const;

    /**
     * Get current act
     * Parses cached state for "game_state.act" field.
     */
    std::optional<int> getAct() const;

private:
    // PIMPL idiom to hide implementation details
    struct Impl;
    std::unique_ptr<Impl> pImpl;
};

} // namespace spirecomm
