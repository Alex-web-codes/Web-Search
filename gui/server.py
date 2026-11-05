"""Frontend GUI: a tiny HTTP server for the search page.

Serves the static page in ./static and a JSON API:

    GET /api/search?q=<query>   -> search results, or {"error": ...} with 400
    GET /api/stats              -> corpus and index sizes

Uses only the standard library, so there is nothing to install.
"""

from __future__ import annotations

import json
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from search_engine import QueryError, SearchEngine

STATIC_DIR = (Path(__file__).parent / "static").resolve()

# Set explicitly: Windows can map .js to text/plain via the registry.
CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


def make_handler(engine: SearchEngine) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "CorpusSearch/1.0"

        def do_GET(self) -> None:
            url = urlparse(self.path)
            if url.path == "/api/search":
                query = parse_qs(url.query).get("q", [""])[0]
                try:
                    self._send_json(engine.search(query).to_dict())
                except QueryError as err:
                    self._send_json({"error": str(err)}, HTTPStatus.BAD_REQUEST)
            elif url.path == "/api/stats":
                self._send_json(engine.stats())
            else:
                self._send_static(url.path)

        def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _send_static(self, path: str) -> None:
            if path in ("", "/"):
                path = "/index.html"
            target = (STATIC_DIR / path.lstrip("/")).resolve()
            if STATIC_DIR not in target.parents or not target.is_file():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            body = target.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", CONTENT_TYPES.get(target.suffix, "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt: str, *args) -> None:
            pass  # keep the console quiet; errors still raise

    return Handler


def serve(engine: SearchEngine, host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    server = ThreadingHTTPServer((host, port), make_handler(engine))
    url = f"http://{host}:{port}/"
    print(f"Serving on {url}  (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
