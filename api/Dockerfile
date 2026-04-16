FROM ghcr.io/astral-sh/uv:python3.12-alpine
WORKDIR /app

COPY pyproject.toml .
RUN uv sync --no-dev --no-workspace

COPY app/ app/
COPY alembic.ini .
COPY alembic/ alembic/
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
