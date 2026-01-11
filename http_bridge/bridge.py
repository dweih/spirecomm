#!/usr/bin/env python3
"""
SpireComm HTTP Bridge

Translates stdin/stdout communication with Communication Mod to HTTP REST API.
Enables any language to interface with Slay the Spire via simple HTTP requests.
"""

import sys
import json
import threading
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import argparse
from socketserver import ThreadingMixIn

# ThreadingHTTPServer for Python 3.7+, manual implementation for older versions
try:
    from http.server import ThreadingHTTPServer
except ImportError:
    # Python < 3.7: Create ThreadingHTTPServer manually
    class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
        daemon_threads = True


class BridgeState:
    """Thread-safe storage for latest game state"""

    def __init__(self, record_dir=None, debug=False):
        self.lock = threading.Lock()
        self.latest_state = None
        self.last_update = None
        self.ready_sent = False
        self.ready_acknowledged = False
        self.record_dir = record_dir
        self.debug = debug
        self.sequence = 0

        if record_dir:
            os.makedirs(record_dir, exist_ok=True)
            self.record_file = open(os.path.join(record_dir, 'states.jsonl'), 'w')
        else:
            self.record_file = None

    def log(self, message):
        """Log debug message if debug mode enabled"""
        if self.debug:
            print(f"[BRIDGE] {message}", file=sys.stderr, flush=True)

    def record_state(self, state_json):
        """Record state to fixture file if recording enabled"""
        if self.record_file:
            try:
                state_obj = json.loads(state_json)
                fixture = {
                    'sequence': self.sequence,
                    'timestamp': time.time(),
                    'screen_type': state_obj.get('game_state', {}).get('screen_type', 'UNKNOWN'),
                    'state': state_obj
                }
                self.record_file.write(json.dumps(fixture) + '\n')
                self.record_file.flush()
                self.sequence += 1
            except Exception as e:
                self.log(f"Error recording state: {e}")


def stdin_reader_thread(state):
    """
    Read stdin line-by-line, process Communication Mod responses, store game states.
    Runs in background daemon thread.
    """
    state.log("stdin reader thread started")

    while True:
        # Read one line from stdin (character by character)
        line = ""
        char_count = 0
        while True:
            ch = sys.stdin.read(1)
            if not ch:  # EOF
                state.log("EOF detected on stdin, exiting reader thread")
                return
            if ch == '\n':
                break
            line += ch
            char_count += 1

        if not line.strip():
            state.log("Received empty line, ignoring")
            continue

        state.log(f"Received {len(line)} chars from stdin (first 100): {line[:100]}...")

        try:
            msg = json.loads(line)
            state.log(f"Parsed JSON successfully. Keys: {list(msg.keys())}")

            # After we send "ready", Communication Mod responds with a message
            # containing "ready_for_command". This is the acknowledgment.
            if not state.ready_acknowledged and msg.get('ready_for_command') is not None:
                state.log(f"Ready acknowledged by Communication Mod (ready_for_command={msg.get('ready_for_command')})")
                state.ready_acknowledged = True
                # This first response might not have in_game yet, so we store it anyway
                with state.lock:
                    state.latest_state = line.strip()
                    state.last_update = time.time()
                continue

            # Store game states (messages with in_game or error field)
            if 'in_game' in msg or 'error' in msg:
                state.log(f"Storing state update (in_game={msg.get('in_game')}, error={msg.get('error')})")
                with state.lock:
                    state.latest_state = line.strip()
                    state.last_update = time.time()

                # Record to fixture file if enabled
                state.record_state(line.strip())
            else:
                state.log(f"Received message but no in_game/error field, storing anyway")
                with state.lock:
                    state.latest_state = line.strip()
                    state.last_update = time.time()

        except json.JSONDecodeError as e:
            state.log(f"Failed to parse JSON: {e}")
            state.log(f"Raw line: {line}")
            # Ignore malformed JSON


