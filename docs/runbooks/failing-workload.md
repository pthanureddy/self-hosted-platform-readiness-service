# Failing Kubernetes workload or GitOps application

## Evidence to preserve

Record snapshot/request IDs, namespace, kind, workload/application name, desired and ready counts, phase, restart count, Argo health/sync/operation state, and observation timestamp. Do not copy secrets or full environment dumps into tickets.

## Read-only checks

1. Confirm the export is current and includes the intended namespace.
2. Read pod status, termination reason, owner references, ReplicaSet revision, and recent namespace events.
3. Read previous container logs with credentials and user content redacted.
4. Review the Argo CD resource diff and change history; do not press Sync.
5. Correlate the time window with request errors, saturation, and an approved change record.

## Bounded hypotheses

Scheduling, rollout, probe, dependency, configuration, or process-exit failures are possible. A readiness count or Argo status does not prove one of them.

## Escalation

Escalate to the workload owner when no replicas are ready for 15 minutes, an SLO is breached, restarts continue rising, the diff touches data/security controls, or causality remains unclear. Involve incident command for user-visible critical impact.

## Change and rollback boundary

Restart, scale, delete, sync, or rollback only through the owning team's approved procedure. Capture the current revision and data-migration compatibility first. Stop rollback if it would reverse an irreversible migration or destroy unpersisted work.

