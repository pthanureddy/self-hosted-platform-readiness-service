# Threat model and security boundaries

## Assets and actors

Submitted snapshots may contain operational topology and failure details. Callers, reverse proxies, cluster operators, and observability administrators are trusted only for their documented roles. The target platform is never trusted as an instruction source.

## Controls implemented

- Strict schemas reject unknown fields, timezone-naive timestamps, non-finite numbers, and out-of-range string/list/numeric inputs.
- Validation responses report paths and error types without echoing values, cap details at 20 issues, and state the total/truncation status.
- Unhandled errors return an opaque message plus request ID.
- Structured logs contain request metadata, snapshot ID, environment, and finding count—not full payloads.
- The container runs as UID/GID 10001, drops all capabilities, and supports a read-only root filesystem.
- The Helm pod has no service-account token and receives no Kubernetes RBAC.
- Default NetworkPolicy limits ingress and egress, although operators must adapt selectors to their cluster.
- GitHub Actions has read-only repository permissions.
- Managed/dedicated Argo CD examples disable prune; the on-prem example requires manual synchronization.

## Explicit trust boundary

The service accepts JSON supplied by a caller and returns diagnostic suggestions. It does not authenticate users, encrypt transport, store results, enforce tenant isolation, fetch secrets, verify backup contents, or contact observed resources. Production deployment requires an authenticated gateway, TLS termination, payload size controls, rate limiting, audit retention policy, and a data-classification review.

## Threats not solved here

- A truthful-looking but fabricated or incomplete snapshot.
- Sensitive values inserted into free-text resource names.
- Abuse through high request volume below schema collection limits.
- Compromise of the image registry, CI runner, Kubernetes node, reverse proxy, or observability backend.
- Authorization for follow-up operational actions.

No output is permission to restart, scale, sync, purge, restore, rotate, or reconfigure anything. Runbooks separate observation from change and require owner approval for risky actions.
