from __future__ import annotations

import json
from pathlib import Path

from readiness_service.cli import build_parser, run


def test_parser_defaults() -> None:
    args = build_parser().parse_args(["snapshot.json"])
    assert args.fail_on == "never"
    assert args.output is None


def test_cli_prints_json(capsys, tmp_path: Path, healthy_dict: dict) -> None:
    source = tmp_path / "snapshot.json"
    source.write_text(json.dumps(healthy_dict), encoding="utf-8")
    assert run([str(source)]) == 0
    assert json.loads(capsys.readouterr().out)["snapshot_id"] == "demo-healthy-001"


def test_cli_writes_output(tmp_path: Path, degraded_dict: dict) -> None:
    source = tmp_path / "snapshot.json"
    output = tmp_path / "result.json"
    source.write_text(json.dumps(degraded_dict), encoding="utf-8")
    assert run([str(source), "--output", str(output)]) == 0
    assert json.loads(output.read_text(encoding="utf-8"))["findings"]


def test_cli_fail_on_high(tmp_path: Path, degraded_dict: dict) -> None:
    source = tmp_path / "snapshot.json"
    source.write_text(json.dumps(degraded_dict), encoding="utf-8")
    assert run([str(source), "--fail-on", "high"]) == 3


def test_cli_fail_on_critical(tmp_path: Path, healthy_dict: dict) -> None:
    healthy_dict["kubernetes_workloads"][0].update(ready_replicas=0, unavailable_seconds=900)
    source = tmp_path / "snapshot.json"
    source.write_text(json.dumps(healthy_dict), encoding="utf-8")
    assert run([str(source), "--fail-on", "critical"]) == 3


def test_cli_critical_mode_allows_high_only(tmp_path: Path, healthy_dict: dict) -> None:
    healthy_dict["kubernetes_workloads"][0].update(restart_count=20)
    source = tmp_path / "snapshot.json"
    source.write_text(json.dumps(healthy_dict), encoding="utf-8")
    assert run([str(source), "--fail-on", "critical"]) == 0


def test_cli_invalid_json(capsys, tmp_path: Path) -> None:
    source = tmp_path / "snapshot.json"
    source.write_text("{bad", encoding="utf-8")
    assert run([str(source)]) == 2
    assert "invalid_snapshot" in capsys.readouterr().err


def test_cli_invalid_schema(capsys, tmp_path: Path) -> None:
    source = tmp_path / "snapshot.json"
    source.write_text("{}", encoding="utf-8")
    assert run([str(source)]) == 2
    assert "invalid_snapshot" in capsys.readouterr().err


def test_cli_missing_file(capsys, tmp_path: Path) -> None:
    assert run([str(tmp_path / "missing.json")]) == 2
    assert "invalid_snapshot" in capsys.readouterr().err
