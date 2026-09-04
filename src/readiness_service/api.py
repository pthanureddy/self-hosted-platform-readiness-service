"""FastAPI transport for readiness analysis."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from readiness_service.engine import analyze_snapshot
from readiness_service.logging import configure_logging, get_logger
from readiness_service.models import AnalysisResult, ErrorDetail, PlatformSnapshot
from readiness_service.telemetry import configure_tracing

REQUESTS = Counter("readiness_http_requests_total", "HTTP requests", ["method", "route", "status"])
ANALYSES = Counter("readiness_analyses_total", "Completed analyses", ["outcome"])
ANALYSIS_SECONDS = Histogram("readiness_analysis_duration_seconds", "Analysis duration")
SERVICE_READY = True


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    tracing = configure_tracing(app)
    get_logger().info("service_started", tracing_enabled=tracing)
    yield
    get_logger().info("service_stopped")


app = FastAPI(
    title="Self-Hosted Platform Readiness Service",
    version="0.1.0",
    description="Read-only analysis of caller-supplied operational snapshots.",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_context(request: Request, call_next: Any) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))[:128]
    started = time.perf_counter()
    structlog.contextvars.bind_contextvars(request_id=request_id)
    try:
        response = cast(Response, await call_next(request))
    except Exception:
        get_logger().exception(
            "unhandled_request_error", method=request.method, path=request.url.path
        )
        response = JSONResponse(
            status_code=500,
            content=ErrorDetail(
                code="internal_error",
                message="The request could not be completed.",
                request_id=request_id,
            ).model_dump(mode="json"),
        )
    response.headers["x-request-id"] = request_id
    route = request.scope.get("route")
    route_label = getattr(route, "path", "unmatched")
    REQUESTS.labels(request.method, route_label, str(response.status_code)).inc()
    get_logger().info(
        "request_completed",
        method=request.method,
        route=route_label,
        status=response.status_code,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )
    structlog.contextvars.clear_contextvars()
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = request.headers.get("x-request-id", "unknown")[:128]
    issues = [
        {"path": ".".join(str(part) for part in error["loc"]), "type": error["type"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=ErrorDetail(
            code="validation_error",
            message="The snapshot does not match the required schema.",
            request_id=request_id,
            issues=issues,
        ).model_dump(mode="json"),
    )


@app.get("/health/live", tags=["health"])
def liveness() -> dict[str, str]:
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
def readiness() -> JSONResponse:
    return JSONResponse(
        status_code=200 if SERVICE_READY else 503,
        content={"status": "ready" if SERVICE_READY else "not_ready"},
    )


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post(
    "/v1/analyze",
    response_model=AnalysisResult,
    responses={422: {"model": ErrorDetail}, 500: {"model": ErrorDetail}},
    tags=["analysis"],
)
def analyze(snapshot: PlatformSnapshot) -> AnalysisResult:
    try:
        with ANALYSIS_SECONDS.time():
            result = analyze_snapshot(snapshot)
    except Exception:
        ANALYSES.labels("error").inc()
        raise
    else:
        ANALYSES.labels("success").inc()
    get_logger().info(
        "snapshot_analyzed",
        snapshot_id=snapshot.metadata.snapshot_id,
        environment=snapshot.metadata.environment,
        findings=result.summary.total,
    )
    return result
