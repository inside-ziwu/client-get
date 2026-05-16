# Launch Checklist

## 发布前

- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build postgres backend collection-scheduler collection-worker scoring-worker sending-worker`
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python -m alembic -c alembic.ini upgrade head`
- [ ] `uv run pytest -q`
- [ ] `uv run python scripts/run_collection_scheduler_worker.py --once`
- [ ] `uv run python scripts/run_collection_worker.py --once`
- [ ] `uv run python scripts/run_scoring_worker.py --once`
- [ ] `uv run python scripts/run_sending_worker.py --once`
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml exec backend python scripts/seed_demo_data.py` 已按需要执行

## 配置

- [ ] `JWT_SECRET` 已替换
- [ ] `DATA_SOURCE_ENCRYPTION_KEY` 已替换
- [ ] `INTERNAL_SERVICE_SECRET` 已替换
- [ ] `ENGAGELAB_WEBHOOK_SECRET` 已替换
- [ ] `DOCKER_DATABASE_URL` / `DOCKER_SYNC_DATABASE_URL` 已指向容器可访问的数据库主机
- [ ] `COLLECTION_SCHEDULER_SLEEP_SECONDS` / `COLLECTION_WORKER_SLEEP_SECONDS` / `COLLECTION_TASK_LEASE_SECONDS` 已按环境核对
- [ ] `ALLOWED_ORIGINS` 只包含真实前端域名
- [ ] `VITE_API_BASE_URL` 已指向后端 API 域名
- [ ] Admin 初始账号已创建并验证

## 第三方

- [ ] EngageLab 发送配置已核对
- [ ] webhook 地址已配置到 `/webhooks/engagelab`
- [ ] 需要启用 AI 的租户已完成 OpenRouter API key 配置并验证状态

## 浏览器冒烟

- [ ] Admin 登录成功
- [ ] Tenant 登录成功
- [ ] `globex-pcb` 能加载 Dashboard、Companies、Templates、Send Plans、Settings
- [ ] `acme-pcb` 能进入 onboarding
- [ ] 情报中心与通知能显示真实数据

## 发布后

- [ ] `backend` 容器健康
- [ ] `collection-scheduler` 容器健康
- [ ] `collection-worker` 容器健康
- [ ] `scoring-worker` 容器健康
- [ ] `sending-worker` 容器健康
- [ ] `/health` 返回正常
- [ ] 日志中无连续 5xx / worker 重启
