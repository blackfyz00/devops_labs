FROM python:3.12-slim

WORKDIR /app

# Установка системных зависимостей для Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen

# Установка браузеров Playwright
RUN uv run playwright install --with-deps chromium

COPY src/ ./src/
COPY scripts/ ./scripts/

CMD ["uv", "run", "-m", "src.main"]
