# Agent Progress

## Current Phase

- 前后端联调与上线前准备已完成一轮闭环，当前状态为“前端已接真实后端，双仓可构建、后端可运行、demo seed 可支撑浏览器联调，Docker 主机发布演练已跑通”。

## 本轮完成

- 完成“采集独立运行单元”第一阶段落地：
  - 新增设计文档：`docs/superpowers/specs/2026-04-22-collection-independent-deployment-design.md`
  - 新增实施计划：`docs/plans/2026-04-22-collection-independent-deployment-plan.md`
  - 后端补齐 `CollectionService.mark_failed(...)` 与 `recover_expired_tasks(...)`
  - internal collection API 新增 `POST /internal/api/v1/collection/tasks/{task_id}/mark-failed`
  - 新增 `backend/app/workers/collection_scheduler.py` 与 `backend/scripts/run_collection_scheduler_worker.py`
  - 新增 `backend/app/workers/collection.py` 与 `backend/scripts/run_collection_worker.py`
  - 新增采集 provider adapter 骨架：
    - `backend/app/integrations/collection/base.py`
    - `backend/app/integrations/collection/router.py`
    - `backend/app/integrations/collection/waimaotong.py`
  - `backend/docker-compose.prod.yml`、`backend/.env.example`、`backend/README.md`、`backend/docs/DEPLOYMENT.md`、`backend/docs/LAUNCH_CHECKLIST.md`、`backend/docs/ROLLBACK.md`、`backend/docs/SEALOS_DEPLOYMENT.md` 已同步纳入 `collection-scheduler` / `collection-worker`
  - 当前 collection provider 仍为骨架；未接入 provider 会真实进入失败/重试路径，不会伪造成功
- 顺手修复一个后端既有断点：
  - `TenantMessagingService.claim_due_emails(...)` 现在允许 `failed/released` 的 send lock 被重新占用，避免重试永远被唯一约束卡死
  - sending 测试增加了对历史 active enrollment 的隔离，避免脏库把新计划饿死
- 完成“租户级 OpenRouter key 替换本地充值账本”收口：
  - 后端新增 `tenant_ai_provider_configs`，租户级加密保存 OpenRouter API key，支持 Admin / Tenant Admin 配置、刷新、清空
  - 后端删除本地充值/流水账本与 `BillingService`，AI 能力改为依赖租户级 provider 状态与余额状态
  - `ai_usage_logs` 改为纯 AI 用量日志，评分/模板生成/情报摘要统一接入 `AiUsageLogService`
  - Admin 新增租户详情里的 OpenRouter 配置卡片，移除租户余额列、充值按钮和余额流水
  - Tenant 新增 `设置 -> OpenRouter` 页面，展示配置状态、余额状态、用量汇总与趋势
  - Tenant Dashboard、Templates、EmailMonitor、Intelligence 不再读取 `/billing/*`，统一读取 `ai-capabilities`
  - 前后端文档、`.env.example`、部署说明已移除全局 `OPENROUTER_API_KEY` 口径

- 完成前端去 mock 收口：
  - Admin 登录、布局、租户管理、数据源、评分模板、情报源、平台模板、预热规则、AI 配置全部接真实 API
  - Tenant 登录、Dashboard、Companies、CuratedCustomers、Templates、SendPlans、EmailMonitor、Intelligence、Settings 全部接真实 API
- 修复关键联调错配：
  - `scoring-templates` 页面不再把分页结果当单对象使用
  - `contact-rules` 页面改为读取启用规则集并按 `{ name, rules }` 保存
  - `team/users` 页面统一使用 `roles[]`，角色映射收口为 `admin / operator / viewer`
  - AI 模板生成 payload 改为真实后端字段
  - 情报页改为消费分页 envelope，不再靠 `unknown as`
  - 新建发送计划改正 query key 失配
- 补齐 onboarding 真链路：
  - Tenant 登录后通过 `/auth/me` 判断 `needs_onboarding`
  - Tenant Layout 在需要时强制跳转 `/onboarding`
  - Onboarding 完成时调用 `/api/v1/onboarding/complete`
- 修复 demo seed 登录阻塞：
  - 种子邮箱从 `.test` 改为合法示例邮箱 `*.example.com`
  - seed 脚本会修复 demo owner/operator/viewer 账号
  - 重新执行 seed 后，`globex-pcb` 与 `acme-pcb` 均可正常登录
