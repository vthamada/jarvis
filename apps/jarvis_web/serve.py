"""Opt-in static fixture server. This is not the JARVIS API or a Core gateway."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ASSET_ROOT = Path(__file__).resolve().parent
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/app.mjs": ("app.mjs", "text/javascript; charset=utf-8"),
    "/controller.mjs": ("controller.mjs", "text/javascript; charset=utf-8"),
    "/fixtures.mjs": ("fixtures.mjs", "text/javascript; charset=utf-8"),
    "/snapshot.mjs": ("snapshot.mjs", "text/javascript; charset=utf-8"),
    "/conversation-pack.mjs": ("conversation-pack.mjs", "text/javascript; charset=utf-8"),
    "/voice-controller.mjs": ("voice-controller.mjs", "text/javascript; charset=utf-8"),
    "/transcript-review.mjs": ("transcript-review.mjs", "text/javascript; charset=utf-8"),
    "/particle-sphere.mjs": ("particle-sphere.mjs", "text/javascript; charset=utf-8"),
    "/local-voice-playback.mjs": ("local-voice-playback.mjs", "text/javascript; charset=utf-8"),
}
CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self'; "
    "connect-src 'none'; img-src 'none'; font-src 'none'; "
    "object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'"
)


class FixtureHandler(BaseHTTPRequestHandler):
    """Allowlisted immutable assets only; suppress URL, user and body logging."""

    server_version = "JarvisFixture/1"
    sys_version = ""

    def log_message(self, format: str, *args: object) -> None:
        pass

    def _reply(self, status: int, payload: bytes, content_type: str, *, head: bool) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        if not head:
            self.wfile.write(payload)

    def _serve(self, *, head: bool = False) -> None:
        port = self.server.server_address[1]
        # Reject hostile Host values as well as absolute-form proxy requests.
        hosts = self.headers.get_all("Host", [])
        if len(hosts) != 1 or hosts[0] not in {f"127.0.0.1:{port}", f"localhost:{port}"}:
            self._reply(403, b"Host not allowed", "text/plain; charset=utf-8", head=head)
            return
        if self.path not in ASSETS:
            self._reply(404, b"Asset not found", "text/plain; charset=utf-8", head=head)
            return
        filename, content_type = ASSETS[self.path]
        path = ASSET_ROOT / filename
        if path.is_symlink() or path.resolve().parent != ASSET_ROOT or not path.is_file():
            self._reply(404, b"Asset not found", "text/plain; charset=utf-8", head=head)
            return
        self._reply(200, path.read_bytes(), content_type, head=head)

    def do_GET(self) -> None:
        self._serve()

    def do_HEAD(self) -> None:
        self._serve(head=True)

    def _reject_method(self) -> None:
        self.close_connection = True
        self._reply(405, b"Only GET and HEAD are allowed", "text/plain; charset=utf-8", head=False)

    def send_error(self, code: int, message=None, explain=None) -> None:
        # Never reflect unsupported methods, parser details or request content.
        self.close_connection = True
        self._reply(code, b"Request rejected", "text/plain; charset=utf-8", head=False)

    do_POST = _reject_method
    do_PUT = _reject_method
    do_PATCH = _reject_method
    do_DELETE = _reject_method
    do_OPTIONS = _reject_method
    do_TRACE = _reject_method
    do_CONNECT = _reject_method


def create_server(port: int = 8765) -> ThreadingHTTPServer:
    """Always bind IPv4 loopback; port zero permits ephemeral test servers."""
    if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
        raise ValueError("Port must be an integer between 0 and 65535")
    return ThreadingHTTPServer(("127.0.0.1", port), FixtureHandler)


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve fixture-only JARVIS cockpit on loopback")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    with create_server(args.port) as server:
        print(f"JARVIS FIXTURE ONLY: http://127.0.0.1:{server.server_port}/")
        print("No Core, API, provider or effects. Ctrl+C stops this foreground server.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
