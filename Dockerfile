# Dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock README.md ./
RUN pip install --no-cache-dir uv && uv sync --frozen --no-dev

RUN uv run playwright install --with-deps chromium

COPY src/ ./src/

CMD ["uv", "run", "-m", "src.main"]
