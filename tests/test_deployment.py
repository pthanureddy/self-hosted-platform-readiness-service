from __future__ import annotations

import json
import socket
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from readiness_service.deployment import (
    MAX_RESPONSE_BYTES,
    SENTINEL,
    main,
    validate_url,
    verify_deployment,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "degraded-snapshot.json"


@contextmanager
def endpoint(mode="normal", redirect_url=None, requests=None):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, status, body, request_id=True):
            self.send_response(status)
            if request_id:
                self.send_header("x-request-id", "test-correlation")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if requests is not None:
                requests.append(self.path)
            if mode == "redirect":
                self.send_response(302)
                self.send_header("Location", redirect_url)
                self.end_headers()
                return
            if mode == "oversized":
                self.reply(200, b"x" * (MAX_RESPONSE_BYTES + 1))
            elif mode == "malformed":
                self.reply(200, b"not-json")
            elif self.path == "/health/live":
                self.reply(200, b'{"status":"alive"}')
            elif self.path == "/health/ready":
                self.reply(503 if mode == "unready" else 200, b'{"status":"ready"}')
            else:
                self.reply(
                    200,
                    b"missing-metric" if mode == "metrics" else b"readiness_http_requests_total 4",
                )

        def do_POST(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            if SENTINEL.encode() in body:
                response = {"code": "validation_error"}
                if mode == "echo":
                    response["input"] = SENTINEL
                self.reply(422, json.dumps(response).encode())
            else:
                finding = "UNKNOWN" if mode == "analysis" else "K8S-001"
                self.reply(
                    200,
                    json.dumps({"findings": [{"rule_id": finding}]}).encode(),
                    request_id=mode != "request_id",
                )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=2)


def test_contract_success(tmp_path):
    with endpoint() as url:
        result = verify_deployment(url, FIXTURE)
        assert result["passed"] and len(result["checks"]) == 7
        output = tmp_path / "nested" / "report.json"
        assert main(["--base-url", url, "--fixture", str(FIXTURE), "--output", str(output)]) == 0
        assert json.loads(output.read_text())["passed"]


@pytest.mark.parametrize(
    "mode,failed_check",
    [
        ("unready", "ready"),
        ("malformed", "live"),
        ("oversized", "live"),
        ("echo", "invalid_input_privacy"),
        ("analysis", "analysis"),
        ("request_id", "request_id"),
        ("metrics", "metrics"),
    ],
)
def test_remote_contract_failures(mode, failed_check, tmp_path):
    with endpoint(mode) as url:
        result = verify_deployment(url, FIXTURE)
        assert not result["passed"]
        assert not next(c for c in result["checks"] if c["id"] == failed_check)["passed"]
        assert (
            main(
                [
                    "--base-url",
                    url,
                    "--fixture",
                    str(FIXTURE),
                    "--output",
                    str(tmp_path / "out.json"),
                ]
            )
            == 1
        )


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:8080",
        "http://example.org",
        "http://user:pass@localhost",
        "http://localhost/api",
        "http://localhost?secret=x",
        "http://localhost#x",
        "http://localhost:99999",
        "http://localhost:0",
    ],
)
def test_rejects_unbounded_or_ambiguous_targets(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_default_and_trailing_slash_url():
    assert validate_url("http://localhost/") == ("http://localhost", "localhost", 80)


def test_redirects_cannot_escape_the_selected_endpoint():
    visited = []
    with endpoint(requests=visited) as other, endpoint("redirect", redirect_url=other) as url:
        result = verify_deployment(url, FIXTURE)
    assert not result["passed"]
    assert visited == []


@pytest.mark.parametrize("timeout", [0.0, float("inf"), float("nan"), 11.0])
def test_timeout_limits(timeout):
    with pytest.raises(ValueError):
        verify_deployment("http://localhost", FIXTURE, timeout)


def test_transport_failure():
    with socket.socket() as unused:
        unused.bind(("127.0.0.1", 0))
        port = unused.getsockname()[1]
        result = verify_deployment(f"http://127.0.0.1:{port}", FIXTURE, timeout=0.1)
    assert not result["passed"]
    assert all(not check["passed"] for check in result["checks"])


def test_invalid_fixture_and_missing_fixture(tmp_path):
    fixture = tmp_path / "bad.json"
    fixture.write_text("{}")
    assert main(["--fixture", str(fixture)]) == 2
    assert main(["--fixture", str(tmp_path / "missing.json")]) == 2
    fixture.write_bytes(b"x" * (1024 * 1024 + 1))
    with pytest.raises(ValueError, match="1 MiB"):
        verify_deployment("http://localhost", fixture)


def test_report_write_failure(tmp_path):
    with endpoint() as url:
        assert main(["--base-url", url, "--fixture", str(FIXTURE), "--output", str(tmp_path)]) == 2
