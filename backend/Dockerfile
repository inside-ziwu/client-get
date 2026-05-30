FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY 03_database ./03_database
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts

RUN pip install --no-cache-dir uv && uv pip install --system .

# 启动脚本：先跑迁移，再拉起服务
RUN printf '#!/bin/sh\nset -e\necho ">>> alembic upgrade head"\nalembic upgrade head\necho ">>> starting uvicorn"\nexec uvicorn app.main:app --host 0.0.0.0 --port 8000\n' > /start.sh && chmod +x /start.sh

CMD ["/start.sh"]
