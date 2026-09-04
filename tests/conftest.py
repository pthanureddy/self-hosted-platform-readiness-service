from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from readiness_service.models import PlatformSnapshot

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 9, 4, 10, 0, tzinfo=UTC)


@pytest.fixture
def degraded_dict() -> dict[str, Any]:
    return json.loads((ROOT / "fixtures" / "degraded-snapshot.json").read_text(encoding="utf-8"))


@pytest.fixture
def healthy_dict() -> dict[str, Any]:
    return json.loads((ROOT / "fixtures" / "healthy-snapshot.json").read_text(encoding="utf-8"))


@pytest.fixture
def degraded_snapshot(degraded_dict: dict[str, Any]) -> PlatformSnapshot:
    return PlatformSnapshot.model_validate(degraded_dict)


@pytest.fixture
def healthy_snapshot(healthy_dict: dict[str, Any]) -> PlatformSnapshot:
    return PlatformSnapshot.model_validate(healthy_dict)
