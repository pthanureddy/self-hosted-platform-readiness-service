"""Validated API contracts for exported operational evidence."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

NonNegativeInt = Annotated[int, Field(ge=0)]
NonNegativeFloat = Annotated[float, Field(ge=0)]


class StrictModel(BaseModel):
    """Reject unknown fields so exporter/schema drift fails visibly."""

    model_config = ConfigDict(extra="forbid")


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class SnapshotMetadata(StrictModel):
    snapshot_id: Annotated[str, Field(min_length=1, max_length=128)]
    captured_at: datetime
    environment: Annotated[str, Field(min_length=1, max_length=64)]
    source_version: Annotated[str, Field(min_length=1, max_length=64)] = "unknown"


class KubernetesWorkload(StrictModel):
    namespace: Annotated[str, Field(min_length=1, max_length=253)]
    name: Annotated[str, Field(min_length=1, max_length=253)]
    kind: Literal["Deployment", "StatefulSet", "DaemonSet", "Job"]
    desired_replicas: NonNegativeInt = 1
    ready_replicas: NonNegativeInt = 0
    available_replicas: NonNegativeInt = 0
    restart_count: NonNegativeInt = 0
    phase: Literal["Running", "Pending", "Failed", "Succeeded", "Unknown"] = "Unknown"
    unavailable_seconds: NonNegativeInt = 0

    @model_validator(mode="after")
    def validate_replica_bounds(self) -> KubernetesWorkload:
        if self.kind != "DaemonSet" and self.ready_replicas > self.desired_replicas:
            raise ValueError("ready_replicas cannot exceed desired_replicas")
        return self


class ArgoApplication(StrictModel):
    name: Annotated[str, Field(min_length=1, max_length=253)]
    namespace: Annotated[str, Field(min_length=1, max_length=253)] = "argocd"
    sync_status: Literal["Synced", "OutOfSync", "Unknown"]
    health_status: Literal["Healthy", "Progressing", "Degraded", "Suspended", "Missing", "Unknown"]
    operation_phase: Literal["Succeeded", "Running", "Failed", "Error", "Unknown"] = "Unknown"
    reconciled_at: datetime | None = None


class RabbitMQQueue(StrictModel):
    vhost: Annotated[str, Field(min_length=1, max_length=255)] = "/"
    name: Annotated[str, Field(min_length=1, max_length=255)]
    messages_ready: NonNegativeInt
    messages_unacked: NonNegativeInt
    consumers: NonNegativeInt
    publish_rate: NonNegativeFloat = 0
    deliver_rate: NonNegativeFloat = 0
    oldest_message_age_seconds: NonNegativeInt = 0


class BackupObject(StrictModel):
    bucket: Annotated[str, Field(min_length=1, max_length=255)]
    key: Annotated[str, Field(min_length=1, max_length=1024)]
    created_at: datetime
    size_bytes: NonNegativeInt
    checksum_present: bool
    encrypted: bool
    restore_verified_at: datetime | None = None


class ProbeResult(StrictModel):
    target: Annotated[str, Field(min_length=1, max_length=2048)]
    probe_type: Literal["dns", "http", "tls"]
    success: bool
    latency_ms: NonNegativeFloat | None = None
    status_code: Annotated[int, Field(ge=100, le=599)] | None = None
    dns_answers: list[str] = Field(default_factory=list, max_length=64)
    certificate_expires_at: datetime | None = None
    error_code: Annotated[str, Field(pattern=r"^[A-Z0-9_\-]{1,64}$")] | None = None


class ObservabilityCoverage(StrictModel):
    component: Annotated[str, Field(min_length=1, max_length=253)]
    logs: bool
    metrics: bool
    traces: bool
    alerts: bool
    last_signal_at: datetime | None = None
    alerts_last_hour: NonNegativeInt = 0


class PlatformSnapshot(StrictModel):
    metadata: SnapshotMetadata
    kubernetes_workloads: list[KubernetesWorkload] = Field(default_factory=list, max_length=5000)
    argo_applications: list[ArgoApplication] = Field(default_factory=list, max_length=5000)
    rabbitmq_queues: list[RabbitMQQueue] = Field(default_factory=list, max_length=5000)
    backups: list[BackupObject] = Field(default_factory=list, max_length=5000)
    probes: list[ProbeResult] = Field(default_factory=list, max_length=5000)
    observability: list[ObservabilityCoverage] = Field(default_factory=list, max_length=5000)


class Finding(StrictModel):
    rule_id: Annotated[str, Field(pattern=r"^[A-Z0-9]+-[0-9]{3}$")]
    severity: Severity
    resource: str
    title: str
    observed_evidence: dict[str, Any]
    bounded_hypothesis: str
    next_safe_check: str
    runbook_url: HttpUrl
    escalation_condition: str


class AnalysisSummary(StrictModel):
    total: NonNegativeInt
    critical: NonNegativeInt
    high: NonNegativeInt
    medium: NonNegativeInt
    low: NonNegativeInt
    info: NonNegativeInt


class AnalysisResult(StrictModel):
    snapshot_id: str
    analyzed_at: datetime
    findings: list[Finding]
    summary: AnalysisSummary


class ErrorDetail(StrictModel):
    code: str
    message: str
    request_id: str
    issues: list[dict[str, Any]] = Field(default_factory=list)
