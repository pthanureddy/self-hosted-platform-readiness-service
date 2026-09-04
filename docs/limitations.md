# Limitations

- This project has no automated remediation and deliberately has no credentials for a target platform.
- It analyzes exported point-in-time evidence; missing, delayed, sampled, or manipulated exports can produce misleading findings.
- Thresholds are illustrative defaults, not customer SLOs, recovery objectives, or compliance policy.
- Backup rules inspect metadata only. They do not read an object or demonstrate a successful restore.
- Queue rates in one snapshot do not establish a trend; a second sample is required.
- Probe results describe one configured vantage point unless the exporter says otherwise.
- Telemetry coverage flags indicate reported availability, not semantic correctness or complete instrumentation.
- The deployment examples have not been presented as live customer, production, or on-call operations.
- The local Compose services use ephemeral storage and anonymous Grafana viewer access for a developer lab. They are not a production monitoring design.
- The project makes no affiliation claim with any platform vendor or operator.

Before real use, define approved thresholds, data classification, exporter integrity, authentication, tenancy, retention, ownership, escalation paths, change management, and recovery-test procedure.
