# Operations

## Signals

- `/health/live` shows that the process can serve a request.
- `/health/ready` shows that the stateless analyzer is accepting requests.
- `/metrics` exports request counts, analysis counts, and analysis duration.
- JSON logs include a bounded `request_id`, route, status, duration, and aggregate analysis metadata.
- Optional traces are sent via OTLP/HTTP only when an endpoint is configured.

Health endpoints do not validate external systems because the analyzer has no external dependencies. A successful readiness response does not imply that a submitted platform is healthy.

## Incident posture

1. Preserve the request ID and snapshot ID.
2. Check service health, resource saturation, and bounded logs.
3. Validate the exporter timestamp and scope before interpreting a finding.
4. Follow the linked evidence-first runbook.
5. Obtain resource-owner approval before a change.

The `scripts/diagnose.sh` helper issues read-only Kubernetes commands. It does not establish authorization for accessing a cluster.

## Upgrade and rollback boundary

Pin an immutable image digest, review the generated release-specific manifest, and observe error/latency metrics during a rollout. Rollback is an operator-controlled Helm/Argo action, not an application feature. Before rollback, determine whether response-schema consumers can tolerate the older version. Preserve failed request metadata, never submitted operational payloads unless policy explicitly permits it.

## Rule changes

Treat rule IDs and response fields as an API contract. Add new IDs for materially different conditions; do not silently repurpose an existing ID. Test threshold boundaries, severity ordering, evidence fields, hypotheses, checks, runbook links, and escalation text.
