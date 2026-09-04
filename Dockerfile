# syntax=docker/dockerfile:1.7
FROM python:3.11.10-slim-bookworm AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN python -m pip install --upgrade "pip==25.0.1" \
    && python -m pip wheel --wheel-dir /wheels .[otel]

FROM python:3.11.10-slim-bookworm AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080
RUN groupadd --system --gid 10001 readiness \
    && useradd --system --uid 10001 --gid readiness --home-dir /nonexistent --shell /usr/sbin/nologin readiness \
    && python -m venv /opt/venv
COPY --from=builder /wheels /wheels
RUN /opt/venv/bin/pip install --no-cache-dir /wheels/*.whl \
    && rm -rf /wheels \
    && find /opt/venv -type d -name __pycache__ -prune -exec rm -rf {} +
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/ready', timeout=2)"]
ENTRYPOINT ["uvicorn", "readiness_service.api:app"]
CMD ["--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--proxy-headers", "--forwarded-allow-ips", ""]

