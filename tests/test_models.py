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
