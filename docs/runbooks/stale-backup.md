# Stale backup or missing restore evidence

## Evidence to preserve

Record inventory scope, bucket/key, object timestamp and size, encryption/checksum metadata, backup job result, retention policy, recovery objectives, and latest isolated restore-test record. Do not download data into an unapproved environment.

## Read-only checks

1. Confirm the export represents the complete expected prefix and latest version.
2. Read scheduler history and failure events.
3. Inspect object metadata, versioning, retention/immutability, and encryption policy with read-only API calls.
4. Compare age to an approved RPO, not the example threshold alone.
5. Review the last restore-test evidence and its data-integrity checks.

## Bounded hypotheses

The job may have failed, written elsewhere, been omitted from the export, or produced an object without reported protection metadata. Metadata alone cannot prove recoverability.

## Escalation

Escalate immediately when a complete inventory confirms missed RPO, required encryption/integrity is absent, retention is at risk, or no recovery test exists within policy.

## Change and rollback boundary

Never overwrite, delete, expire, restore over production, or weaken immutability during triage. Run restores only in an isolated approved destination with capacity, access controls, integrity criteria, cleanup plan, and named owner.

