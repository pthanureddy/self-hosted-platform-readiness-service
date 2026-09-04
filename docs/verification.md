# Verification record

Local verification was completed on 2026-09-04 for the current repository revision. The checks exercise the implementation and configuration; they are not evidence of a live external or production platform.

## Completed checks

| Check | Command | Result |
|---|---|---|
| Formatting | `ruff format --check .` | 29 files already formatted |
| Lint | `ruff check .` | Passed |
| Type safety | `mypy` | Passed; 9 source files |
| Tests and coverage | `pytest -q` | 93 passed; 97.15% branch-aware coverage (380 statements, 76 branches) |
| Static repository policy | `python scripts/verify_static.py` | Passed; 18 non-template YAML files, 3 Argo Applications, and 5 runbooks checked |
| Shell syntax | `bash -n scripts/diagnose.sh scripts/smoke.sh` | Passed with GNU Bash 5.2.37 |
| Compose model | `docker compose config --quiet` | Passed |
| Helm | `helm lint helm/readiness-service` | Passed; 1 chart |
| Helm profiles | `helm template` with kind, managed, dedicated, and on-prem values | All 4 rendered; digest, release-specific-name, discovery-label, and absent-series alert assertions passed |
| Terraform format | `terraform -chdir=terraform fmt -check -recursive` | Passed |
| Terraform validation | `terraform -chdir=terraform validate` | Passed |
| Terraform tests | `terraform -chdir=terraform test` | 2 passed, 0 failed with mocked Kubernetes provider |
| Package | `python -m pip wheel --no-deps .` | Wheel built successfully |
| CLI fixture | `readiness fixtures/degraded-snapshot.json --fail-on never` | Parsed; 13 ordered findings; first code `K8S-001` |

The test suite covers timezone-aware timestamps, finite bounded numbers, probe field semantics, backup stream selection, completed Jobs, every rule family and threshold branch, deterministic ordering and summaries, capped API/CLI validation errors, correlation IDs, health/metrics/OpenAPI behavior, CLI output/exit policies, logging setup, and optional tracing behavior.

## Environment-limited checks

The Docker 28.4.0 client was present locally, but its Linux daemon pipe was unavailable, so no local image or kind result is claimed. Public [GitHub Actions run 33912715020](https://github.com/pthanureddy/self-hosted-platform-readiness-service/actions/runs/33912715020) passed the image builds and an ephemeral kind smoke deployment that loaded the image, installed the Helm chart, waited for rollout, checked readiness, posted `fixtures/degraded-snapshot.json`, and asserted `K8S-001`.

## Operational limitations

- Rules evaluate caller-supplied exports and make no live platform calls.
- No automated remediation is implemented.
- Terraform tests use a mocked provider and do not apply resources.
- Helm and Argo CD files are rendered configuration examples, not proof of managed, dedicated, or on-prem operation.
- Mimir, Loki, and Tempo datasource/config examples are compatibility scaffolding for a disposable lab, not production observability evidence.
- No production, customer, on-call, or platform-vendor affiliation claim is made.