class BridgeHTTPHandler(BaseHTTPRequestHandler):
    """HTTP request handler for bridge endpoints"""

    def log_message(self, format, *args):
        """Suppress default HTTP logging unless debug enabled"""
        if self.server.state.debug:
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
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        state = self.server.state

        if path == '/health':
            # Health check endpoint
            with state.lock:
                has_state = state.latest_state is not None
                last_update = state.last_update

            self._send_json_response(200, {
                'status': 'ready',
                'has_state': has_state,
                'last_update': last_update,
                'ready_sent': state.ready_sent,
                'ready_acknowledged': state.ready_acknowledged
            })

        elif path == '/state':
            # Get latest game state
            with state.lock:
                latest = state.latest_state
                timestamp = state.last_update

            if latest is None:
                # No state available yet
                self._send_json_response(204, {})
            else:
                self._send_json_response(200, {
                    'state': latest,
                    'timestamp': timestamp
                })

        elif path == '/ready':
            # Manual ready handshake (alternative to auto-handshake)
            state.log("Manual ready request received")
            if not state.ready_sent:
                print(json.dumps({"ready": True}), flush=True)
                state.ready_sent = True
            self._send_json_response(200, {'ready': True})

        else:
            # 404 Not Found
            self._send_json_response(404, {'error': 'Not found'})

    def do_POST(self):
        """Handle POST requests"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        state = self.server.state

        if path == '/action':
            # Send action to Communication Mod
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')

            try:
                data = json.loads(body)
                command = data.get('command', '')

                if not command:
                    self._send_json_response(400, {'error': 'Missing command field'})
                    return

                # Send command to stdout (Communication Mod)
                state.log(f"Sending command to stdout: {command}")
                print(command, flush=True)

                self._send_json_response(200, {'status': 'sent', 'command': command})

            except json.JSONDecodeError:
                self._send_json_response(400, {'error': 'Invalid JSON'})
            except Exception as e:
                state.log(f"Error handling action: {e}")
                self._send_json_response(500, {'error': str(e)})

        else:
            # 404 Not Found
            self._send_json_response(404, {'error': 'Not found'})

    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


def main():
    """Main entry point for HTTP bridge"""
    parser = argparse.ArgumentParser(description='SpireComm HTTP Bridge')
    parser.add_argument('--port', type=int,
                        default=int(os.environ.get('SPIRECOMM_BRIDGE_PORT', 8080)),
                        help='HTTP server port (default: 8080)')
    parser.add_argument('--host', type=str,
                        default=os.environ.get('SPIRECOMM_BRIDGE_HOST', '127.0.0.1'),
                        help='HTTP server host (default: 127.0.0.1)')
    parser.add_argument('--debug', action='store_true',
                        default=os.environ.get('SPIRECOMM_BRIDGE_DEBUG', '').lower() in ('1', 'true', 'yes'),
                        help='Enable debug logging')
    parser.add_argument('--record-fixtures', type=str, metavar='DIR',
                        help='Record game states to fixture directory')

    args = parser.parse_args()

    # Create shared state
    state = BridgeState(record_dir=args.record_fixtures, debug=args.debug)

    print(f"[BRIDGE] HTTP server listening on http://{args.host}:{args.port}", file=sys.stderr, flush=True)
    print(f"[BRIDGE] Debug mode: {args.debug}", file=sys.stderr, flush=True)
    if args.record_fixtures:
        print(f"[BRIDGE] Recording fixtures to: {args.record_fixtures}", file=sys.stderr, flush=True)

    # Check if stdin is a pipe (connected to Communication Mod) or a terminal
    stdin_is_pipe = not sys.stdin.isatty()

    if stdin_is_pipe:
        # Running with Communication Mod - send ready handshake and start reader
        state.log("stdin is a pipe, sending ready handshake to Communication Mod...")
        print("ready", flush=True)  # Send to stdout (Communication Mod listens here)
        state.ready_sent = True
        state.log("Ready handshake sent, starting stdin reader...")

        # Start stdin reader thread AFTER sending ready
        reader = threading.Thread(target=stdin_reader_thread, args=(state,), daemon=True)
        reader.start()
        state.log("stdin reader thread started")
    else:
        # Running standalone (testing mode) - no Communication Mod connected
        print(f"[BRIDGE] WARNING: stdin is a terminal (not piped)", file=sys.stderr, flush=True)
        print(f"[BRIDGE] Running in STANDALONE mode (no Communication Mod)", file=sys.stderr, flush=True)
        print(f"[BRIDGE] HTTP API is available, but no game state will be received", file=sys.stderr, flush=True)
        print(f"[BRIDGE] For testing, use: python test_bridge.py fixtures/sample", file=sys.stderr, flush=True)

    # Create and start HTTP server (threaded for concurrent requests)
    server = ThreadingHTTPServer((args.host, args.port), BridgeHTTPHandler)
    server.state = state  # Attach state to server for handler access

    state.log("Starting HTTP server (threaded)...")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[BRIDGE] Shutting down...", file=sys.stderr, flush=True)
        if state.record_file:
            state.record_file.close()
        server.shutdown()


if __name__ == '__main__':
    main()
