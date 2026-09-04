from __future__ import annotations

import builtins

from fastapi import FastAPI

from readiness_service.logging import configure_logging, get_logger
from readiness_service.telemetry import configure_tracing


def test_logging_configuration_returns_bound_logger(monkeypatch) -> None:
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    configure_logging()
    assert get_logger() is not None


def test_tracing_disabled_without_endpoint(monkeypatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert configure_tracing(FastAPI()) is False


def test_tracing_missing_optional_packages_is_safe(monkeypatch) -> None:
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://collector:4318")
    real_import = builtins.__import__

    def import_without_otel(name, *args, **kwargs):
        if name.startswith("opentelemetry"):
            raise ImportError("simulated optional dependency absence")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", import_without_otel)
    assert configure_tracing(FastAPI()) is False
