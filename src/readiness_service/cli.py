"""Command-line interface for offline snapshot analysis."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from readiness_service.engine import analyze_snapshot
from readiness_service.models import PlatformSnapshot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Analyze an exported platform snapshot without changing it."
    )
    parser.add_argument("snapshot", type=Path, help="Path to a UTF-8 JSON snapshot")
    parser.add_argument(
        "--output", type=Path, help="Write JSON result to this path; stdout is the default"
    )
    parser.add_argument("--fail-on", choices=("never", "critical", "high"), default="never")
    return parser


def run(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        raw = json.loads(args.snapshot.read_text(encoding="utf-8"))
        snapshot = PlatformSnapshot.model_validate(raw)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        print(json.dumps({"error": "invalid_snapshot", "detail": str(exc)}), file=sys.stderr)
        return 2

    result = analyze_snapshot(snapshot)
    rendered = result.model_dump_json(indent=2)
    if args.output:
        args.output.write_text(f"{rendered}\n", encoding="utf-8")
    else:
        print(rendered)
    if args.fail_on == "critical" and result.summary.critical:
        return 3
    if args.fail_on == "high" and (result.summary.critical or result.summary.high):
        return 3
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":  # pragma: no cover
    main()
