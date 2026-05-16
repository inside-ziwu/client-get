# Deployment

## 目标

- 目标环境：Linux Docker 主机
- 发布单元：`postgres`、`backend`、`collection-scheduler`、`collection-worker`、`scoring-worker`、`sending-worker`
- 反向代理：Nginx / Caddy / Traefik 均可，统一回源到 `backend:8000`

## 环境准备

1. 复制 `.env.example` 为 `.env`
2. 设置生产密钥：
   - `JWT_SECRET`
   - `INTERNAL_SERVICE_SECRET`
   - `ENGAGELAB_WEBHOOK_SECRET`
   - `DATA_SOURCE_ENCRYPTION_KEY`
3. 区分宿主机和容器内数据库地址：
   - 宿主机命令默认读取 `DATABASE_URL`、`SYNC_DATABASE_URL`
   - Docker Compose 生产运行默认读取 `DOCKER_DATABASE_URL`、`DOCKER_SYNC_DATABASE_URL`
   - 如果沿用仓内 `postgres` 服务，保持默认 `postgres:5432` 即可，不要把容器内连接写成 `localhost:5432`
4. 设置前端来源域名：
   - `ALLOWED_ORIGINS=https://admin.example.com,https://tenant.example.com`
5. 如果启用真实发送或 AI：
   - `ENGAGELAB_*`
   - OpenRouter 改为租户级 API key，不再配置全局 `OPENROUTER_API_KEY`
   - 上线后需由平台管理员或租户管理员为对应租户写入 OpenRouter key
6. 采集 worker 相关参数：
   - `COLLECTION_SCHEDULER_SLEEP_SECONDS`
   - `COLLECTION_WORKER_SLEEP_SECONDS`
   - `COLLECTION_TASK_LEASE_SECONDS`
   - `COLLECTION_WORKER_LIMIT`
   - `COLLECTION_HEARTBEAT_INTERVAL_SECONDS`

## 启动顺序

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build postgres backend collection-scheduler collection-worker scoring-worker sending-worker
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python -m alembic -c alembic.ini upgrade head
```

如果是首次环境，需要再执行：

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python scripts/bootstrap_platform_admin.py
```

如果要准备演示数据：

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python scripts/seed_demo_data.py
```

## 反向代理要求

- Admin 前端把 API 指到 `https://api.example.com`
- Tenant 前端把 API 指到 `https://api.example.com`
- 后端实际路径为：
  - `https://api.example.com/admin/api/v1/*`
  - `https://api.example.com/t/{slug}/api/v1/*`
  - `https://api.example.com/internal/api/v1/*`
  - `https://api.example.com/webhooks/*`

## CORS

- `ALLOWED_ORIGINS` 只填写真实前端域名
- 本地开发值不要带到生产
- 如果增加新的预发布环境，同步更新 `ALLOWED_ORIGINS`

## Worker 说明

- `collection-scheduler`：持续回收过期 lease 的采集任务，并把 `collection_keywords` 聚合调度为 `collection_tasks`
- `collection-worker`：持续执行采集任务 `claim -> provider -> heartbeat -> submit-result|mark-failed`
- `scoring-worker`：持续执行评分队列 claim/score/submit-result
- `sending-worker`：持续执行待发送邮件 claim/send/mark-sent|mark-failed
- 四个后台单元都支持 `--once`，但生产必须使用守护模式
- 当前仓库中的 collection provider adapter 仍是骨架；未接入的采集源会真实失败并进入重试/失败路径，不会伪造成功结果
- 生产 compose 已把运行命令切到 `python ...`，避免容器启动时再次创建 `.venv`

## 健康检查

- 应用健康检查：`GET /health`
- 数据库健康检查：`pg_isready`
- 发布后建议人工核验：
  - Admin 登录
  - Tenant 登录
  - `collection-scheduler` / `collection-worker` / `scoring-worker` / `sending-worker` 容器状态
  - webhook secret 是否正确
