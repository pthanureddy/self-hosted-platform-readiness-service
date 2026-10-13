"""Bounded loopback TCP/HTTP verification of an installed lab service."""

from __future__ import annotations

import argparse
import json
import math
import socket
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from readiness_service.models import PlatformSnapshot

MAX_RESPONSE_BYTES = 512 * 1024
SENTINEL = "deployment-check-private-sentinel"


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Request, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def validate_url(base_url: str) -> tuple[str, str, int]:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("Use an HTTP loopback URL without credentials, query or path")
    port = parsed.port if parsed.port is not None else 80
    if not 1 <= port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    return base_url.rstrip("/"), parsed.hostname, port


def _request(
    base_url: str, path: str, timeout: float, payload: bytes | None = None
) -> tuple[int, bytes, dict[str, str]]:
    headers = {"Content-Type": "application/json"} if payload is not None else {}
    request = Request(base_url + path, data=payload, headers=headers)
    opener = build_opener(ProxyHandler({}), _RejectRedirect())
    try:
        response = opener.open(request, timeout=timeout)
    except HTTPError as error:
        response = error
    with response:
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if len(body) > MAX_RESPONSE_BYTES:
            raise ValueError("Response exceeds the bounded probe limit")
        return int(response.code), body, {k.lower(): v for k, v in response.headers.items()}


def verify_deployment(base_url: str, fixture: Path, timeout: float = 3.0) -> dict[str, Any]:
    base_url, host, port = validate_url(base_url)
    if not math.isfinite(timeout) or not 0.1 <= timeout <= 10:
        raise ValueError("Timeout must be finite and between 0.1 and 10 seconds")
    if fixture.stat().st_size > 1024 * 1024:
        raise ValueError("Fixture exceeds 1 MiB")
    snapshot = PlatformSnapshot.model_validate_json(fixture.read_text(encoding="utf-8"))
    checks: list[dict[str, Any]] = []

    def record(check_id: str, passed: bool, detail: str) -> None:
        checks.append({"id": check_id, "passed": passed, "detail": detail})

    try:
        with socket.create_connection((host, port), timeout=timeout):
            record("tcp_connect", True, "Loopback port accepts a TCP connection")
    except OSError:
        record("tcp_connect", False, "Loopback TCP connection failed")
    for path, expected in [("/health/live", "alive"), ("/health/ready", "ready")]:
        try:
            status, body, _ = _request(base_url, path, timeout)
            valid = status == 200 and json.loads(body).get("status") == expected
            record(path.rsplit("/", 1)[1], valid, f"Expected HTTP200/status={expected}")
        except (OSError, ValueError, AttributeError):
            record(path.rsplit("/", 1)[1], False, "Health response failed validation")
    try:
        status, body, headers = _request(
            base_url, "/v1/analyze", timeout, snapshot.model_dump_json().encode()
        )
        findings = json.loads(body).get("findings", [])
        valid = status == 200 and any(item.get("rule_id") == "K8S-001" for item in findings)
        record("analysis", valid, "Degraded fixture returns the expected K8S-001 finding")
        record("request_id", bool(headers.get("x-request-id")), "Response carries a request ID")
    except (OSError, ValueError, AttributeError, TypeError):
        record("analysis", False, "Analysis response failed validation")
        record("request_id", False, "No validated analysis response")
    try:
        status, body, _ = _request(
            base_url, "/v1/analyze", timeout, json.dumps({"invalid_probe": SENTINEL}).encode()
        )
        valid = (
            status == 422
            and json.loads(body).get("code") == "validation_error"
            and SENTINEL.encode() not in body
        )
        record(
            "invalid_input_privacy", valid, "Invalid input is rejected without echoing its value"
        )
    except (OSError, ValueError, AttributeError):
        record("invalid_input_privacy", False, "Invalid-input response failed validation")
    try:
        status, body, _ = _request(base_url, "/metrics", timeout)
        record(
            "metrics",
            status == 200 and b"readiness_http_requests_total" in body,
            "Metrics endpoint exposes the expected request series",
        )
    except (OSError, ValueError):
        record("metrics", False, "Metrics response failed validation")
    return {
        "schema_version": 1,
        "base_url": base_url,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
        "scope": "Loopback lab contracts; no device, TLS, firewall or production audit",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18080")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--output", type=Path, default=Path("artifacts/linux-deployment.json"))
    arguments = parser.parse_args(argv)
    try:
        result = verify_deployment(arguments.base_url, arguments.fixture, arguments.timeout)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"Deployment-check setup error: {type(error).__name__}")
        return 2
    print(
        f"Deployment checks: {sum(c['passed'] for c in result['checks'])}/{len(result['checks'])}"
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
