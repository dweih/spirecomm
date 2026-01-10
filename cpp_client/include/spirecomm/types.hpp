#pragma once

#include <string>

namespace spirecomm {

/**
 * Connection status of the client
 */
enum class ConnectionStatus {
    DISCONNECTED,         // Not connected to bridge
    CONNECTED,            // Connected but no state yet
    WAITING_FOR_STATE,    // Waiting for first game state
    READY                 // Ready to send actions
};

/**
 * Configuration for SpireCommClient
 */
struct ClientConfig {
    std::string host = "127.0.0.1";  // Bridge host
    int port = 8080;                  // Bridge port
    int timeout_ms = 5000;            // HTTP request timeout
    int poll_interval_ms = 50;        // Recommended state polling interval
    int max_consecutive_failures = 10; // Max failures before disconnect
    bool debug = false;               // Enable debug logging
};

} // namespace spirecomm
