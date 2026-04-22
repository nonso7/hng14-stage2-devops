# syntax=docker/dockerfile:1.7

FROM python:3.12-slim-bookworm AS builder
WORKDIR /build
COPY requirements.txt .
RUN python -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip==24.3.1 \
 && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim-bookworm AS runtime
# hadolint ignore=DL3008
RUN apt-get update \
 && apt-get upgrade -y \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd --system --gid 10001 appuser \
 && useradd  --system --uid 10001 --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
COPY --from=builder /opt/venv /opt/venv
WORKDIR /app
COPY --chown=appuser:appuser worker.py healthcheck.py ./
USER appuser
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "/app/healthcheck.py"]
CMD ["python", "-u", "worker.py"]
