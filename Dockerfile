FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY meteo ./meteo
EXPOSE 8000
CMD [".venv/bin/fastapi", "run", "meteo/main.py", "--port", "8000"]
