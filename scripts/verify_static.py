"""Dependency-light repository policy checks used by CI."""

from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    yaml_files = sorted(
        path
        for path in ROOT.rglob("*.yaml")
        if "templates" not in path.parts and ".venv" not in path.parts
    )
    errors: list[str] = []
    for path in yaml_files:
        try:
            list(yaml.safe_load_all(path.read_text(encoding="utf-8")))
        except yaml.YAMLError as exc:
            errors.append(f"{path.relative_to(ROOT)}: {exc}")

    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    for required in ("USER 10001:10001", "HEALTHCHECK", "python:3.11.10-slim-bookworm"):
        if required not in dockerfile:
            errors.append(f"Dockerfile missing {required}")

    deployment = (ROOT / "helm" / "readiness-service" / "templates" / "deployment.yaml").read_text(
        encoding="utf-8"
    )
    for required in (
        "runAsNonRoot: true",
        "readOnlyRootFilesystem: true",
        'capabilities: {drop: ["ALL"]}',
        "automountServiceAccountToken: false",
    ):
        if required not in deployment:
            errors.append(f"Helm Deployment missing {required}")

    argo_files = sorted((ROOT / "argocd").glob("*.yaml"))
    if len(argo_files) != 3:
        errors.append(f"expected 3 Argo CD Applications, found {len(argo_files)}")
    for path in argo_files:
        document = yaml.safe_load(path.read_text(encoding="utf-8"))
        if document.get("kind") != "Application":
            errors.append(f"{path.relative_to(ROOT)} is not an Application")
        prune = document.get("spec", {}).get("syncPolicy", {}).get("automated", {}).get("prune")
        if prune is not False:
            errors.append(f"{path.relative_to(ROOT)} must keep automated pruning disabled")

    expected_runbooks = {
        "failing-workload.md",
        "network-probes.md",
        "queue-backlog.md",
        "stale-backup.md",
        "telemetry.md",
    }
    actual_runbooks = {path.name for path in (ROOT / "docs" / "runbooks").glob("*.md")}
    if actual_runbooks != expected_runbooks:
        errors.append("the five required evidence-first runbooks are not present")

    scripts = "\n".join(
        path.read_text(encoding="utf-8").lower() for path in (ROOT / "scripts").glob("*.sh")
    )
    for forbidden in (
        "kubectl delete",
        "kubectl patch",
        "kubectl apply",
        "rollout restart",
        "purge",
    ):
        if forbidden in scripts:
            errors.append(f"shell diagnostics contain forbidden mutation: {forbidden}")

    workflow = (ROOT / ".github" / "workflows" / "ci.yaml").read_text(encoding="utf-8")
    for required in ("pytest", "helm lint", "terraform test", "kind load docker-image"):
        if required not in workflow:
            errors.append(f"CI workflow missing {required}")

    if errors:
        print("\n".join(errors))
        return 1
    print(
        f"validated {len(yaml_files)} YAML files, {len(argo_files)} Argo applications, "
        f"{len(actual_runbooks)} runbooks, and repository policies"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
