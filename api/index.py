import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from http.server import BaseHTTPRequestHandler
import json
from wumpus_world import WumpusWorld

# Global game state (per-session via cookie workaround)
_games = {}

class handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        pass

    def _send_json(self, data, status=200):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))

    def _path(self):
        return self.path.split("?")[0]

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        path = self._path()
        if path in ("/", "/index.html"):
            html_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "index.html"
            )
            with open(html_path, "r", encoding="utf-8") as f:
                self._send_html(f.read())
        elif path == "/state":
            game = _games.get("default")
            if not game:
                self._send_json({"error": "No active game"}, 400)
            else:
                self._send_json(game.state())
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        path  = self._path()
        body  = self._read_body()

        if path == "/new":
            rows = max(4, min(10, int(body.get("rows", 5))))
            cols = max(4, min(10, int(body.get("cols", 5))))
            _games["default"] = WumpusWorld(rows, cols)
            self._send_json(_games["default"].state())

        elif path == "/move":
            game = _games.get("default")
            if not game:
                self._send_json({"error": "No active game"}, 400)
                return
            self._send_json(game.move_agent(int(body["row"]), int(body["col"])))

        elif path == "/step":
            game = _games.get("default")
            if not game:
                self._send_json({"error": "No active game"}, 400)
                return
            self._send_json(game.agent_step())

        else:
            self._send_json({"error": "Not found"}, 404)