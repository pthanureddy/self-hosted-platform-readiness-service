"""Readiness analysis orchestration."""

from __future__ import annotations

from collections import Counter
from datetime import datetime

from readiness_service.models import AnalysisResult, AnalysisSummary, PlatformSnapshot, Severity
from readiness_service.rules import RULES, normalize_now

SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}


def analyze_snapshot(
    snapshot: PlatformSnapshot, *, analyzed_at: datetime | None = None
) -> AnalysisResult:
    """Evaluate all rules without mutating or reaching into the target environment."""
    # Default to the evidence capture time: replaying the same export should not
    # create new time-based findings merely because it is analyzed later.
    now = normalize_now(analyzed_at or snapshot.metadata.captured_at)
    findings = [finding for rule in RULES for finding in rule(snapshot, now)]
    findings.sort(
        key=lambda finding: (SEVERITY_ORDER[finding.severity], finding.rule_id, finding.resource)
    )
    counts = Counter(finding.severity for finding in findings)
    return AnalysisResult(
        snapshot_id=snapshot.metadata.snapshot_id,
        analyzed_at=now,
        findings=findings,
        summary=AnalysisSummary(
            total=len(findings),
            critical=counts[Severity.CRITICAL],
            high=counts[Severity.HIGH],
            medium=counts[Severity.MEDIUM],
            low=counts[Severity.LOW],
            info=counts[Severity.INFO],
        ),
    )
