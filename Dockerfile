# --- Етап 1: Builder ---
FROM python:3.11-slim AS builder

WORKDIR /build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip && \
    pip wheel --no-cache-dir --wheel-dir /wheels .

# --- Етап 2: Runtime ---
FROM python:3.11-slim AS runtime

LABEL org.opencontainers.image.source="https://github.com/lyndorind/mmeln" \
      org.opencontainers.image.description="mmeln containerized Python application"

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN useradd --create-home --shell /bin/bash appuser

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels mmeln && \
    rm -rf /wheels

USER appuser

ENTRYPOINT ["python", "-m", "mmeln.app"]