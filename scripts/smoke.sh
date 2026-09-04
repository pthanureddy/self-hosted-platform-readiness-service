#!/usr/bin/env bash
set -euo pipefail

base_url="${1:-http://127.0.0.1:8080}"
curl --fail --silent --show-error "$base_url/health/ready" | grep -q '"ready"'
response="$(curl --fail --silent --show-error -H 'content-type: application/json' --data-binary @fixtures/degraded-snapshot.json "$base_url/v1/analyze")"
printf '%s' "$response" | grep -q '"rule_id":"K8S-001"\|"rule_id": "K8S-001"'
echo "smoke test passed"

