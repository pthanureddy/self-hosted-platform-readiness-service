# DNS, HTTP, or TLS probe failure

## Evidence to preserve

Record target, probe type, timestamp, vantage point, resolver, error code, HTTP status, latency, DNS answers, certificate chain summary, and certificate expiry. Redact tokens, cookies, query secrets, and private payloads.

## Read-only checks

1. Repeat the probe from an approved second vantage point.
2. Read authoritative/recursive DNS results and TTLs.
3. Inspect route, endpoint, load-balancer, ingress, and NetworkPolicy configuration.
4. For HTTP, use a safe idempotent endpoint and compare status/latency.
5. For TLS, inspect SNI, issuer, SANs, chain, expiry, renewal controller status, and events.

## Bounded hypotheses

DNS propagation, routing, policy, endpoint, certificate, or vantage-specific failure may exist. A failed probe does not prove global unavailability.

## Escalation

Escalate after failure from two vantage points, for a user-facing outage, at the certificate owner's renewal threshold, or immediately when expiry/identity mismatch is imminent.

## Change and rollback boundary

Do not edit DNS, ingress, certificates, or network policy without owner review. Capture previous values, TTL/propagation expectations, certificate/key custody, validation criteria, and a tested rollback route.

