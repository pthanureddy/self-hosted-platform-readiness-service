# Noisy or missing telemetry

## Evidence to preserve

Record component, expected logs/metrics/traces/alerts, last observed signal time, alert fingerprints and counts, collector/backend health, sampling policy, and deployment version. Avoid copying sensitive log bodies or span attributes.

## Read-only checks

1. Generate no synthetic production traffic; identify an existing known event or approved test signal.
2. Query each boundary: application emission, collector receive/export, transport, storage, and dashboard/query.
3. Check time range, labels, tenancy headers, sampling, retention, and clock skew.
4. Group alert fingerprints and identify top contributors.
5. Correlate gaps or noise with recent configuration/deployment changes.

## Bounded hypotheses

Instrumentation, collector, transport, storage, query, or sampling issues may explain missing signals. High alert volume may reflect a real incident, duplication, or poor tuning.

## Escalation

Escalate when visibility blocks incident assessment, regulated/audit signals are absent, storage is losing data, or alert noise threatens response. Include telemetry and service owners.

## Change and rollback boundary

Do not mute alerts, reduce retention, increase sampling cost, or change pipelines during an incident without approval. Version configuration, define before/after measures, preserve critical alerts, and make rollback a reviewed operator action.

