"""Command-line interface for offline snapshot analysis."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from readiness_service.engine import analyze_snapshot
from readiness_service.models import MAX_VALIDATION_ISSUES, PlatformSnapshot


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
        content = args.snapshot.read_text(encoding="utf-8")
    except OSError:
        print(json.dumps({"error": "snapshot_unreadable"}), file=sys.stderr)
        return 2
    try:
        raw = json.loads(content)
    except json.JSONDecodeError as exc:
        print(
            json.dumps({"error": "invalid_json", "line": exc.lineno, "column": exc.colno}),
            file=sys.stderr,
        )
        return 2
    try:
        snapshot = PlatformSnapshot.model_validate(raw)
    except ValidationError as exc:
        errors = exc.errors()
        issues = [
            {"path": ".".join(str(part) for part in error["loc"]), "type": error["type"]}
            for error in errors[:MAX_VALIDATION_ISSUES]
        ]
        print(
            json.dumps(
                {
                    "error": "invalid_snapshot",
                    "issues": issues,
                    "total_issues": len(errors),
                    "truncated": len(errors) > MAX_VALIDATION_ISSUES,
                }
            ),
            file=sys.stderr,
        )
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
