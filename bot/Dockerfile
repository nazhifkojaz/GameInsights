FROM ghcr.io/astral-sh/uv:python3.12-alpine
WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev --no-workspace

COPY app/ app/
CMD ["uv", "run", "python", "-m", "app.main"]
