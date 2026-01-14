#!/usr/bin/env python3
"""
SpireComm HTTP Server - REST API for controlling Slay the Spire

Wraps the Coordinator with an HTTP interface, providing endpoints for
querying game state and sending actions.

Usage:
    python -m spirecomm.http_server [--port PORT] [--host HOST] [--debug] [--log-file FILE]

Endpoints:
    GET  /health  - Health check and queue status
    GET  /state   - Current game state
    POST /action  - Queue an action
    POST /clear   - Clear action queue

For complete API documentation, see HTTP_API.md
"""

import json
import logging
import sys
import threading
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

from spirecomm.communication.action_factory import action_from_json
from spirecomm.communication.coordinator import Coordinator

# Global logger
logger = None


def setup_logger(log_file=None, debug=False):
    """Setup file-based logger for both http_server and coordinator"""
    global logger

    # Default log file location
    if log_file is None:
        log_file = f'spirecomm_server_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'

    # Formatter
    formatter = logging.Formatter('%(asctime)s [%(name)s] [%(levelname)s] %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')

    # File handler (shared by all loggers)
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    file_handler.setFormatter(formatter)

    # Console handler (for initial startup messages)
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Configure http_server logger
    logger = logging.getLogger('spirecomm.http_server')
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.handlers = []
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    # Configure coordinator logger
    coord_logger = logging.getLogger('spirecomm.coordinator')
    coord_logger.setLevel(logging.DEBUG if debug else logging.INFO)
    coord_logger.handlers = []
    coord_logger.addHandler(file_handler)
    # No console handler for coordinator to reduce noise

    logger.info(f"SpireComm HTTP Server starting. Logging to: {log_file}")
    return log_file


# ThreadingHTTPServer for Python 3.7+, manual implementation for older versions
try:
    from http.server import ThreadingHTTPServer
except ImportError:
    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True


class SpireCommHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler with access to SpireComm coordinator"""

    def log_message(self, format, *args):
        """Suppress default HTTP logging unless debug enabled"""
        if self.server.debug:
            super().log_message(format, *args)

    def _send_json_response(self, status_code, data):
        """Send JSON response with proper headers"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_GET(self):
        """Handle GET requests"""
        coordinator = self.server.coordinator

        if self.path == '/health':
            # Health check
            self._send_json_response(200, {
                'status': 'ready',
                'in_game': coordinator.in_game,
                'game_ready': coordinator.game_is_ready,
                'has_state': coordinator.last_game_state is not None,
                'queue_size': len(coordinator.action_queue)
            })

        elif self.path == '/state':
            # Get current game state
            game_state = coordinator.last_game_state

            if game_state is None:
                # No state available yet
                self._send_json_response(204, {})
            else:
                # Serialize game state
                response = {
                    'in_game': coordinator.in_game,
                    'ready_for_command': coordinator.game_is_ready,
                    'game_state': game_state.to_json()
                }

                # Add available commands
                available_commands = []
                if game_state.play_available:
                    available_commands.append('play')
                if game_state.end_available:
                    available_commands.append('end')
                if game_state.potion_available:
                    available_commands.append('potion')
                if game_state.proceed_available:
                    available_commands.append('proceed')
                if game_state.cancel_available:
                    available_commands.append('cancel')

                response['available_commands'] = available_commands

                self._send_json_response(200, response)

        elif self.path == '/clear':
            # Clear the action queue
            coordinator.clear_actions()

            if self.server.debug:
                logger.debug("[HTTP] Action queue cleared (GET)")

            self._send_json_response(200, {
                'status': 'cleared',
                'queue_size': 0
            })

        else:
            self._send_json_response(404, {'error': 'Not found'})

    def do_POST(self):
        """Handle POST requests"""
        coordinator = self.server.coordinator

        if self.path == '/action':
            # Queue an action
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                action_data = json.loads(body)

                if self.server.debug:
                    logger.debug(f"[HTTP] Received action: {action_data}")

                action = action_from_json(action_data)

                if self.server.debug:
                    logger.debug(f"[HTTP] Created action object: {type(action).__name__}")

                # Queue action in coordinator
                coordinator.add_action_to_queue(action)

                if self.server.debug:
                    logger.debug(f"[HTTP] Queued action. Queue size: {len(coordinator.action_queue)}")

                self._send_json_response(200, {
                    'status': 'queued',
                    'action': action_data.get('type')
                })

            except ValueError as e:
                logger.error(f"[HTTP] ValueError: {e}")
                self._send_json_response(400, {
                    'status': 'error',
                    'error': str(e)
                })
            except json.JSONDecodeError:
                logger.error("[HTTP] JSON decode error")
                self._send_json_response(400, {
                    'status': 'error',
                    'error': 'Invalid JSON'
                })
            except Exception as e:
                logger.error(f"[HTTP] Unexpected error: {e}")
                self._send_json_response(500, {
                    'status': 'error',
                    'error': str(e)
                })

        elif self.path == '/clear':
            # Clear the action queue
            coordinator.clear_actions()

            if self.server.debug:
                logger.debug("[HTTP] Action queue cleared")

            self._send_json_response(200, {
                'status': 'cleared',
                'queue_size': 0
            })

        else:
            self._send_json_response(404, {'error': 'Not found'})

    def do_OPTIONS(self):
        """Handle CORS preflight"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


class SpireCommServer:
    """Wraps Coordinator with HTTP interface"""

    def __init__(self, host='127.0.0.1', port=8080, debug=False):
        self.host = host
        self.port = port
        self.debug = debug
        self.coordinator = Coordinator()
        self.server = None

    def _coordinator_loop(self):
        """Custom coordinator loop that polls state without callbacks"""
        try:
            while True:
                # Check if we have actions to execute
                if self.coordinator.action_queue and self.debug:
                    logger.debug(f"[COORDINATOR] Queue has {len(self.coordinator.action_queue)} action(s). "
                                f"Ready: {self.coordinator.game_is_ready}")

                # Execute any queued actions
                executed = self.coordinator.execute_next_action_if_ready()

                if executed and self.debug:
                    logger.debug(f"[COORDINATOR] Action executed. Queue remaining: {len(self.coordinator.action_queue)}")

                # Receive state updates but don't trigger callbacks
                received = self.coordinator.receive_game_state_update(block=False, perform_callbacks=False)

                if received and self.debug:
                    game_state = self.coordinator.last_game_state
                    screen_type = game_state.screen_type.name if game_state and game_state.screen_type else "NONE"
                    room_type = game_state.room_type if game_state else "Unknown"
                    logger.debug(f"[COORDINATOR] State update: in_game={self.coordinator.in_game}, "
                                f"ready={self.coordinator.game_is_ready}, "
                                f"screen={screen_type}, room={room_type}")
        except (EOFError, BrokenPipeError):
            # Game disconnected - shut down server
            logger.info("Game disconnected, shutting down...")
            if self.server:
                self.server.shutdown()

    def run(self):
        """Start the HTTP server"""
        logger.info("Sending ready handshake...")

        # Send ready handshake
        self.coordinator.signal_ready()

        logger.info("Starting coordinator in background thread...")

        # Start coordinator loop in background thread (custom loop without callbacks)
        coordinator_thread = threading.Thread(
            target=self._coordinator_loop,
            daemon=True
        )
        coordinator_thread.start()

        # Create HTTP server
        self.server = ThreadingHTTPServer((self.host, self.port), SpireCommHTTPHandler)
        self.server.coordinator = self.coordinator
        self.server.debug = self.debug

        logger.info(f"HTTP server listening on http://{self.host}:{self.port}")
        logger.info(f"Debug mode: {self.debug}")
        logger.info("Ready for connections")

        # Start HTTP server on main thread
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.server.shutdown()


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='SpireComm HTTP Server')
    parser.add_argument('--port', type=int, default=8080,
                        help='HTTP server port (default: 8080)')
    parser.add_argument('--host', type=str, default='127.0.0.1',
                        help='HTTP server host (default: 127.0.0.1)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    parser.add_argument('--log-file', type=str, default=None,
                        help='Log file path (default: spirecomm_server_TIMESTAMP.log)')

    args = parser.parse_args()

    # Setup logging
    log_file = setup_logger(log_file=args.log_file, debug=args.debug)

    logger.info("Starting SpireComm HTTP Server")
    logger.info(f"Log file: {log_file}")

    server = SpireCommServer(host=args.host, port=args.port, debug=args.debug)
    server.run()


if __name__ == '__main__':
    main()
