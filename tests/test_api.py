from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from readiness_service import api


@pytest.fixture
def client() -> TestClient:
    with TestClient(api.app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_liveness(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["x-request-id"]


def test_readiness(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_not_ready(monkeypatch: pytest.MonkeyPatch, client: TestClient) -> None:
    monkeypatch.setattr(api, "SERVICE_READY", False)
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready"}


def test_analyze_returns_stable_code(client: TestClient, degraded_dict: dict[str, Any]) -> None:
    response = client.post("/v1/analyze", json=degraded_dict, headers={"x-request-id": "test-123"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-123"
    body = response.json()
    assert body["snapshot_id"] == "demo-degraded-001"
    assert "K8S-001" in [finding["rule_id"] for finding in body["findings"]]


def test_validation_error_is_bounded(client: TestClient, healthy_dict: dict[str, Any]) -> None:
    healthy_dict["metadata"]["snapshot_id"] = ""
    healthy_dict["metadata"]["secret"] = "do-not-echo"
    response = client.post(
        "/v1/analyze", json=healthy_dict, headers={"x-request-id": "validation-1"}
    )
    assert response.status_code == 422
    serialized = response.text
    assert "do-not-echo" not in serialized
    assert response.json()["code"] == "validation_error"
    assert response.json()["request_id"] == "validation-1"


def test_metrics_endpoint(client: TestClient) -> None:
    client.get("/health/live")
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "readiness_http_requests_total" in response.text
    assert "readiness_analyses_total" in response.text


def test_openapi_documents_contract(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert schema["info"]["title"] == "Self-Hosted Platform Readiness Service"
    assert "/v1/analyze" in schema["paths"]


def test_unmatched_route_has_request_id(client: TestClient) -> None:
    response = client.get("/not-found")
    assert response.status_code == 404
    assert response.headers["x-request-id"]


def test_unhandled_error_is_sanitized(
    monkeypatch: pytest.MonkeyPatch, client: TestClient, healthy_dict: dict[str, Any]
) -> None:
    def explode(_: object) -> None:
        raise RuntimeError("sensitive internal detail")

    monkeypatch.setattr(api, "analyze_snapshot", explode)
    response = client.post("/v1/analyze", json=healthy_dict)
    assert response.status_code == 500
    assert response.json()["code"] == "internal_error"
    assert "sensitive" not in response.text
