# Codex / Claude Code Master Prompt

你正在从 0 实现 ClientGet 后端。请先完整阅读本目录中的文档，并严格以下列文件为真源：

1. `00_SOURCE_OF_TRUTH_DECISIONS.md`
2. `01_final_repaired_docs/*`
3. `02_architecture/BACKEND_ARCHITECTURE.md`
4. `02_architecture/SECURITY_RLS_AUTH_ARCHITECTURE.md`
5. `03_database/schema.sql`
6. `04_api/API_CONTRACT.md`
7. `05_services/*`
8. `06_frontend_alignment/FRONTEND_BACKEND_ALIGNMENT.md`
9. `07_implementation_plan/DEVELOPMENT_PLAN.md`
10. `07_implementation_plan/ACCEPTANCE_TEST_PLAN.md`

不要直接照搬 `00_original_sources/` 中的原始文档；它们只用于追溯。若原始文档与上述最终文档冲突，采用最终文档。

## 技术栈

- Python 3.11+
- FastAPI
- Pydantic v2
- PostgreSQL 16+
- Alembic
- asyncpg 或 SQLAlchemy 2 async
- pytest + pytest-asyncio + httpx AsyncClient

## 必须遵守

1. 四类入口：Admin / Tenant / Internal / Webhook。
2. Tenant API 必须启用 RLS，并在同一事务连接上设置 `SET LOCAL app.current_tenant_id`。
3. Admin 平台管理员使用 `platform_users`，不要混入 tenant roles。
4. Tenant roles 只能是 `admin/operator/viewer`。
5. Tenant API path slug 必须与 JWT tid/slug 交叉校验。
6. AI 调用必须走预授权/结算状态机。
7. 发送幂等必须用 `email_send_locks`，不能依赖 emails 分区表 unique。
8. Webhook 必须用 provider_event_id 幂等。
9. 分区表分页必须用 `(created_at, id)` cursor。
10. API 响应格式必须统一。

## 第一阶段任务

先完成 P0：

- 项目脚手架。
- Alembic migrations。
- Seed data。
- Auth/RBAC/RLS。
- Admin/Tenant 基础 CRUD。
- 单元测试覆盖 RLS 和 auth。

完成 P0 后再做采集、AI、发送、Webhook。

## 输出要求

每完成一个任务：

1. 写或更新测试。
2. 运行测试。
3. 说明涉及的 API、表、服务。
4. 不要跳过 RLS/权限测试。
