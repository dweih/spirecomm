#include "spirecomm/client.hpp"
#include <nlohmann/json.hpp>
#include <httplib.h>
#include <iostream>
#include <sstream>
#include <chrono>
#include <thread>

using json = nlohmann::json;

namespace spirecomm {

// PIMPL implementation
struct SpireCommClient::Impl {
    ClientConfig config;
    std::unique_ptr<httplib::Client> http_client;
    json cached_state;
    double last_timestamp = 0.0;
    int consecutive_failures = 0;
    ConnectionStatus status = ConnectionStatus::DISCONNECTED;
    std::string last_error;

    Impl(const ClientConfig& cfg) : config(cfg) {
        // Create HTTP client
        http_client = std::make_unique<httplib::Client>(
            config.host.c_str(), config.port
        );
        http_client->set_connection_timeout(0, config.timeout_ms * 1000); // sec, usec
        http_client->set_read_timeout(config.timeout_ms / 1000, (config.timeout_ms % 1000) * 1000);
    }

    void log(const std::string& message) {
        if (config.debug) {
            std::cerr << "[CLIENT] " << message << std::endl;
        }
    }

    void setError(const std::string& error) {
        last_error = error;
        log("Error: " + error);
    }

    bool handleFailure(const std::string& error) {
        setError(error);
        consecutive_failures++;
        if (consecutive_failures >= config.max_consecutive_failures) {
            log("Max consecutive failures reached, setting status to DISCONNECTED");
            status = ConnectionStatus::DISCONNECTED;
            return false;
        }
        return true;
    }

