FROM ghcr.io/astral-sh/uv:python3.12-alpine
WORKDIR /app

RUN addgroup -S appgroup && adduser -S appuser -G appgroup

COPY pyproject.toml .
RUN uv sync --no-dev --no-workspace

COPY app/ app/

RUN chown -R appuser:appgroup /app
USER appuser

CMD ["uv", "run", "python", "-m", "app.main"]
