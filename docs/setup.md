# Setup

## Local Python

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev,otel]"
pytest
uvicorn readiness_service.api:app --host 127.0.0.1 --port 8080
```

Tracing is off by default. Set `OTEL_EXPORTER_OTLP_ENDPOINT=http://127.0.0.1:4318` to enable OTLP/HTTP export when the optional dependencies are installed.

## Docker Compose lab

```bash
docker compose up --build readiness otel-collector prometheus grafana
docker compose --profile full up --build
```

The full profile starts local single-process Mimir, Loki, and Tempo examples. All state is disposable. The collector defaults to its debug exporter so Tempo is not required by the base profile.

## Helm

```bash
helm lint helm/readiness-service
helm template readiness helm/readiness-service -f helm/readiness-service/values-kind.yaml
helm upgrade --install readiness helm/readiness-service \
  --namespace readiness-service --create-namespace \
  --values helm/readiness-service/values-onprem.yaml
```

Use an immutable image digest and reviewed environment-specific network policy in any controlled deployment. `values-kind.yaml` exists only for CI and disables CRD-dependent resources and network policy.

## Terraform bootstrap

```bash
terraform -chdir=terraform init -backend=false
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform validate
terraform -chdir=terraform test
```

Review a real provider context and saved plan before any apply. The automated tests mock the Kubernetes provider and do not contact a cluster.

