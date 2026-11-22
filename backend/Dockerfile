FROM python:3.12-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Копируем файлы проекта
COPY pyproject.toml .
RUN uv sync --no-install-project

COPY . .
RUN uv sync

ENV PORT=8000
EXPOSE $PORT

CMD ["uv", "run", "uvicorn", "src.api:app", "--host", "0.0.0.0", "--port", "$PORT"]