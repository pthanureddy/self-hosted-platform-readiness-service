# Limitations

- This project has no automated remediation and deliberately has no credentials for a target platform.
- It analyzes exported point-in-time evidence; missing, delayed, sampled, or manipulated exports can produce misleading findings.
- Thresholds are illustrative defaults, not customer SLOs, recovery objectives, or compliance policy.
- Backup rules group supplied objects by bucket and caller-defined logical stream, then inspect only the latest object's age/protection metadata and the stream's latest restore timestamp. They do not prove export completeness, read an object, or demonstrate a successful restore.
- Queue rates in one snapshot do not establish a trend; a second sample is required.
- Probe results describe one configured vantage point unless the exporter says otherwise.
- Telemetry coverage flags indicate reported availability, not semantic correctness or complete instrumentation.
- The deployment examples have not been presented as live customer, production, or on-call operations.
- The local Compose services use ephemeral storage and anonymous Grafana viewer access for a developer lab. The collector exports to debug only; Prometheus remote write and log shipping are absent. Mimir/Loki/Tempo files and datasources are configuration-compatibility examples, not a production monitoring design.
- The chart's GHCR image is an external reference only. This repository does not claim that an image, the `v0.1.0` Git tag, or any Argo CD Application has been published or applied.
- The project makes no affiliation claim with any platform vendor or operator.

Before real use, define approved thresholds, data classification, exporter integrity, authentication, tenancy, retention, ownership, escalation paths, change management, and recovery-test procedure.
