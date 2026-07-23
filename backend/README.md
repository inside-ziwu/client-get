# ClientGet Backend

FastAPI + PostgreSQL + Alembic + 后台 worker。**完整文档见根目录 [README.md](../README.md)**：架构 §4、行为口径 §5、环境与部署 §7、本地开发 §8、运维脚本速查 §9。

四类路由入口：`/admin/api/v1`（管理端）、`/t/{slug}/api/v1`（租户端）、`/internal/api/v1`（worker 内部调用）、`/webhooks`。

## 快速开始

```bash
uv sync
# 配置 backend/.env.local（变量清单见 .env.example；开发库为 Neon 云 PG，见 README §7）
uv run alembic -c alembic.ini upgrade head
uv run uvicorn app.main:app --reload        # http://localhost:8000
uv run pytest -q                            # 测试
uv run python scripts/run_sending_worker.py --once   # 发送 worker 单轮
```

## Demo 联调数据

```bash
uv run python scripts/seed_demo_data.py
```

生成两个 demo 租户（密码 `ChangeMe123!`）：`globex-pcb`（已完成 onboarding，适合直接联调仪表盘/模板/发送计划/情报）与 `acme-pcb`（保留首次改密与 onboarding 流程）。平台管理员由 `.env.local` 的 `ADMIN_EMAIL` / `ADMIN_PASSWORD` 引导创建。

生产部署走 GitHub Actions `workflow_dispatch` → 阿里云 ACR → Sealos（详见 README §7 与 [AGENTS.md](../AGENTS.md) §6）；生产数据库操作纪律见 AGENTS.md §3。
