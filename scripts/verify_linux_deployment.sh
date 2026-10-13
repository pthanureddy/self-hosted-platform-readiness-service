#!/usr/bin/env bash
set -Eeuo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"
mkdir -p artifacts wheelhouse
python -m pip wheel . --wheel-dir wheelhouse
application_wheel="$(find "$repository_root/wheelhouse" -maxdepth 1 -name 'self_hosted_platform_readiness_service-*.whl' -print -quit)"
application_sha="$(sha256sum "$application_wheel" | cut -d ' ' -f 1)"
python - "$application_wheel" "$application_sha" "$repository_root/wheelhouse" <<'PY'
import json
from pathlib import Path
import sys
wheel, digest, wheelhouse = sys.argv[1:]
Path("artifacts/deployment-vars.json").write_text(json.dumps({
    "readiness_wheel": wheel, "readiness_wheelhouse": wheelhouse,
    "readiness_expected_sha256": digest,
}), encoding="utf-8")
PY
ansible-playbook -i ansible/inventory.ini ansible/deploy.yaml \
  --extra-vars @artifacts/deployment-vars.json | tee artifacts/ansible-first.log
ansible-playbook -i ansible/inventory.ini ansible/deploy.yaml \
  --extra-vars @artifacts/deployment-vars.json | tee artifacts/ansible-second.log
grep -Eq 'changed=0[[:space:]]+unreachable=0[[:space:]]+failed=0' artifacts/ansible-second.log
python -m readiness_service.deployment --fixture fixtures/degraded-snapshot.json \
  --output artifacts/linux-deployment.json
systemctl show readiness-lab --property=User,NoNewPrivileges,ProtectSystem,ProtectHome,PrivateTmp \
  | tee artifacts/systemd-security.txt
grep -qx 'User=readiness-lab' artifacts/systemd-security.txt
grep -qx 'NoNewPrivileges=yes' artifacts/systemd-security.txt
grep -qx 'ProtectSystem=strict' artifacts/systemd-security.txt
grep -qx 'ProtectHome=yes' artifacts/systemd-security.txt
grep -qx 'PrivateTmp=yes' artifacts/systemd-security.txt

# Force candidate failure with an occupied port serving unrelated HTTP content.
python -m http.server 18081 --bind 127.0.0.1 >artifacts/busy-port.log 2>&1 &
busy_pid=$!
trap 'kill "$busy_pid" 2>/dev/null || true' EXIT
python - <<'PY'
import socket
import time
for attempt in range(30):
    try:
        with socket.create_connection(("127.0.0.1", 18081), timeout=1):
            break
    except OSError:
        time.sleep(0.1)
else:
    raise SystemExit("Busy-port fixture did not start")
PY
if ansible-playbook -i ansible/inventory.ini ansible/deploy.yaml \
    --extra-vars @artifacts/deployment-vars.json --extra-vars '{"readiness_port":18081}' \
    >artifacts/ansible-rollback.log 2>&1; then
  echo "Expected busy-port deployment to fail" >&2
  exit 1
fi
grep -q 'Candidate readiness failed; previous unit restored' artifacts/ansible-rollback.log
python -m readiness_service.deployment --fixture fixtures/degraded-snapshot.json \
  --output artifacts/linux-recovered.json
echo "Linux install, zero-change reapply, seven checks, confinement and rollback passed"
