# Self-Hosted Platform Readiness Service

A deterministic FastAPI and CLI service that turns **exported** platform observations into ordered, evidence-first findings. It helps an operator triage a snapshot without connecting to, changing, or remediating the target environment.

The project is an independent engineering portfolio implementation. It is not affiliated with any platform vendor, is not proof of production or on-call operation, and does not claim that its example deployment profiles have run in customer environments.

## What it evaluates

- Kubernetes workload readiness, failed state, and restarts
- Argo CD application sync, health, and operation state
- RabbitMQ backlog, consumer availability, throughput, and message age
- S3-compatible backup age, checksum/encryption metadata, and restore-test evidence
- DNS, HTTP, and TLS probe exports
- Logs, metrics, traces, and alerts coverage

Every finding carries a stable rule ID, severity, resource, observed evidence, bounded hypothesis, next safe check, runbook link, and explicit escalation condition. Rules never call a cluster, cloud API, queue, endpoint, or object store.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
readiness fixtures/degraded-snapshot.json
uvicorn readiness_service.api:app --host 127.0.0.1 --port 8080
curl -sS -H 'content-type: application/json' --data-binary @fixtures/degraded-snapshot.json http://127.0.0.1:8080/v1/analyze
```

On PowerShell, activate with `.venv\Scripts\Activate.ps1`. Use `--fail-on high` or `--fail-on critical` for a policy-aware CLI exit code; the default never fails on findings.

## Interfaces

| Interface | Purpose |
|---|---|
| `POST /v1/analyze` | Validate and analyze one snapshot |
| `GET /health/live` | Process liveness |
| `GET /health/ready` | Request-serving readiness |
| `GET /metrics` | Prometheus metrics |
| `readiness SNAPSHOT.json` | Offline CLI analysis |

Unknown input fields are rejected. Validation and internal errors use bounded responses and do not echo submitted values. The service logs request metadata and analysis counts, not entire snapshots.

## Deployment evidence

- Multi-stage, non-root, read-only compatible Docker image
- Docker Compose observability lab with OTel Collector, Prometheus, Grafana, and optional Mimir/Loki/Tempo profiles
- Hardened Helm chart plus `managed`, `dedicated`, `onprem`, and ephemeral `kind` values
- Three Argo CD Application examples with pruning disabled
- Terraform namespace, quota, and limit-range bootstrap with mocked plan tests
- GitHub Actions for Python quality, image build, Helm rendering, Terraform validation/tests, YAML policies, and a real ephemeral kind deployment smoke test

These are testable deployment artifacts, not evidence that the service currently operates a live external platform. See [architecture](docs/architecture.md), [security boundaries](docs/security-boundaries.md), [setup](docs/setup.md), [operations](docs/operations.md), and [limitations](docs/limitations.md).

## Rule behavior

Rules are deterministic for a given snapshot and analysis timestamp. Findings are sorted by severity, then rule ID, then resource. Time-based thresholds are intentionally conservative examples and should be replaced with approved service policies before operational use.

## Verification

```bash
ruff format --check .
ruff check .
mypy
pytest --cov=readiness_service --cov-report=term-missing --cov-fail-under=90
python scripts/verify_static.py
docker compose config --quiet
docker build -t readiness-service:local .
helm lint helm/readiness-service
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform validate
terraform -chdir=terraform test
```

Helm, Terraform, Docker daemon, and Kubernetes verification require those tools locally. CI runs the complete path, including kind.

## License

[MIT](LICENSE)
