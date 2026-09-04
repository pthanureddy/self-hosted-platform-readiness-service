# Architecture

## Data flow

```text
exported JSON snapshot
        |
        v
Pydantic validation --rejects--> bounded 422 response
        |
        v
deterministic rule functions
        |
        v
severity/rule/resource ordering
        |
        +--> JSON API response
        +--> CLI stdout or file

service telemetry --> Prometheus / optional OTLP collector
```

The domain model separates six evidence types. Every operational timestamp must include timezone information, and bounded numeric fields reject non-finite values. Each rule consumes only the validated in-memory snapshot plus a normalized UTC analysis time. Backup objects are grouped by bucket and explicit logical stream: recency and integrity/encryption rules evaluate only the latest supplied object, while the latest restore-test timestamp is evaluated across that stream. The engine gathers and orders immutable Pydantic findings. It performs no discovery, remediation, shell execution, or outbound query.

## Components

- `models.py`: strict input/output contracts and bounded collection sizes.
- `rules.py`: independent deterministic generators with stable IDs.
- `engine.py`: orchestration, ordering, and severity summary.
- `api.py`: FastAPI transport, health, metrics, correlation IDs, and capped value-free errors.
- `cli.py`: local-file adapter, capped value-free validation errors, and policy exit codes.
- `telemetry.py`: optional OTLP/HTTP traces when configured and installed.

## Deployment topology

The Helm chart runs an unprivileged stateless pod behind a release-specific ClusterIP Service. It disables service-account token mounting, drops Linux capabilities, uses a read-only root filesystem and bounded `/tmp`, supports immutable image digests, defines resource requests/limits and probes, and can add a disruption budget, network policy, ServiceMonitor, and PrometheusRule. Monitoring-resource discovery labels are configurable.

The three Argo CD examples select configuration profiles at the `v0.1.0` source revision; on-prem synchronization remains manual. They do not establish connectivity to a real cluster or guarantee that the external chart image exists. Terraform bootstraps only namespace-level controls. The Compose stack is a local configuration lab, with Mimir/Loki/Tempo behind an explicit `full` profile. Its OTel Collector exports traces to `debug` only; no remote-write or log-shipping pipeline is configured.

## Design decisions

- Deterministic rules make output explainable and regression-testable.
- Hypotheses are explicitly bounded because snapshots cannot prove causality.
- Remediation is intentionally outside the trust boundary.
- Argo CD pruning is disabled for automated profiles, and on-prem sync is manual, to avoid implied destructive automation.
- No Kubernetes credentials are needed by the application.
