# Linux service deployment

This path installs the existing readiness API on a disposable Debian/Ubuntu
systemd host. It adds an alternative to Kubernetes deployment, using Ansible,
Bash, Python virtual environments and explicit transport checks. It does not
install or communicate with radars, cameras, sensors or customer systems.

## Requirements and execution

Use a disposable Ubuntu24.04 host with Python3.11+, systemd, Bash, curl,
`sha256sum`, ShellCheck and a sudo-capable operator. The verification script
changes only its named lab service, user and `/opt/readiness-service-lab`
installation; it leaves immutable release directories for inspection.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]' 'ansible-core>=2.18,<2.20'
ansible-playbook -i ansible/inventory.ini ansible/deploy.yaml --syntax-check
shellcheck scripts/verify_linux_deployment.sh
bash scripts/verify_linux_deployment.sh
```

The Ansible controller must be Linux. Windows can run the Python unit tests
and Git Bash syntax checks; that does not establish Linux installation success.
The script expects passwordless sudo in its disposable CI host. For an attended
installation, prepare the wheelhouse and variables, then invoke the same
playbook with `--ask-become-pass`. No passwords are stored in inventory.

`pip wheel . --wheel-dir wheelhouse` prepares application and dependency
wheels. The script records the application wheel SHA256 and passes the exact
controller paths to Ansible. The role checks that digest before target changes.
Ansible installs from the copied wheelhouse with `--no-index`. Application
digest identity is not a signature check or a hash lock of every dependency.
Dependencies are resolved while preparing the wheelhouse; preserve that
wheelhouse to replay the same artifacts. Production supply-chain policy would
need independently approved dependency locks/signatures and artifact storage.

## Architecture and behavior

Each application digest gets a root-owned release directory and virtual
environment. The non-login `readiness-lab` user reads it but cannot change it.
The templated systemd unit binds only `127.0.0.1`, drops capability privileges,
uses `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome`
and `UMask=0077`. It restarts on process failure. These controls are a bounded
configuration, not proof of a security audit or availability SLA.

Unchanged reapply uses the same wheel identity and service configuration; the
verification script requires zero Ansible changes on its second application.
Candidate configuration is activated only after installation. If readiness
fails, the previous unit text is restored and its service restarted. A failed
first installation stops/disables its new service and removes only its unit.
Package install and artifact copy failures occur before unit activation.
Recovery is attempted, not guaranteed in an arbitrary broken operating system.
Persistent application-state migrations are outside this read-only service.

The Bash campaign uses an occupied loopback port to make a candidate fail.
It requires a failed deployment exit code, the recorded recovery message and
seven passing checks on the restored original service.

## Verification outputs

`readiness-deployment-check --fixture fixtures/degraded-snapshot.json` checks
TCP connection, liveness, readiness, expected diagnostic finding, correlation
header, private-value rejection and the metrics endpoint. Reports contain
check results, not the input fixture or invalid private probe value. HTTP
reads are bounded at512KiB and timeouts at0.1-10seconds; proxies are disabled.
Only an explicit HTTP loopback base URL is accepted. TLS, firewall rules,
authentication, physical network topology and hardware protocols are outside scope.

The `linux-deployment` CI job saves first/second application logs, actual service
checks, systemd confinement properties, failed-candidate/recovery logs and a
post-recovery check report. Unit tests use local HTTP fixtures; hosted CI uses
the actual installed API. The existing pipeline also tests the Python service,
container/Helm/kind path and two Terraform mock plan cases. Terraform does not
provision a VM. Containers and runners do not establish hypervisor administration.

## Limits and maintenance

The inventory names localhost deliberately. Add approved hosts and explicit
host-key/SSH configuration before any external use. This lab's unauthenticated
API remains loopback-only; external access requires a separate reviewed access
layer. No production or client installation, uptime gain, hardware integration,
Linux certification or travel experience is inferred from these artifacts.

Implementation, tests and documentation used Codex assistance. Read the source,
inspect the retained artifacts and understand the boundaries before adapting it.
Ansible module references: [systemd service](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/systemd_service_module.html)
and [pip virtual environments](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/pip_module.html).
