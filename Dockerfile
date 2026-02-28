# syntax=docker/dockerfile:1

# Multi-stage build for optimized production image

# Stage 1: Builder - Install dependencies
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN uv sync --locked --no-install-project --no-dev

COPY . .

RUN uv sync --locked --no-editable --no-dev

# Stage 2: Runtime - Minimal production image
FROM python:3.12-slim-bookworm

# SECURITY: Create non-root user
RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid appuser --shell /bin/false --create-home appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser . .

ENV PATH="/app/.venv/bin:$PATH"

# SECURITY: Run as non-root user
USER appuser

EXPOSE 8891

CMD ["gunicorn", "app.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "-w", "4", \
     "--bind", "0.0.0.0:8891", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]
