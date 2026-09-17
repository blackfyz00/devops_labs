FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

FROM python:3.12-slim
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1
WORKDIR /app
RUN python -m playwright install --with-deps chromium && \
    apt-get purge -y --auto-remove && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY src ./src
RUN mkdir -p out
# Запускаем скрапер
CMD ["python", "-m", "src.main"]
