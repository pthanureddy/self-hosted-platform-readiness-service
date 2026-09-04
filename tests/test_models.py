from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from readiness_service.models import KubernetesWorkload, PlatformSnapshot, Severity


def test_valid_fixture_parses(degraded_dict: dict) -> None:
    snapshot = PlatformSnapshot.model_validate(degraded_dict)
    assert snapshot.metadata.snapshot_id == "demo-degraded-001"
    assert len(snapshot.probes) == 2


def test_unknown_top_level_field_rejected(healthy_dict: dict) -> None:
    healthy_dict["unexpected"] = True
    with pytest.raises(ValidationError, match="extra_forbidden"):
        PlatformSnapshot.model_validate(healthy_dict)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("metadata", "snapshot_id"), ""),
        (("metadata", "environment"), ""),
        (("kubernetes_workloads", 0, "desired_replicas"), -1),
        (("kubernetes_workloads", 0, "kind"), "Pod"),
        (("rabbitmq_queues", 0, "messages_ready"), -1),
        (("rabbitmq_queues", 0, "publish_rate"), -0.1),
        (("backups", 0, "size_bytes"), -1),
        (("backups", 0, "stream"), ""),
        (("probes", 0, "probe_type"), "tcp"),
        (("probes", 0, "status_code"), 99),
        (("probes", 0, "error_code"), "lower case"),
        (("observability", 0, "alerts_last_hour"), -1),
    ],
)
def test_invalid_values_rejected(healthy_dict: dict, path: tuple, value: object) -> None:
    target = healthy_dict
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        PlatformSnapshot.model_validate(healthy_dict)


def test_ready_cannot_exceed_desired() -> None:
    with pytest.raises(ValidationError, match="ready_replicas"):
        KubernetesWorkload(
            namespace="default",
            name="api",
            kind="Deployment",
            desired_replicas=1,
            ready_replicas=2,
        )


def test_daemonset_allows_ready_above_exported_desired() -> None:
    item = KubernetesWorkload(
        namespace="default", name="agent", kind="DaemonSet", desired_replicas=1, ready_replicas=2
    )
    assert item.ready_replicas == 2


def test_severity_values_are_stable() -> None:
    assert [item.value for item in Severity] == ["critical", "high", "medium", "low", "info"]


def test_input_is_not_mutated(healthy_dict: dict) -> None:
    before = deepcopy(healthy_dict)
    PlatformSnapshot.model_validate(healthy_dict)
    assert healthy_dict == before


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: d["metadata"].update(captured_at="2026-09-04T10:00:00"),
        lambda d: d["argo_applications"][0].update(reconciled_at="2026-09-04T10:00:00"),
        lambda d: d["backups"][0].update(created_at="2026-09-04T10:00:00"),
        lambda d: d["backups"][0].update(restore_verified_at="2026-09-04T10:00:00"),
        lambda d: d["observability"][0].update(last_signal_at="2026-09-04T10:00:00"),
        lambda d: d["probes"][0].update(
            probe_type="tls",
            status_code=None,
            certificate_expires_at="2026-09-10T10:00:00",
        ),
    ],
)
def test_operational_timestamps_require_timezone(healthy_dict: dict, mutate) -> None:
    mutate(healthy_dict)
    with pytest.raises(ValidationError) as caught:
        PlatformSnapshot.model_validate(healthy_dict)
    assert any(error["type"] == "timezone_aware" for error in caught.value.errors())


@pytest.mark.parametrize(
    "probe",
    [
        {"target": "dns.example", "probe_type": "dns", "success": True},
        {
            "target": "dns.example",
            "probe_type": "dns",
            "success": False,
            "status_code": 503,
        },
        {"target": "http.example", "probe_type": "http", "success": True},
        {
            "target": "http.example",
            "probe_type": "http",
            "success": True,
            "status_code": 200,
            "dns_answers": ["192.0.2.1"],
        },
        {"target": "tls.example", "probe_type": "tls", "success": True},
        {
            "target": "tls.example",
            "probe_type": "tls",
            "success": False,
            "dns_answers": ["192.0.2.1"],
        },
        {
            "target": "http.example",
            "probe_type": "http",
            "success": True,
            "status_code": 200,
            "error_code": "TIMEOUT",
        },
    ],
)
def test_probe_type_specific_fields_are_enforced(healthy_dict: dict, probe: dict) -> None:
    healthy_dict["probes"] = [probe]
    with pytest.raises(ValidationError):
        PlatformSnapshot.model_validate(healthy_dict)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_rates_are_rejected(healthy_dict: dict, value: float) -> None:
    healthy_dict["rabbitmq_queues"][0]["publish_rate"] = value
    with pytest.raises(ValidationError) as caught:
        PlatformSnapshot.model_validate(healthy_dict)
    assert any(error["type"] == "finite_number" for error in caught.value.errors())


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("rabbitmq_queues", 0, "messages_ready"), 2_147_483_648),
        (("backups", 0, "size_bytes"), 9_007_199_254_740_992),
        (("probes", 0, "latency_ms"), 3_600_001),
        (("rabbitmq_queues", 0, "publish_rate"), 1_000_000_001),
    ],
)
def test_numeric_maxima_are_enforced(healthy_dict: dict, path: tuple, value: object) -> None:
    target = healthy_dict
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError) as caught:
        PlatformSnapshot.model_validate(healthy_dict)
    assert any(error["type"] == "less_than_equal" for error in caught.value.errors())
