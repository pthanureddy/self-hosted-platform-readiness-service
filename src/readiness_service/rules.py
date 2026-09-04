"""Deterministic, read-only rules over supplied snapshot evidence."""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import HttpUrl

from readiness_service.models import Finding, PlatformSnapshot, Severity

RUNBOOK_BASE = (
    "https://github.com/pthanureddy/self-hosted-platform-readiness-service/blob/main/docs/runbooks"
)


def _finding(
    rule_id: str,
    severity: Severity,
    resource: str,
    title: str,
    evidence: dict[str, Any],
    hypothesis: str,
    check: str,
    runbook: str,
    escalation: str,
) -> Finding:
    return Finding(
        rule_id=rule_id,
        severity=severity,
        resource=resource,
        title=title,
        observed_evidence=evidence,
        bounded_hypothesis=hypothesis,
        next_safe_check=check,
        runbook_url=HttpUrl(f"{RUNBOOK_BASE}/{runbook}"),
        escalation_condition=escalation,
    )


def kubernetes_findings(snapshot: PlatformSnapshot, _: datetime) -> Iterable[Finding]:
    for item in snapshot.kubernetes_workloads:
        resource = f"{item.namespace}/{item.kind}/{item.name}"
        if item.phase == "Failed" or (item.desired_replicas > 0 and item.ready_replicas == 0):
            yield _finding(
                "K8S-001",
                Severity.CRITICAL if item.unavailable_seconds >= 900 else Severity.HIGH,
                resource,
                "Workload has no ready replicas",
                {
                    "desired_replicas": item.desired_replicas,
                    "ready_replicas": item.ready_replicas,
                    "phase": item.phase,
                    "unavailable_seconds": item.unavailable_seconds,
                },
                "The exported state is consistent with an unavailable workload; it does not identify the cause.",
                "Read pod status and recent namespace events; do not restart or roll back from this finding alone.",
                "failing-workload.md",
                "Escalate when zero ready replicas persist for 15 minutes or a stated service objective is breached.",
            )
        elif item.ready_replicas < item.desired_replicas:
            yield _finding(
                "K8S-002",
                Severity.MEDIUM,
                resource,
                "Workload is below desired readiness",
                {"desired_replicas": item.desired_replicas, "ready_replicas": item.ready_replicas},
                "A rollout, scheduling constraint, or unhealthy pod may explain the readiness gap.",
                "Compare desired and current ReplicaSet or StatefulSet revisions, then inspect events.",
                "failing-workload.md",
                "Escalate if capacity remains reduced beyond the deployment's accepted rollout window.",
            )
        if item.restart_count >= 5:
            yield _finding(
                "K8S-003",
                Severity.HIGH if item.restart_count >= 20 else Severity.MEDIUM,
                resource,
                "Elevated container restart count",
                {"restart_count": item.restart_count, "phase": item.phase},
                "Repeated process exits or probe failures may be occurring; restart count alone is not causal evidence.",
                "Read termination reasons and previous container logs with secrets redacted.",
                "failing-workload.md",
                "Escalate for continued restart growth, correlated request failures, or data-integrity risk.",
            )


def argo_findings(snapshot: PlatformSnapshot, _: datetime) -> Iterable[Finding]:
    for app in snapshot.argo_applications:
        resource = f"{app.namespace}/Application/{app.name}"
        if app.health_status in {"Degraded", "Missing"} or app.operation_phase in {
            "Failed",
            "Error",
        }:
            yield _finding(
                "ARGO-001",
                Severity.HIGH,
                resource,
                "GitOps application reports unhealthy state",
                {"health_status": app.health_status, "operation_phase": app.operation_phase},
                "A failed reconciliation or unhealthy managed resource may exist in the exported Argo CD state.",
                "Read the application condition and resource diff before approving sync or rollback.",
                "failing-workload.md",
                "Escalate when the application is degraded across two reconciliations or affects a critical service.",
            )
        if app.sync_status == "OutOfSync":
            yield _finding(
                "ARGO-002",
                Severity.MEDIUM,
                resource,
                "GitOps application is out of sync",
                {"sync_status": app.sync_status, "reconciled_at": app.reconciled_at},
                "Declared and observed resources differ; the snapshot does not establish whether drift is intentional.",
                "Review the read-only Argo CD diff and change history with the service owner.",
                "failing-workload.md",
                "Escalate when drift includes security controls, persistent data, or remains unexplained.",
            )


