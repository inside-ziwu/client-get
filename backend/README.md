# ClientGet Backend

ClientGet 后端采用 `FastAPI + PostgreSQL`，按蓝图提供四类入口：

- Admin API: `/admin/api/v1/*`
- Tenant API: `/t/{slug}/api/v1/*`
- Internal API: `/internal/api/v1/*`
- Webhook: `/webhooks/*`

## 本地运行

```bash
docker compose up -d postgres
uv sync
uv run alembic -c alembic.ini upgrade head
uv run uvicorn app.main:app --reload
```

默认平台管理员：

- email: `admin@example.com`
- password: `change-me-now`

## Demo Seed

```bash
uv run python scripts/seed_demo_data.py
```

默认 demo 租户账号：

- `globex-pcb` / `owner@globex.example.com` / `ChangeMe123!`
- `acme-pcb` / `owner@acme.example.com` / `ChangeMe123!`

其中 `globex-pcb` 已完成 onboarding，适合直接联调 Dashboard、模板、发送计划、情报中心；`acme-pcb` 保留首次改密与 onboarding 流程。

## 测试与 Worker

```bash
uv run pytest -q
uv run python scripts/run_collection_scheduler_worker.py --once
uv run python scripts/run_collection_worker.py --once
uv run python scripts/run_scoring_worker.py --once
uv run python scripts/run_sending_worker.py --once
uv run python scripts/maintain_partitions.py --months-ahead 1
uv run python scripts/migrate_legacy.py --dry-run
```

持续运行 worker 的方式见 [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)。

## 环境变量

参考 [.env.example](.env.example)。

生产必须至少覆盖：

- `APP_ENV=production`
- `DEBUG=false`
- `JWT_SECRET`
- `DATABASE_URL`
- `SYNC_DATABASE_URL`
- `DOCKER_DATABASE_URL`
- `DOCKER_SYNC_DATABASE_URL`
- `ALLOWED_ORIGINS`
- `INTERNAL_SERVICE_SECRET`
- `ENGAGELAB_WEBHOOK_SECRET`
- `DATA_SOURCE_ENCRYPTION_KEY`
- `COLLECTION_SCHEDULER_SLEEP_SECONDS`
- `COLLECTION_WORKER_SLEEP_SECONDS`
- `COLLECTION_TASK_LEASE_SECONDS`
- `COLLECTION_WORKER_LIMIT`
- `COLLECTION_HEARTBEAT_INTERVAL_SECONDS`

如果需要真实发送或 AI 调用，再补：

- `ENGAGELAB_BASE_URL`
- `ENGAGELAB_API_KEY`
- `ENGAGELAB_SEND_PATH`
- `ENGAGELAB_AUTH_HEADER`
- `ENGAGELAB_AUTH_SCHEME`
- `ENGAGELAB_TIMEOUT_SECONDS`

OpenRouter 不再使用全局环境变量。每个租户的 OpenRouter API key 由平台管理员或租户管理员在页面内按租户单独配置，后端只保存加密后的租户级配置。

## Docker 主机部署

生产部署建议使用：

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python -m alembic -c alembic.ini upgrade head
```

说明：

- 宿主机本地调试仍使用 `DATABASE_URL=...@localhost:5432/...`
- Docker 主机部署时，compose 运行容器会优先读取 `DOCKER_DATABASE_URL` 与 `DOCKER_SYNC_DATABASE_URL`
- 仓内默认值已经指向 `postgres:5432`，避免容器内错误连接到 `localhost`

`docker-compose.prod.yml` 会额外启动：

- `backend`
- `collection-scheduler`
- `collection-worker`
- `scoring-worker`
- `sending-worker`

发布顺序、CORS、反向代理、回滚说明见：

- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- [docs/LAUNCH_CHECKLIST.md](docs/LAUNCH_CHECKLIST.md)
- [docs/ROLLBACK.md](docs/ROLLBACK.md)

## 关键说明

- 评分支持 `trigger(mode=inline)` 和 `trigger(mode=enqueue)`；生产建议走队列合同。
- 采集支持独立的 `collection-scheduler` 与 `collection-worker` 运行单元；当前 provider adapter 仍是骨架实现，未接入的采集源会真实失败，不会伪造成功结果。
- 发送 worker 未配置 EngageLab 时会按 provider 失败分支落库，不会伪造成功发送。
- 模板和发送渲染内容都经过 HTML allowlist 清洗。
- `/emails` 支持稳定 cursor 分页。
- demo seed 使用合法示例邮箱，不再使用 `.test` 保留域名，避免前端登录被 schema 拒绝。

更多实现约束见：

- [docs/ASSUMPTIONS.md](docs/ASSUMPTIONS.md)
- [docs/IMPLEMENTATION_NOTES.md](docs/IMPLEMENTATION_NOTES.md)
- [docs/OPEN_QUESTIONS.md](docs/OPEN_QUESTIONS.md)
