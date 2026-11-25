"""Dashboard build and the local server's security behaviour."""

import http.client
import json
import re
import threading
from pathlib import Path

import pytest
from conftest import SMARD_CSV

from product_data_checker.dashboard import build_payload, write_site
from product_data_checker.metrics import quality_metrics, smard_metrics
from product_data_checker.server import make_server

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"
WEB = ROOT / "src" / "product_data_checker" / "dashboard" / "web"


@pytest.fixture(scope="module")
def site(tmp_path_factory, demo_result):
    out = tmp_path_factory.mktemp("site")
    smard = smard_metrics(SMARD_CSV) if SMARD_CSV.exists() else None
    payload = build_payload(demo_result, quality_metrics(demo_result), smard)
    secret = out.parent / "secret.txt"
    secret.write_text("nicht ausliefern")
    return write_site(payload, out / "site", [])


@pytest.fixture(scope="module")
def server(site):
    srv = make_server(site, 0)
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv.server_address[1]
    srv.shutdown()
    srv.server_close()


def request(port, method, path):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path)
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    return resp, body


def test_payload_is_complete(site, demo_result):
    data = json.loads((site / "data.json").read_text(encoding="utf-8"))
    assert len(data["review"]) == len(demo_result.to_review())
    assert len(data["released"]) == len(demo_result.released())
    assert data["pipeline"]["released"] == len(demo_result.released())
    assert {q["name"] for q in data["queries"]} >= {"error_rate_by_supplier", "reasons"}
    assert all(q["sql"].strip() for q in data["queries"])


def test_html_has_no_inline_script_or_style(site):
    html = (site / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)", html)
    assert "style=" not in html
    assert "<style" not in html


def test_frontend_never_writes_html_from_data():
    """Every value from data.json reaches the page as React text, never as markup."""
    sources = [
        *FRONTEND.rglob("*.ts"),
        *FRONTEND.rglob("*.tsx"),
        ROOT / "frontend" / "public" / "boot.js",
    ]
    assert len(sources) > 20
    sinks = (
        "dangerouslySetInnerHTML",
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "document.write",
        "eval(",
        "new Function",
    )
    for path in sources:
        code = path.read_text(encoding="utf-8")
        for sink in sinks:
            assert sink not in code, f"{sink} in {path.name}"


def test_built_bundle_is_shipped_and_has_no_inline_code():
    """pdc serve needs no Node: the built app is part of the package."""
    html = (WEB / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)", html)
    assert "<style" not in html and "style=" not in html
    scripts = re.findall(r'src="\./(assets/[^"]+\.js)"', html)
    assert scripts and all((WEB / s).exists() for s in scripts)
    assert (WEB / "assets" / "AlloVariableFriendly.woff2").exists()
    assert (WEB / "licenses" / "Allo-OFL.txt").exists()


def test_security_headers(server):
    resp, body = request(server, "GET", "/")
    assert resp.status == 200
    csp = resp.getheader("Content-Security-Policy")
    assert (
        "default-src 'none'" in csp and "script-src 'self'" in csp and "'unsafe-inline'" not in csp
    )
    assert resp.getheader("X-Content-Type-Options") == "nosniff"
    assert resp.getheader("X-Frame-Options") == "DENY"
    assert "Python" not in resp.getheader("Server")


@pytest.mark.parametrize(
    "path", ["/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt", "/..%5csecret.txt"]
)
def test_no_path_traversal(server, path):
    resp, body = request(server, "GET", path)
    assert resp.status == 404
    assert b"nicht ausliefern" not in body


def test_no_directory_listing(server):
    resp, _ = request(server, "GET", "/assets/")
    assert resp.status == 404


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
def test_write_methods_are_refused(server, method):
    resp, _ = request(server, method, "/data.json")
    assert resp.status in (405, 501)


def test_server_binds_to_localhost_only(site):
    srv = make_server(site, 0)
    try:
        assert srv.server_address[0] == "127.0.0.1"
    finally:
        srv.server_close()


def request_with_host(port, host):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.putrequest("GET", "/data.json", skip_host=True)
    if host is not None:
        conn.putheader("Host", host)
    conn.endheaders()
    resp = conn.getresponse()
    body = resp.read()
    conn.close()
    return resp, body


@pytest.mark.parametrize(
    "host", ["attacker.example", "attacker.example:{port}", "127.0.0.1:1", "", None]
)
def test_foreign_host_header_is_refused(server, host):
    """DNS rebinding: a foreign page resolving its own name to 127.0.0.1 gets nothing."""
    resp, body = request_with_host(server, host.format(port=server) if host else host)
    assert resp.status == 421
    assert b"review" not in body


@pytest.mark.parametrize("host", ["127.0.0.1:{port}", "localhost:{port}", "LOCALHOST:{port}"])
def test_loopback_host_header_is_served(server, host):
    resp, _ = request_with_host(server, host.format(port=server))
    assert resp.status == 200


def test_error_pages_are_german_styled_and_echo_nothing(server):
    resp, body = request(server, "GET", "/gibt-es-nicht-xyz")
    assert resp.status == 404
    text = body.decode("utf-8")
    assert "Diese Seite gibt es nicht" in text
    assert 'href="/error.css"' in text
    assert "<script" not in text and "style=" not in text
    assert "gibt-es-nicht-xyz" not in text  # the request path is never written into the page
    assert "Content-Security-Policy" in dict(resp.getheaders())