- 补齐上线前文档：
  - `backend/README.md`
  - `backend/docker-compose.prod.yml`
  - `backend/docs/DEPLOYMENT.md`
  - `backend/docs/LAUNCH_CHECKLIST.md`
  - `backend/docs/ROLLBACK.md`
  - `frontend/README.md`
  - `frontend/.env.example`
  - `frontend/apps/admin/.env.example`
  - `frontend/apps/tenant/.env.example`
- 处理前端 production build 大包 warning：
  - 为 `apps/admin` 与 `apps/tenant` 的 `vite.config.ts` 增加稳定 `manualChunks`
  - 仅抽离稳定公共依赖：`react-vendor`、`router-vendor`、`query-vendor`、`data-vendor`
  - 保留 `antd` 的默认组件级切分，避免把组件重新合成单个超大 vendor chunk
  - 当前构建已不再出现 Vite `chunk size warning`
- 跑通 Docker 主机发布演练并修复生产 compose 环境变量坑：
  - 根因是容器运行直接吃宿主机 `.env`，导致 `DATABASE_URL` / `SYNC_DATABASE_URL` 在容器内仍指向 `localhost:5432`
  - `backend/docker-compose.prod.yml` 已增加 `DOCKER_DATABASE_URL` / `DOCKER_SYNC_DATABASE_URL` 覆盖，默认指向 `postgres:5432`
  - 生产 compose 中 `backend`、`scoring-worker`、`sending-worker` 已统一改为 `python ...` 运行，不再在容器启动时重复创建 `.venv`
  - `backend/.env.example`、`backend/docs/DEPLOYMENT.md`、`backend/docs/LAUNCH_CHECKLIST.md`、`backend/README.md` 已同步更新

## 验证结果

- 后端：
  - `docker compose up -d postgres`
  - `uv run alembic -c alembic.ini upgrade head`
  - `uv run pytest -q` → `32 passed`
  - `uv run python scripts/run_collection_scheduler_worker.py --once`
  - `uv run python scripts/run_collection_worker.py --once`
  - `uv run python scripts/run_scoring_worker.py --once`
  - `uv run python scripts/run_sending_worker.py --once`
  - `uv run python scripts/seed_demo_data.py`
- 前端：
  - `pnpm type-check`
  - `pnpm build`
- Docker 主机发布演练：
  - `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build postgres backend scoring-worker sending-worker`
  - `docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend python -m alembic -c alembic.ini upgrade head`
  - `docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T backend python scripts/seed_demo_data.py`
  - `curl -fsS http://127.0.0.1:8000/health` → `{"data":{"status":"ok"}}`
  - `docker compose ... ps` 显示 `backend` healthy，`scoring-worker` / `sending-worker` 持续运行且无重启
  - `curl http://localhost:4173` / `curl http://localhost:4174` 均返回生产预览 `dist/index.html`
  - Admin / Tenant 登录 API 与关键数据接口 smoke 均通过：
    - `/admin/api/v1/auth/login`
    - `/admin/api/v1/auth/me`
    - `/admin/api/v1/tenants`
    - `/t/globex-pcb/api/v1/auth/login`
    - `/t/globex-pcb/api/v1/auth/me`
    - `/t/globex-pcb/api/v1/dashboard/overview`
    - `/t/globex-pcb/api/v1/dashboard/funnel`
    - `/t/globex-pcb/api/v1/companies`
- 浏览器 smoke：
  - Admin 登录后可进入租户管理页
  - Tenant `globex-pcb` 可加载 Dashboard、Companies、Templates、Send Plans、Settings/Team
  - Tenant `acme-pcb` 可进入 `/onboarding`

## 当前 Demo 账号

- Platform Admin:
  - `admin@example.com` / `change-me-now`
- Tenant:
  - `globex-pcb` / `owner@globex.example.com` / `ChangeMe123!`
  - `acme-pcb` / `owner@acme.example.com` / `ChangeMe123!`

## 已知剩余项

- collection provider 目前只有骨架，`waimao_tong` 尚未接入真实外采实现
- Sealos / Docker 层虽然已纳入 `collection-scheduler` / `collection-worker`，但还没有重新跑浏览器或真实第三方联调来验证采集结果展示
- EngageLab / OpenRouter 仍按“页面走真实后端，第三方可未配置”口径交付
- 历史数据迁移仍是 dry-run 骨架，不包含真实旧库导入
- 本机 Playwright MCP 因 `/.playwright-mcp` 只读限制无法截图，这属于本地工具环境问题，不是项目发布阻塞
- 本轮只完成后端测试与前端构建校验，未重新跑浏览器级 smoke