def rabbitmq_findings(snapshot: PlatformSnapshot, _: datetime) -> Iterable[Finding]:
    for queue in snapshot.rabbitmq_queues:
        vhost = queue.vhost.strip("/") or "root"
        resource = f"rabbitmq://{vhost}/queue/{queue.name}"
        if queue.messages_ready >= 100 and queue.consumers == 0:
            yield _finding(
                "RMQ-001",
                Severity.HIGH,
                resource,
                "Queue backlog has no consumers",
                {"messages_ready": queue.messages_ready, "consumers": queue.consumers},
                "Consumers may be unavailable or detached; queue statistics do not identify why.",
                "Confirm bindings and consumer deployment readiness using read-only commands.",
                "queue-backlog.md",
                "Escalate if backlog age or size breaches the queue owner's documented threshold.",
            )
        elif queue.messages_ready >= 100 and queue.publish_rate > queue.deliver_rate:
            yield _finding(
                "RMQ-002",
                Severity.MEDIUM,
                resource,
                "Queue backlog is growing",
                {
                    "messages_ready": queue.messages_ready,
                    "publish_rate": queue.publish_rate,
                    "deliver_rate": queue.deliver_rate,
                },
                "Current ingress exceeds delivery rate in this snapshot; the trend requires another sample.",
                "Compare multiple time-bounded samples and inspect consumer saturation metrics.",
                "queue-backlog.md",
                "Escalate when growth persists for the owner-defined interval or oldest-message SLO is exceeded.",
            )
        if queue.oldest_message_age_seconds >= 3600:
            yield _finding(
                "RMQ-003",
                Severity.HIGH,
                resource,
                "Old message remains queued",
                {"oldest_message_age_seconds": queue.oldest_message_age_seconds},
                "The snapshot contains a message older than one hour; poison-message or capacity causes remain unproven.",
                "Inspect redacted message metadata and dead-letter routing without consuming or deleting messages.",
                "queue-backlog.md",
                "Escalate before any purge/requeue action and when contractual processing latency is breached.",
            )


def backup_findings(snapshot: PlatformSnapshot, now: datetime) -> Iterable[Finding]:
    stale_before = now - timedelta(hours=25)
    restore_before = now - timedelta(days=30)
    for backup in snapshot.backups:
        resource = f"s3://{backup.bucket}/{backup.key}"
        if backup.created_at < stale_before:
            yield _finding(
                "BKP-001",
                Severity.HIGH,
                resource,
                "Latest supplied backup is stale",
                {"created_at": backup.created_at, "age_threshold_hours": 25},
                "The supplied object is older than the policy threshold; this may be an incomplete export.",
                "Confirm inventory scope and scheduler history without writing to the backup bucket.",
                "stale-backup.md",
                "Escalate when the complete inventory has no recent successful backup or retention is at risk.",
            )
        if backup.restore_verified_at is None or backup.restore_verified_at < restore_before:
            yield _finding(
                "BKP-002",
                Severity.MEDIUM,
                resource,
                "Restore verification is absent or old",
                {"restore_verified_at": backup.restore_verified_at, "age_threshold_days": 30},
                "Recovery usability has not been demonstrated recently by the supplied metadata.",
                "Review the last isolated restore-test record; schedule a controlled test through change management.",
                "stale-backup.md",
                "Escalate when recovery objectives require a newer proof or no isolated test environment exists.",
            )
        if not backup.checksum_present or not backup.encrypted:
            yield _finding(
                "BKP-003",
                Severity.HIGH,
                resource,
                "Backup protection metadata is incomplete",
                {"checksum_present": backup.checksum_present, "encrypted": backup.encrypted},
                "Integrity or encryption evidence is absent in the export; the object itself was not accessed.",
                "Confirm bucket policy, encryption headers, and checksum metadata using read-only API calls.",
                "stale-backup.md",
                "Escalate immediately if policy requires encryption/integrity and absence is confirmed at source.",
            )


