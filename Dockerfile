# 概要: 依存を固定してインストールし、非rootユーザーでAPIを起動するイメージを作成します。
FROM ghcr.io/astral-sh/uv:0.13.0 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY src ./src
COPY alembic ./alembic
COPY alembic.ini README.md ./
RUN uv sync --frozen --no-dev && useradd --create-home app
USER app
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "sns_office.main:app", "--host", "0.0.0.0", "--port", "8000"]
