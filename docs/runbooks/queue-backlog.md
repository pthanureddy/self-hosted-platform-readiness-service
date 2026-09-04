# RabbitMQ queue backlog

## Evidence to preserve

Record vhost, queue, ready/unacknowledged counts, consumer count, publish/deliver rates, oldest age, policies, and two or more time-bounded samples. Never export message bodies by default.

## Read-only checks

1. Confirm queue name/vhost and sample age.
2. Compare rates and depth across multiple samples.
3. Inspect bindings, consumer connections, channel state, and consumer deployment readiness.
4. Review redacted dead-letter counts and message metadata.
5. Correlate consumer logs, dependency latency, and resource saturation.

## Bounded hypotheses

Consumer unavailability, inadequate capacity, poison messages, downstream latency, or a legitimate burst may explain the evidence. One snapshot cannot establish a trend or cause.

## Escalation

Escalate when the owner-defined depth/age threshold is breached, consumers remain absent, publish rate continues exceeding delivery, or processing correctness is at risk.

## Change and rollback boundary

Do not purge, requeue, move, acknowledge, change TTL, or scale consumers from this finding. These actions can duplicate or lose work. Require queue-owner approval, capture starting counts, define a stop condition, and retain a recovery route before change.

