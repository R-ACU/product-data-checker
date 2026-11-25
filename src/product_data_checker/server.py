"""Minimal read-only server for the built dashboard (stdlib only).

Binds to 127.0.0.1, answers GET/HEAD only, serves nothing outside the site folder,
lists no directories, refuses foreign Host headers (DNS rebinding) and sends a strict
Content-Security-Policy.
"""

from __future__ import annotations

import socket
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
        "font-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'; "
        "frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Cache-Control": "no-store",
}


ERROR_PAGE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<title>%(code)d | Produktdaten-Prüfer</title>
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/error.css">
</head>
<body>
<main class="card">
<p class="code">%(code)d</p>
<h1>%(message)s</h1>
<p class="lede">%(explain)s</p>
<a class="btn" href="/">Zum Dashboard</a>
</main>
</body>
</html>
"""
# German texts for the few errors this server sends; nothing from the request is echoed
ERROR_TEXTS = {
    HTTPStatus.NOT_FOUND: (
        "Diese Seite gibt es nicht",
        "Das Dashboard liefert nur seine eigenen Dateien aus.",
    ),
    HTTPStatus.METHOD_NOT_ALLOWED: (
        "Nur lesen erlaubt",
        "Das Dashboard nimmt keine Daten entgegen.",
    ),
    HTTPStatus.MISDIRECTED_REQUEST: (
        "Adresse nicht zugelassen",
        "Das Dashboard antwortet nur unter 127.0.0.1 und localhost.",
    ),
    HTTPStatus.NOT_IMPLEMENTED: ("Nur lesen erlaubt", "Das Dashboard nimmt keine Daten entgegen."),
}


class DashboardHandler(SimpleHTTPRequestHandler):
    server_version = "pdc"  # no framework or Python version in the Server header
    sys_version = ""
    error_message_format = ERROR_PAGE
    error_content_type = "text/html; charset=utf-8"

    def send_error(self, code, message=None, explain=None):
        title, text = ERROR_TEXTS.get(
            code, ("Anfrage nicht möglich", "Das Dashboard kann diese Anfrage nicht beantworten.")
        )
        super().send_error(code, title, text)

    extensions_map = {
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".json": "application/json; charset=utf-8",
        ".woff2": "font/woff2",
        ".svg": "image/svg+xml",
        ".txt": "text/plain; charset=utf-8",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".csv": "text/csv; charset=utf-8",
    }

    def end_headers(self) -> None:
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)
        if self.path.startswith("/downloads/"):
            self.send_header("Content-Disposition", "attachment")
        super().end_headers()

    def _suspicious(self) -> bool:
        """Dot segments, backslashes or NUL in the decoded path are refused outright.

        SimpleHTTPRequestHandler already drops such segments; refusing them is clearer
        than relying on that and avoids odd redirects on Windows.
        """
        decoded = unquote(urlsplit(self.path).path)
        parts = decoded.replace("\\", "/").split("/")
        return "\\" in decoded or "\x00" in decoded or ".." in parts

    def _foreign_host(self) -> bool:
        """True unless the Host header names this server on loopback.

        A web page on another origin can point its own domain at 127.0.0.1 (DNS
        rebinding) and then read responses as same-origin. The browser still sends that
        domain as Host, so only the loopback names with our port are served.
        """
        port = self.server.server_address[1]
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        return (self.headers.get("Host") or "").strip().lower() not in allowed

    def _refuse(self) -> bool:
        if self._foreign_host():
            self.send_error(HTTPStatus.MISDIRECTED_REQUEST)
            return True
        if self._suspicious():
            self.send_error(HTTPStatus.NOT_FOUND)
            return True
        return False

    def do_GET(self) -> None:  # noqa: N802
        if not self._refuse():
            super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802
        if not self._refuse():
            super().do_HEAD()

    def list_directory(self, path):  # no directory listings
        self.send_error(HTTPStatus.NOT_FOUND)
        return None

    def do_POST(self) -> None:  # noqa: N802 (http.server naming)
        self.send_error(HTTPStatus.METHOD_NOT_ALLOWED)

    do_PUT = do_DELETE = do_PATCH = do_OPTIONS = do_POST  # noqa: N815

    def log_message(self, fmt: str, *args) -> None:
        pass  # quiet; the CLI prints the URL once


def port_is_free(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) != 0


def make_server(site_dir: Path, port: int, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    if not (site_dir / "index.html").exists():
        raise FileNotFoundError(f"{site_dir} enthält kein index.html; zuerst 'pdc build' ausführen")
    handler = partial(DashboardHandler, directory=str(site_dir.resolve()))
    return ThreadingHTTPServer((host, port), handler)
