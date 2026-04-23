FROM python:3.12-slim

WORKDIR /app

# 安装 uv 并同步依赖
COPY pyproject.toml uv.lock ./
RUN pip install uv && uv sync --frozen --no-dev

COPY alembic.ini ./
COPY alembic/ alembic/
COPY src/ src/

EXPOSE 9000
