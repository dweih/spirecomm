#!/usr/bin/env python3
"""
SpireComm HTTP Server - Minimal implementation for combat testing

Wraps the Coordinator with an HTTP interface.
"""

import sys
import json
import threading
from http.server import BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from http.server import HTTPServer

from spirecomm.communication.coordinator import Coordinator
from spirecomm.communication.action_factory import action_from_json


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
                action = action_from_json(action_data)

                # Queue action in coordinator
                coordinator.add_action_to_queue(action)

                self._send_json_response(200, {
                    'status': 'queued',
                    'action': action_data.get('type')
                })

            except ValueError as e:
                self._send_json_response(400, {
                    'status': 'error',
                    'error': str(e)
                })
            except json.JSONDecodeError:
                self._send_json_response(400, {
                    'status': 'error',
                    'error': 'Invalid JSON'
                })
            except Exception as e:
                self._send_json_response(500, {
                    'status': 'error',
                    'error': str(e)
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
                # Execute any queued actions
                self.coordinator.execute_next_action_if_ready()
                # Receive state updates but don't trigger callbacks
                received = self.coordinator.receive_game_state_update(block=False, perform_callbacks=False)

                if received and self.debug:
                    print(f"[COORDINATOR] State update: in_game={self.coordinator.in_game}, "
                          f"has_state={self.coordinator.last_game_state is not None}, "
                          f"ready={self.coordinator.game_is_ready}",
                          file=sys.stderr, flush=True)
        except (EOFError, BrokenPipeError):
            # Game disconnected - shut down server
            print("\n[SPIRECOMM] Game disconnected, shutting down...", file=sys.stderr, flush=True)
            if self.server:
                self.server.shutdown()

    def run(self):
        """Start the HTTP server"""
        print("[SPIRECOMM] Sending ready handshake...", file=sys.stderr, flush=True)

        # Send ready handshake
        self.coordinator.signal_ready()

        print("[SPIRECOMM] Starting coordinator in background thread...", file=sys.stderr, flush=True)

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

        print(f"[SPIRECOMM] HTTP server listening on http://{self.host}:{self.port}", file=sys.stderr, flush=True)
        print(f"[SPIRECOMM] Debug mode: {self.debug}", file=sys.stderr, flush=True)
        print("[SPIRECOMM] Ready for connections", file=sys.stderr, flush=True)

        # Start HTTP server on main thread
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n[SPIRECOMM] Shutting down...", file=sys.stderr, flush=True)
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

    args = parser.parse_args()

    server = SpireCommServer(host=args.host, port=args.port, debug=args.debug)
    server.run()


if __name__ == '__main__':
    main()
