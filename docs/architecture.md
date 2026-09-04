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

The domain model separates six evidence types. Each rule consumes only the validated in-memory snapshot plus a normalized UTC analysis time. The engine gathers and orders immutable Pydantic findings. It performs no discovery, remediation, shell execution, or outbound query.

## Components

- `models.py`: strict input/output contracts and bounded collection sizes.
- `rules.py`: independent deterministic generators with stable IDs.
- `engine.py`: orchestration, ordering, and severity summary.
- `api.py`: FastAPI transport, health, metrics, correlation IDs, and safe errors.
- `cli.py`: local-file adapter and policy exit codes.
- `telemetry.py`: optional OTLP/HTTP traces when configured and installed.

## Deployment topology

The Helm chart runs an unprivileged stateless pod behind a ClusterIP Service. It disables service-account token mounting, drops Linux capabilities, uses a read-only root filesystem and bounded `/tmp`, defines resource requests/limits and probes, and can add a disruption budget, network policy, ServiceMonitor, and PrometheusRule.

The three Argo CD examples select configuration profiles; they do not establish connectivity to a real cluster. Terraform bootstraps only namespace-level controls. The Compose stack is a local integration lab, with Mimir/Loki/Tempo behind an explicit `full` profile.

## Design decisions

- Deterministic rules make output explainable and regression-testable.
- Hypotheses are explicitly bounded because snapshots cannot prove causality.
- Remediation is intentionally outside the trust boundary.
- Argo CD pruning is disabled in examples to avoid implied destructive automation.
- No Kubernetes credentials are needed by the application.

