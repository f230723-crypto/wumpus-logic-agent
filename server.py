"""
server.py
=========
Lightweight HTTP server for the Wumpus Logic Agent web application.

Endpoints
---------
GET  /              → Serve index.html (the frontend)
GET  /state         → Return current game state as JSON
POST /new           → Start a new game  {rows, cols}
POST /move          → Manual move       {row, col}
POST /step          → Agent auto-step

Run
---
    python server.py
    # then open http://localhost:8000
"""

import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

from wumpus_world import WumpusWorld


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL GAME STATE
# ─────────────────────────────────────────────────────────────────────────────

_game: WumpusWorld | None = None


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST HANDLER
# ─────────────────────────────────────────────────────────────────────────────

class WumpusHandler(BaseHTTPRequestHandler):
    """Handles all incoming HTTP requests."""

    # ── silences the default per-request log noise ────────────────────────────
    def log_message(self, fmt, *args):
        pass

    # ── helpers ───────────────────────────────────────────────────────────────

    def _send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type",   "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type",   "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def _path(self) -> str:
        return self.path.split("?")[0]

    def _no_game(self) -> bool:
        """Return 400 and True if no game is active."""
        global _game
        if _game is None:
            self._send_json({"error": "No active game. POST /new first."}, 400)
            return True
        return False

    # ── GET ───────────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        path = self._path()

        if path in ("/", "/index.html"):
            # Serve the frontend HTML file from the same directory
            html_path = os.path.join(os.path.dirname(__file__), "index.html")
            try:
                with open(html_path, "r", encoding="utf-8") as fh:
                    self._send_html(fh.read())
            except FileNotFoundError:
                self._send_json({"error": "index.html not found"}, 404)

        elif path == "/state":
            if self._no_game():
                return
            self._send_json(_game.state())

        else:
            self._send_json({"error": "Not found"}, 404)

    # ── POST ──────────────────────────────────────────────────────────────────

    def do_POST(self) -> None:
        global _game
        path = self._path()
        body = self._read_body()

        if path == "/new":
            rows  = max(4, min(10, int(body.get("rows", 5))))
            cols  = max(4, min(10, int(body.get("cols", 5))))
            _game = WumpusWorld(rows, cols)
            self._send_json(_game.state())

        elif path == "/move":
            if self._no_game():
                return
            row = int(body.get("row", 0))
            col = int(body.get("col", 0))
            self._send_json(_game.move_agent(row, col))

        elif path == "/step":
            if self._no_game():
                return
            self._send_json(_game.agent_step())

        else:
            self._send_json({"error": "Not found"}, 404)

    # ── OPTIONS (CORS preflight) ──────────────────────────────────────────────

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self._cors_headers()
        self.end_headers()


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

PORT = 8000

if __name__ == "__main__":
    server = HTTPServer(("", PORT), WumpusHandler)
    print("=" * 56)
    print("  Wumpus Logic Agent — Server")
    print("=" * 56)
    print(f"  URL  :  http://localhost:{PORT}")
    print(f"  Files:  server.py | wumpus_world.py | logic_engine.py | index.html")
    print("  Stop :  Ctrl + C")
    print("=" * 56)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
