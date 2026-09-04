from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

import pytest

from readiness_service.engine import analyze_snapshot
from readiness_service.models import PlatformSnapshot
from tests.conftest import NOW


def codes(data: dict[str, Any]) -> list[str]:
    result = analyze_snapshot(PlatformSnapshot.model_validate(data), analyzed_at=NOW)
    return [finding.rule_id for finding in result.findings]


def test_healthy_fixture_has_no_findings(healthy_dict: dict) -> None:
    assert codes(healthy_dict) == []


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (
            lambda d: d["kubernetes_workloads"][0].update(
                ready_replicas=0, unavailable_seconds=1200
            ),
            "K8S-001",
        ),
        (lambda d: d["kubernetes_workloads"][0].update(ready_replicas=1), "K8S-002"),
        (lambda d: d["kubernetes_workloads"][0].update(restart_count=5), "K8S-003"),
        (lambda d: d["argo_applications"][0].update(health_status="Degraded"), "ARGO-001"),
        (lambda d: d["argo_applications"][0].update(sync_status="OutOfSync"), "ARGO-002"),
        (lambda d: d["rabbitmq_queues"][0].update(messages_ready=100, consumers=0), "RMQ-001"),
        (
            lambda d: d["rabbitmq_queues"][0].update(
                messages_ready=100, publish_rate=2, deliver_rate=1
            ),
            "RMQ-002",
        ),
        (lambda d: d["rabbitmq_queues"][0].update(oldest_message_age_seconds=3600), "RMQ-003"),
        (lambda d: d["backups"][0].update(created_at="2026-09-02T00:00:00Z"), "BKP-001"),
        (lambda d: d["backups"][0].update(restore_verified_at=None), "BKP-002"),
        (lambda d: d["backups"][0].update(checksum_present=False), "BKP-003"),
        (
            lambda d: d["probes"][0].update(probe_type="dns", success=False, error_code="NXDOMAIN"),
            "NET-001",
        ),
        (
            lambda d: d["probes"][0].update(probe_type="http", success=False, error_code="TIMEOUT"),
            "NET-002",
        ),
        (
            lambda d: d["probes"][0].update(
                probe_type="tls", success=False, error_code="HANDSHAKE"
            ),
            "NET-003",
        ),
        (
            lambda d: d["probes"][0].update(
                probe_type="tls", certificate_expires_at="2026-09-10T00:00:00Z"
            ),
            "NET-004",
        ),
        (lambda d: d["observability"][0].update(traces=False), "OBS-001"),
        (lambda d: d["observability"][0].update(alerts_last_hour=100), "OBS-002"),
    ],
)
def test_individual_rule(healthy_dict: dict, mutate: Any, expected: str) -> None:
    mutate(healthy_dict)
    assert expected in codes(healthy_dict)


def test_failed_phase_is_critical_candidate(healthy_dict: dict) -> None:
    healthy_dict["kubernetes_workloads"][0].update(phase="Failed", ready_replicas=0)
    result = analyze_snapshot(PlatformSnapshot.model_validate(healthy_dict), analyzed_at=NOW)
    assert result.findings[0].rule_id == "K8S-001"
    assert result.findings[0].severity == "high"


def test_long_unavailable_is_critical(healthy_dict: dict) -> None:
    healthy_dict["kubernetes_workloads"][0].update(ready_replicas=0, unavailable_seconds=900)
    result = analyze_snapshot(PlatformSnapshot.model_validate(healthy_dict), analyzed_at=NOW)
    assert result.findings[0].severity == "critical"


def test_twenty_restarts_is_high(healthy_dict: dict) -> None:
    healthy_dict["kubernetes_workloads"][0]["restart_count"] = 20
    result = analyze_snapshot(PlatformSnapshot.model_validate(healthy_dict), analyzed_at=NOW)
    assert result.findings[0].severity == "high"


def test_tls_three_days_is_high(healthy_dict: dict) -> None:
    healthy_dict["probes"][0].update(
        probe_type="tls", certificate_expires_at="2026-09-07T10:00:00Z"
    )
    result = analyze_snapshot(PlatformSnapshot.model_validate(healthy_dict), analyzed_at=NOW)
    assert result.findings[0].severity == "high"


def test_naive_analyzed_at_becomes_utc(healthy_snapshot: PlatformSnapshot) -> None:
    result = analyze_snapshot(healthy_snapshot, analyzed_at=datetime(2026, 9, 4, 10, 0))
    assert result.analyzed_at.tzinfo is not None


def test_degraded_fixture_all_findings_have_actionable_contract(
    degraded_snapshot: PlatformSnapshot,
) -> None:
    result = analyze_snapshot(degraded_snapshot, analyzed_at=NOW)
    assert result.findings
    for finding in result.findings:
        assert finding.observed_evidence
        assert (
            "snapshot" in finding.bounded_hypothesis.lower()
            or "supplied" in finding.bounded_hypothesis.lower()
            or "export" in finding.bounded_hypothesis.lower()
            or "may" in finding.bounded_hypothesis.lower()
        )
        assert finding.next_safe_check
        assert finding.runbook_url.path.endswith(".md")
        assert finding.escalation_condition.startswith("Escalate")


def test_analysis_does_not_mutate_snapshot(degraded_dict: dict) -> None:
    before = deepcopy(degraded_dict)
    analyze_snapshot(PlatformSnapshot.model_validate(degraded_dict), analyzed_at=NOW)
    assert degraded_dict == before


def test_deterministic_order_and_summary(degraded_snapshot: PlatformSnapshot) -> None:
    first = analyze_snapshot(degraded_snapshot, analyzed_at=NOW)
    second = analyze_snapshot(degraded_snapshot, analyzed_at=NOW)
    assert first == second
    ranks = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    order = [(ranks[f.severity], f.rule_id, f.resource) for f in first.findings]
    assert order == sorted(order)
    assert first.summary.total == len(first.findings)
    assert (
        sum(
            [
                first.summary.critical,
                first.summary.high,
                first.summary.medium,
                first.summary.low,
                first.summary.info,
            ]
        )
        == first.summary.total
    )