    void resetFailures() {
        if (consecutive_failures > 0) {
            consecutive_failures = 0;
            log("Reset failure counter");
        }
    }
};

// Constructor
SpireCommClient::SpireCommClient(const ClientConfig& config)
    : pImpl(std::make_unique<Impl>(config)) {
}

// Destructor
SpireCommClient::~SpireCommClient() = default;

// Move constructor
SpireCommClient::SpireCommClient(SpireCommClient&&) noexcept = default;

// Move assignment
SpireCommClient& SpireCommClient::operator=(SpireCommClient&&) noexcept = default;

// Connect to bridge
bool SpireCommClient::connect() {
    pImpl->log("Connecting to bridge at " + pImpl->config.host + ":" + std::to_string(pImpl->config.port));

    auto res = pImpl->http_client->Get("/health");

    if (!res) {
        pImpl->handleFailure("Failed to connect to bridge (no response)");
        return false;
    }

    if (res->status != 200) {
        pImpl->handleFailure("Bridge health check failed (status " + std::to_string(res->status) + ")");
        return false;
    }

    pImpl->log("Connected to bridge successfully");
    pImpl->status = ConnectionStatus::CONNECTED;
    pImpl->resetFailures();
    return true;
}

// Wait for ready state
bool SpireCommClient::waitForReady(int timeout_ms) {
    pImpl->log("Waiting for ready state (timeout " + std::to_string(timeout_ms) + "ms)");

    auto start = std::chrono::steady_clock::now();
    auto timeout = std::chrono::milliseconds(timeout_ms);

    while (true) {
        auto state = getState();
        if (state && isReadyForCommand()) {
            pImpl->log("Ready state achieved");
            pImpl->status = ConnectionStatus::READY;
            return true;
        }

        // Check timeout
        auto elapsed = std::chrono::steady_clock::now() - start;
        if (elapsed >= timeout) {
            pImpl->setError("Timeout waiting for ready state");
            return false;
        }

        // Sleep briefly before retrying
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
}

// Get state from bridge
std::optional<json> SpireCommClient::getState() {
    auto res = pImpl->http_client->Get("/state");

    if (!res) {
        pImpl->handleFailure("Failed to get state (no response)");
        return std::nullopt;
    }

    if (res->status == 204) {
        // No content - no state available yet
        pImpl->log("No state available yet (204)");
        return std::nullopt;
    }

    if (res->status != 200) {
        pImpl->handleFailure("Get state failed (status " + std::to_string(res->status) + ")");
        return std::nullopt;
    }

    pImpl->resetFailures();

    try {
        // Parse bridge response
        json bridge_response = json::parse(res->body);
        double timestamp = bridge_response["timestamp"];

        // Check if state has changed
        if (timestamp == pImpl->last_timestamp && !pImpl->cached_state.empty()) {
            // Return cached state (unchanged)
            return pImpl->cached_state;
        }

        // Parse state string from bridge
        std::string state_str = bridge_response["state"];
        json state = json::parse(state_str);

        // Update cache
        pImpl->cached_state = state;
        pImpl->last_timestamp = timestamp;

        pImpl->log("State updated (timestamp " + std::to_string(timestamp) + ")");

        return state;

    } catch (const json::exception& e) {
        pImpl->handleFailure("Failed to parse state JSON: " + std::string(e.what()));
        return std::nullopt;
    }
}

// Check if new state available
bool SpireCommClient::hasNewState() {
    auto res = pImpl->http_client->Get("/state");

    if (!res || res->status != 200) {
        return false;
    }

    try {
        json bridge_response = json::parse(res->body);
        double timestamp = bridge_response["timestamp"];
        return timestamp != pImpl->last_timestamp;
    } catch (...) {
        return false;
    }
}

// Send action
bool SpireCommClient::sendAction(const std::string& command) {
    pImpl->log("Sending action: " + command);

    json action_body = {
        {"command", command}
    };

    auto res = pImpl->http_client->Post("/action", action_body.dump(), "application/json");

    if (!res) {
        pImpl->handleFailure("Failed to send action (no response)");
        return false;
    }

    if (res->status != 200) {
        pImpl->handleFailure("Send action failed (status " + std::to_string(res->status) + ")");
        return false;
    }

    pImpl->resetFailures();
    pImpl->log("Action sent successfully");
    return true;
}

// Send action with one argument
bool SpireCommClient::sendAction(const std::string& command, int arg) {
    std::ostringstream oss;
    oss << command << " " << arg;
    return sendAction(oss.str());
}

// Send action with two arguments
bool SpireCommClient::sendAction(const std::string& command, int arg1, int arg2) {
    std::ostringstream oss;
    oss << command << " " << arg1 << " " << arg2;
    return sendAction(oss.str());
}

// Get status
ConnectionStatus SpireCommClient::getStatus() const {
    return pImpl->status;
}

// Get consecutive failures
int SpireCommClient::getConsecutiveFailures() const {
    return pImpl->consecutive_failures;
}

// Get last error
std::string SpireCommClient::getLastError() const {
    return pImpl->last_error;
}

// Helper: is in game
bool SpireCommClient::isInGame() const {
    if (pImpl->cached_state.empty()) {
        return false;
    }
    try {
        return pImpl->cached_state.value("in_game", false);
    } catch (...) {
        return false;
    }
}

// Helper: is ready for command
bool SpireCommClient::isReadyForCommand() const {
    if (pImpl->cached_state.empty()) {
        return false;
    }
    try {
        return pImpl->cached_state.value("ready_for_command", false);
    } catch (...) {
        return false;
    }
}

// Helper: get screen type
std::optional<std::string> SpireCommClient::getScreenType() const {
    if (pImpl->cached_state.empty()) {
        return std::nullopt;
    }
    try {
        if (pImpl->cached_state.contains("game_state") &&
            pImpl->cached_state["game_state"].contains("screen_type")) {
            return pImpl->cached_state["game_state"]["screen_type"].get<std::string>();
        }
    } catch (...) {
    }
    return std::nullopt;
}

// Helper: get current HP
std::optional<int> SpireCommClient::getCurrentHP() const {
    if (pImpl->cached_state.empty()) {
        return std::nullopt;
    }
    try {
        if (pImpl->cached_state.contains("game_state") &&
            pImpl->cached_state["game_state"].contains("current_hp")) {
            return pImpl->cached_state["game_state"]["current_hp"].get<int>();
        }
    } catch (...) {
    }
    return std::nullopt;
}

// Helper: get max HP
std::optional<int> SpireCommClient::getMaxHP() const {
    if (pImpl->cached_state.empty()) {
        return std::nullopt;
    }
    try {
        if (pImpl->cached_state.contains("game_state") &&
            pImpl->cached_state["game_state"].contains("max_hp")) {
            return pImpl->cached_state["game_state"]["max_hp"].get<int>();
        }
    } catch (...) {
    }
    return std::nullopt;
}

// Helper: get floor
std::optional<int> SpireCommClient::getFloor() const {
    if (pImpl->cached_state.empty()) {
        return std::nullopt;
    }
    try {
        if (pImpl->cached_state.contains("game_state") &&
            pImpl->cached_state["game_state"].contains("floor")) {
            return pImpl->cached_state["game_state"]["floor"].get<int>();
        }
    } catch (...) {
    }
    return std::nullopt;
}

// Helper: get act
std::optional<int> SpireCommClient::getAct() const {
    if (pImpl->cached_state.empty()) {
        return std::nullopt;
    }
    try {
        if (pImpl->cached_state.contains("game_state") &&
            pImpl->cached_state["game_state"].contains("act")) {
            return pImpl->cached_state["game_state"]["act"].get<int>();
        }
    } catch (...) {
    }
    return std::nullopt;
}

} // namespace spirecomm
