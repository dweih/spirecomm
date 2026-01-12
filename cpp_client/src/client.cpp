#include "spirecomm/client.hpp"
#include <nlohmann/json.hpp>
#include <httplib.h>
#include <iostream>
#include <sstream>

namespace spirecomm {

using json = nlohmann::json;

// PIMPL implementation
struct SpireCommClient::Impl {
    ClientConfig config;
    std::unique_ptr<httplib::Client> http_client;
    json cached_state;
    bool connected = false;
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

    bool sendAction(const json& action_json) {
        log("Sending action: " + action_json.dump());

        auto res = http_client->Post("/action", action_json.dump(), "application/json");

        if (!res) {
            setError("Failed to send action (no response)");
            return false;
        }

        if (res->status != 200) {
            setError("Send action failed (status " + std::to_string(res->status) + ")");
            if (!res->body.empty()) {
                log("Response body: " + res->body);
            }
            return false;
        }

        log("Action sent successfully");
        return true;
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

// Connect to server
bool SpireCommClient::connect() {
    pImpl->log("Connecting to server at " + pImpl->config.host + ":" + std::to_string(pImpl->config.port));

    auto res = pImpl->http_client->Get("/health");

    if (!res) {
        pImpl->setError("Failed to connect to server (no response)");
        pImpl->connected = false;
        return false;
    }

    if (res->status != 200) {
        pImpl->setError("Health check failed (status " + std::to_string(res->status) + ")");
        pImpl->connected = false;
        return false;
    }

    try {
        json health = json::parse(res->body);
        std::string status = health.value("status", "");
        if (status != "ready") {
            pImpl->setError("Server not ready (status: " + status + ")");
            pImpl->connected = false;
            return false;
        }
    } catch (const json::exception& e) {
        pImpl->setError("Failed to parse health response: " + std::string(e.what()));
        pImpl->connected = false;
        return false;
    }

    pImpl->log("Connected to server successfully");
    pImpl->connected = true;
    return true;
}

// Check if connected
bool SpireCommClient::isConnected() const {
    return pImpl->connected;
}

// Get last error
std::string SpireCommClient::getLastError() const {
    return pImpl->last_error;
}

// Get state from server
std::optional<json> SpireCommClient::getState() {
    auto res = pImpl->http_client->Get("/state");

    if (!res) {
        pImpl->setError("Failed to get state (no response)");
        return std::nullopt;
    }

    if (res->status == 204) {
        // No content - no state available yet
        pImpl->log("No state available yet (204)");
        return std::nullopt;
    }

    if (res->status != 200) {
        pImpl->setError("Get state failed (status " + std::to_string(res->status) + ")");
        return std::nullopt;
    }

    try {
        // Parse full state response
        json state = json::parse(res->body);

        // Update cache
        pImpl->cached_state = state;

        pImpl->log("State retrieved successfully");

        return state;

    } catch (const json::exception& e) {
        pImpl->setError("Failed to parse state JSON: " + std::string(e.what()));
        return std::nullopt;
    }
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

// Helper: get available commands
std::vector<std::string> SpireCommClient::getAvailableCommands() const {
    std::vector<std::string> commands;
    if (pImpl->cached_state.empty()) {
        return commands;
    }
    try {
        if (pImpl->cached_state.contains("available_commands")) {
            for (const auto& cmd : pImpl->cached_state["available_commands"]) {
                commands.push_back(cmd.get<std::string>());
            }
        }
    } catch (...) {
    }
    return commands;
}

// Action: Play card (no target)
bool SpireCommClient::playCard(int card_index) {
    json action = {
        {"type", "play_card"},
        {"card_index", card_index}
    };
    return pImpl->sendAction(action);
}

// Action: Play card (with target)
bool SpireCommClient::playCard(int card_index, int target_index) {
    json action = {
        {"type", "play_card"},
        {"card_index", card_index},
        {"target_index", target_index}
    };
    return pImpl->sendAction(action);
}

// Action: End turn
bool SpireCommClient::endTurn() {
    json action = {
        {"type", "end_turn"}
    };
    return pImpl->sendAction(action);
}

// Action: Use potion (no target)
bool SpireCommClient::usePotion(int potion_index) {
    json action = {
        {"type", "use_potion"},
        {"potion_index", potion_index}
    };
    return pImpl->sendAction(action);
}

// Action: Use potion (with target)
bool SpireCommClient::usePotion(int potion_index, int target_index) {
    json action = {
        {"type", "use_potion"},
        {"potion_index", potion_index},
        {"target_index", target_index}
    };
    return pImpl->sendAction(action);
}

// Action: Discard potion
bool SpireCommClient::discardPotion(int potion_index) {
    json action = {
        {"type", "discard_potion"},
        {"potion_index", potion_index}
    };
    return pImpl->sendAction(action);
}

// Action: Proceed
bool SpireCommClient::proceed() {
    json action = {
        {"type", "proceed"}
    };
    return pImpl->sendAction(action);
}

} // namespace spirecomm