def probe_findings(snapshot: PlatformSnapshot, now: datetime) -> Iterable[Finding]:
    for probe in snapshot.probes:
        resource = f"{probe.probe_type}://{probe.target}"
        if not probe.success:
            rule_id = {"dns": "NET-001", "http": "NET-002", "tls": "NET-003"}[probe.probe_type]
            yield _finding(
                rule_id,
                Severity.HIGH,
                resource,
                f"{probe.probe_type.upper()} probe failed",
                {"error_code": probe.error_code, "status_code": probe.status_code},
                "The exported probe failed from its observation point; reachability elsewhere is unknown.",
                "Repeat from an approved second vantage point and inspect configuration without changing it.",
                "network-probes.md",
                "Escalate when two vantage points fail or a user-facing endpoint is unavailable.",
            )
        if probe.probe_type == "tls" and probe.certificate_expires_at:
            days = (probe.certificate_expires_at - now).total_seconds() / 86400
            if days <= 14:
                yield _finding(
                    "NET-004",
                    Severity.HIGH if days <= 3 else Severity.MEDIUM,
                    resource,
                    "TLS certificate expires soon",
                    {
                        "certificate_expires_at": probe.certificate_expires_at,
                        "days_remaining": round(days, 2),
                    },
                    "The presented certificate is near expiry; renewal state was not supplied.",
                    "Inspect issuer, secret/controller status, and renewal events without replacing the certificate.",
                    "network-probes.md",
                    "Escalate at three days remaining, on renewal errors, or per certificate-owner policy.",
                )


def observability_findings(snapshot: PlatformSnapshot, now: datetime) -> Iterable[Finding]:
    stale_before = now - timedelta(minutes=15)
    for signal in snapshot.observability:
        missing = [
            name
            for name, present in (
                ("logs", signal.logs),
                ("metrics", signal.metrics),
                ("traces", signal.traces),
                ("alerts", signal.alerts),
            )
            if not present
        ]
        if missing or signal.last_signal_at is None or signal.last_signal_at < stale_before:
            yield _finding(
                "OBS-001",
                Severity.MEDIUM,
                f"component/{signal.component}",
                "Telemetry coverage is incomplete or stale",
                {"missing_signals": missing, "last_signal_at": signal.last_signal_at},
                "Telemetry may be missing at source, collector, transport, or query layer; the snapshot cannot localize it.",
                "Check one known signal at each pipeline boundary using read-only queries.",
                "telemetry.md",
                "Escalate when missing visibility blocks incident assessment or breaches monitoring policy.",
            )
        if signal.alerts_last_hour >= 100:
            yield _finding(
                "OBS-002",
                Severity.LOW,
                f"component/{signal.component}",
                "High alert volume may obscure actionable signals",
                {"alerts_last_hour": signal.alerts_last_hour},
                "Alert volume is high in the supplied window; duplicate or low-value alerts are possible but unproven.",
                "Group alert fingerprints and identify top contributors without muting or editing rules.",
                "telemetry.md",
                "Escalate tuning changes to alert owners and incident command before muting any alert.",
            )


RULES = (
    kubernetes_findings,
    argo_findings,
    rabbitmq_findings,
    backup_findings,
    probe_findings,
    observability_findings,
)


def normalize_now(value: datetime) -> datetime:
    """Return a timezone-aware UTC timestamp for deterministic time comparisons."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
