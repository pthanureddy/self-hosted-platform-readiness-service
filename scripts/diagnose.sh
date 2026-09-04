#!/usr/bin/env bash
set -euo pipefail

# Read-only diagnostics: this script never restarts, scales, patches, deletes, or synchronizes resources.
namespace="${1:-readiness-service}"
kubectl auth can-i get pods --namespace "$namespace"
kubectl get deployment,pod,service --namespace "$namespace" -o wide
kubectl get events --namespace "$namespace" --sort-by=.metadata.creationTimestamp | tail -n 50
kubectl get networkpolicy,poddisruptionbudget --namespace "$namespace"

