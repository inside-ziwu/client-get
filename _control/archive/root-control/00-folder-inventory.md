# 00 · 工作区文件分类清单

> **目的**：把整个工作区下的所有文件按"用途/类型"一次性分类清楚，给后续的代码工作建立基础地图。
> **盘点时间**：2026-05-04
> **本次原则**：**只索引，不动文件**——不移动 / 不删除 / 不重命名 / 不改业务代码 / 不读取或输出 secret 值。
> **范围**：工作区根 `/Users/lay/Documents/Github/client_get/` 下所有文件，排除 `node_modules`、`.venv`、`.git/objects`、`__pycache__`、`.pytest_cache`、`.playwright-mcp` 噪音目录。

## 标签图例

| 标签 | 含义 |
| --- | --- |
| `[BASELINE?]` | 可能是当前 V3 开发基线（活跃代码 / 文档），**待用户确认** |
| `[HISTORY]` | 可能是历史版本，仍保留 |
| `[DOCS]` | 文档资料 |
| `[DEPLOY]` | 部署资料 |
| `[CONFIRM?]` | 需要用户确认用途 |
| `[SENSITIVE]` | 高风险敏感文件，已避免读取内容 |
| `[BUILT]` | 构建产物，理论上可重生 |
| `[DUP]` | 与其他文件内容重复 |

---

## 1. 前端代码（可能是当前 V3 开发基线 `[BASELINE?]`）

**仓库**：`frontend/`（独立 git，main 分支，最新提交 2026-04-30）
**包管理**：pnpm monorepo
**统计**：208 个 ts/tsx/js 文件（apps + packages）

| 路径 | 角色 | 文件数 |
| --- | --- | --- |
| `frontend/apps/tenant/` | 租户端 SPA | 95（24 ts/tsx） |
| `frontend/apps/admin/` | 管理端 SPA | 79（21 ts/tsx） |
| `frontend/packages/shared-api/` | 接口客户端工厂 | 34（32 ts/tsx） |
| `frontend/packages/shared-ui/` | 共享组件 | 12（10 ts/tsx） |
| `frontend/packages/shared-hooks/` | 共享 hook | 6（4 ts/tsx） |
| `frontend/packages/shared-types/` | 类型定义 | 7（5 ts/tsx） |

每个 app 内部目录都对称：`components/ layouts/ lib/ pages/ router.tsx stores/ main.tsx vite-env.d.ts`。
shared-ui 内组件：`AIAccessGuard、AppLayout、CompanyDetailDrawer、ContactStatusTag、ExcelImporter、NotificationBell、PermissionGate、RatingTag、RequireAuth、StatusTag、TemplateEditor`。

> ⚠️ 注：`frontend/apps/admin/src/pages/CollectionArchive` 是页面名（"采集归档"），**不是历史版本**。

**前端配置/工具文件**：

- `frontend/package.json`、`pnpm-workspace.yaml`、`pnpm-lock.yaml`
- `frontend/tsconfig.base.json` + 每个包内 `tsconfig.json`
- `frontend/.prettierrc`、`.npmrc`、`.gitignore`、`.dockerignore`
- 每个 app 内 `vite.config.ts`

---

## 2. 后端代码（可能是当前 V3 开发基线 `[BASELINE?]`）

**仓库**：`backend/`（独立 git，main 分支，最新提交 2026-05-01）
**栈**：FastAPI + PostgreSQL + Alembic + uv
**统计**：83 个 .py 文件（仅 `app/`），25 个测试 .py，9 个 scripts

| 路径 | 角色 |
| --- | --- |
| `backend/app/main.py` | FastAPI 入口 |
| `backend/app/dependencies.py` | 依赖注入 |
| `backend/app/api/` | 路由层 |
| `backend/app/core/` | 核心配置 |
| `backend/app/db/` | 数据库连接/会话 |
| `backend/app/models/` | ORM 模型 |
| `backend/app/repositories/` | 仓储层 |
| `backend/app/schemas/` | Pydantic schema |
| `backend/app/security/` | 鉴权 |
| `backend/app/services/` | 业务逻辑 |
| `backend/app/integrations/` | 第三方集成 |
| `backend/app/utils/` | 工具 |
| `backend/app/workers/` | 异步任务（详见 §3） |

**后端配置文件**：`backend/pyproject.toml`、`backend/uv.lock`、`backend/alembic.ini`

---

## 3. Worker 代码 `[BASELINE?]`

| 文件 | 推测职责（基于文件名，未读代码） |
| --- | --- |
| `backend/app/workers/collection.py` | 采集 worker |
| `backend/app/workers/collection_scheduler.py` | 采集调度 worker |
| `backend/app/workers/scoring.py` | 评分 worker |
| `backend/app/workers/sending.py` | 邮件发送 worker |

**Worker 启动脚本**（`backend/scripts/`）：

- `run_collection_worker.py`
- `run_collection_scheduler_worker.py`
- `run_collection_scheduler.py`
- `run_scoring_worker.py`
- `run_sending_worker.py`

> 🟡 `[CONFIRM?]` `run_collection_scheduler_worker.py` 与 `run_collection_scheduler.py` 同时存在，命名相近——是否有重复或职责切分？

---

## 4. 数据库 / migration 文件

### 4.1 Alembic 迁移（`[BASELINE?]`）

`backend/alembic/`：

| 版本号 | 文件 |
| --- | --- |
| 0001 | `20260421_0001_canonical_schema.py` |
| 0002 | `20260421_0002_seed_and_partitions.py` |
| 0003 | `20260422_0003_scoring_jobs.py` |
| 0004 | `20260422_0004_tenant_ai_provider.py` |
| 0005 | `20260423_0005_drop_source_type_check.py` |
| 0006 | `20260423_0006_email_template_design.py` |
| 0007 | `20260429_0007_collection_task_type.py` |
| 0008 | `20260429_0008_competitor_enrichment.py` |
| 0009 | `20260430_0009_phase1_collection_schema.py` |
| 0010 | `20260501_0010_add_default_partitions.py` |
| 0011 | `20260501_0011_drop_ai_model_pricing_columns.py` |
| 0012 | `20260501_0012_waimaotong_raw_contacts.py` |
| 0013 | `20260501_0013_drop_ai_fallback.py` |

入口：`backend/alembic/env.py`、`backend/alembic.ini`

### 4.2 Schema SQL

| 路径 | 状态 |
| --- | --- |
| `blueprint/03_database/schema.sql` | `[BASELINE?]` 设计真源副本（MD5: 9421ff22…） |
| `backend/03_database/schema.sql` | `[BASELINE?]` **代码运行时被加载**（alembic 0001 read_text 加载此文件） |

> 🟢 **澄清**（2026-05-04 整理 schema 时）：两份 MD5 相同**不是冗余**——blueprint 那份是设计真源副本（人维护），backend 那份是代码加载入口（alembic 0001 直接读取）。两份都需要，但缺乏同步机制——见 [`04-open-questions.md`](04-open-questions.md) #F4。

### 4.3 整理后的集中索引

`_control/inputs/database/`（2026-05-04 拷贝）：

- [`README.md`](inputs/database/README.md) —— 完整索引：来源映射、44 张表分组、迁移时间线、待确认事项
- `schema.sql`、`RLS_POLICY_MATRIX.md`、`MIGRATION_ORDER_AND_NOTES.md`、`09_DATABASE_DESIGN_REPAIRED.md`、`14_DATA_MIGRATION_REPAIRED.md`、`SECURITY_RLS_AUTH_ARCHITECTURE.md`、`entities.yaml`
- `alembic-migrations/` 13 份迁移拷贝

---

## 5. Docker / Sealos / 部署相关 `[DEPLOY]`

### 5.1 容器构建

| 文件 | 用途 |
| --- | --- |
| `frontend/Dockerfile.tenant` | 租户端镜像 |
| `frontend/Dockerfile.admin` | 管理端镜像 |
| `frontend/.dockerignore` | 前端 docker 忽略 |
| `backend/Dockerfile` | 后端镜像 |
| `backend/docker-compose.yml` | 本地开发 compose |
| `backend/docker-compose.prod.yml` | 生产 compose |

### 5.2 部署脚本与配置

| 文件 | 用途 |
| --- | --- |
| `frontend/deploy/push-tenant.sh` | 推送租户镜像脚本 |
| `frontend/deploy/nginx-spa.conf` | SPA Nginx 配置 |

### 5.3 Sealos / 部署文档

| 路径 | 标签 | 摘要 |
| --- | --- | --- |
| `backend/docs/SEALOS_DEPLOYMENT.md` | `[DEPLOY]` `[BASELINE?]` | 后端 Sealos 部署文档（9KB） |
| `backend/docs/DEPLOYMENT.md` | `[DEPLOY]` | 通用部署文档 |
| `backend/docs/LAUNCH_CHECKLIST.md` | `[DEPLOY]` | 上线 checklist |
| `backend/docs/ROLLBACK.md` | `[DEPLOY]` | 回滚预案 |
| `blueprint/docs/solutions/best-practices/sealos-direct-deployment-from-local-ghcr-images-2026-04-23.md` | `[DEPLOY]` `[HISTORY]` | Sealos 从本地 GHCR 镜像直接部署最佳实践（2026-04-23） |
| `blueprint/docs/solutions/best-practices/sealos-devbox-clientget-deployment-with-app-launchpad-2026-04-23.md` | `[DEPLOY]` `[HISTORY]` | Sealos Devbox + AppLaunchpad 部署最佳实践（2026-04-23） |
| `_control/inputs/sealos/` | 空 | 预留收件箱 |

### 5.4 Scripts（运维 / 数据迁移）

`backend/scripts/`：

| 文件 | 推测用途 |
| --- | --- |
| `bootstrap_platform_admin.py` | 引导平台管理员账号 |
| `seed_demo_data.py` | 演示数据种子 |
| `maintain_partitions.py` | 维护分区 |
| `migrate_legacy.py` | 历史数据迁移 |

---

## 6. 本地产品文档 `[DOCS]`

### 6.1 docs/ 根级 8 份（活跃产品/技术文档，2026-04-30 前后产出）

详见 [`02-docs-index.md`](02-docs-index.md) §1。

### 6.2 docs/ 子目录

| 目录 | 文件数 | 标签 |
| --- | --- | --- |
| `docs/guide/` | 1 | `[DOCS]` 含项目目录导航 |
| `docs/meetings/` | 22 | `[DOCS]` `[HISTORY]` 会议记录 |
| `docs/research/` | 16 | `[DOCS]` `[BASELINE?]` 调研材料（含 tendata-field-mapping） |
| `docs/source-materials/` | 4 | `[DOCS]` 原始材料 |
| `docs/session-records/` | 1 | `[DOCS]` `[HISTORY]` |
| `docs/archive/` | 15 | `[DOCS]` `[HISTORY]` 已归档 |

---

## 7. 技术方案文档（蓝图） `[DOCS]`

### 7.1 蓝图根级（设计真源）

| 文件 | 标签 | 摘要 |
| --- | --- | --- |
| `blueprint/00_SOURCE_OF_TRUTH_DECISIONS.md` | `[DOCS]` `[BASELINE?]` | **最高优先级真源**——解决文档冲突 |
| `blueprint/CODEX_START_HERE.md` | `[DOCS]` `[BASELINE?]` | 给 Codex/Claude 的开发启动说明 |
| `blueprint/README.md` | `[DOCS]` | 蓝图包总入口 |

### 7.2 蓝图 00–09 + machine_readable + docs

| 目录 | 文件数 | 标签 | 角色 |
| --- | --- | --- | --- |
| `00_original_sources/` | 17 | `[HISTORY]` | 原始资料（已被 01 取代） |
| `01_final_repaired_docs/` | 10 | `[BASELINE?]` | 修订后的实现真源 |
| `02_architecture/` | 2 | `[BASELINE?]` | 后端架构 + 安全 RLS |
| `03_database/` | 3 | `[BASELINE?]` | schema.sql + 迁移笔记 + RLS 矩阵 |
| `04_api/` | 3 | `[BASELINE?]` | API 合同 + 路由矩阵 + FastAPI 路由顺序 |
| `05_services/` | 5 | `[BASELINE?]` | 5 个服务规范 |
| `06_frontend_alignment/` | 2 | `[BASELINE?]` | 前后端对齐 |
| `07_implementation_plan/` | 4 | `[BASELINE?]` | 主提示词 + 开发计划 + 验收测试 + TASKS.yaml |
| `08_references/` | 2 | `[DOCS]` | 业主未决问题 + 来源追溯 |
| `09_self_audit/` | 1 | `[BASELINE?]` | 蓝图自审报告（优先级仅次于 SOT） |
| `machine_readable/` | 4 | `[BASELINE?]` | 机读规范（路由/实体/任务/状态机） |
| `docs/` | 4 + 子目录 | `[DOCS]` | AGENT_PROGRESS / ASSUMPTIONS / NEXT_SESSION_PROMPT / OPEN_QUESTIONS + plans/ solutions/ superpowers/ |

详细单文件清单见 [`02-docs-index.md`](02-docs-index.md)。

### 7.3 backend/docs（与代码并行的工程文档） `[DOCS]`

| 文件 | 标签 | 摘要 |
| --- | --- | --- |
| `ASSUMPTIONS.md` | `[DOCS]` | 已做假设 |
| `IMPLEMENTATION_NOTES.md` | `[DOCS]` `[BASELINE?]` | 实现笔记 |
| `DEPLOYMENT.md` `LAUNCH_CHECKLIST.md` `ROLLBACK.md` `SEALOS_DEPLOYMENT.md` | `[DEPLOY]` | 见 §5.3 |
| `legacy_migration_report.json` | `[CONFIRM?]` | **未读取**——需确认是否含敏感数据，是否需要从 git 排除 |

---

## 8. 测试记录

### 8.1 后端测试 `[BASELINE?]`

`backend/tests/`：25 个 .py 文件。

### 8.2 前端测试

> 🟡 `[CONFIRM?]` 未在前端发现独立的 `tests/` 或 `__tests__/` 目录——前端是否有测试？或者仍待补？

### 8.3 测试运行产物（`[BUILT]`，不应入仓）

- `.pytest_cache/`（工作区根） / `backend/.pytest_cache/`
- `.playwright-mcp/`（含 146 项截图与 console log）

---

## 9. 旧版本文件 `[HISTORY]`

| 路径 | 标签 | 备注 |
| --- | --- | --- |
| `docs/archive/` | `[HISTORY]` | 15 份归档文档 |
| `blueprint/00_original_sources/` | `[HISTORY]` | 已被 01_final_repaired_docs 取代 |
| `openspec/archive/` | `[HISTORY]` | 当前为空 |
| `openspec/changes/archive/` | `[HISTORY]` | 当前为空 |

> 🟢 **2026-05-10 已整理**：原 `clientget-backend-blueprint-v1/` 已拆分为 `backend/` 与 `blueprint/`。`backend/` 是活跃后端代码，`blueprint/` 只保留历史蓝图与设计依据。

---

## 10. 构建产物 `[BUILT]`

| 路径 | 状态 |
| --- | --- |
| `frontend/apps/tenant/dist/` | 存在，被 `frontend/.gitignore` 排除 |
| `frontend/apps/admin/dist/` | 存在，被 `frontend/.gitignore` 排除 |
| `frontend/node_modules/` | 存在，被排除 |
| `backend/.venv/` | 存在，被排除 |
| 各类 `__pycache__/`、`.pytest_cache/` | 存在，被排除 |

---

## 11. 高风险敏感文件 `[SENSITIVE]`

> **本次只列路径与风险等级，不读取内容、不输出值。**

| 路径 | 等级 | 处置建议（暂不执行） |
| --- | --- | --- |
| `backend/.env` | 🔴 **高** | 真实环境变量文件。**确认是否在子仓库 .gitignore 内**；如不在，存在凭证泄露风险 |
| `backend/.env.example` | 🟢 低 | 模板文件，按惯例不含真实密钥 |
| `frontend/.env.example` | 🟢 低 | 模板文件 |
| `frontend/apps/tenant/.env.example` | 🟢 低 | 模板文件 |
| `frontend/apps/admin/.env.example` | 🟢 低 | 模板文件 |
| `frontend/apps/tenant/.env.development` | 🟡 中 | 本地开发环境变量。可能含开发用 API key——**确认是否被前端 .gitignore 排除** |
| `frontend/apps/admin/.env.development` | 🟡 中 | 同上 |
| `backend/docs/legacy_migration_report.json` | 🟡 中 | 历史迁移报告，**未读取**——可能含数据库样本数据，待确认 |

**未在工作区发现**：
- `.pem` / `.key` / `.crt` / `id_rsa` 等密钥/证书文件 ✅
- `kubeconfig` / `.kubeconfig` ✅
- `*.dump` / `*.sql.gz` / `*.bak` / `*.sqlite` 等数据库 dump ✅
- 顶层散落的 `*.csv` ✅

---

## 12. 不确定用途文件 `[CONFIRM?]`

| 路径 | 疑点 |
| --- | --- |
| `opencode.json`（工作区根） | 124 字节，OpenCode CLI 配置——**用户当前是否在用 OpenCode？** |
| `.opencode/` | 含 commands/ 与 skills/——OpenCode 代理本地配置 |
| `.codex/` | Codex CLI 本地配置 |
| `backend/run_collection_scheduler_worker.py` 与 `run_collection_scheduler.py` | 命名相近，是否重复？ |
| `backend/03_database/schema.sql` | 与 blueprint 顶层同名同 MD5——**是否两份都需要？** |
| `blueprint/docs/AGENT_PROGRESS.md` `NEXT_SESSION_PROMPT.md` | AI 代理工作状态记录——**是否仍准确？** |
| `blueprint/docs/superpowers/specs/2026-04-22-collection-independent-deployment-design.md` | "collection 独立部署"设计——**是否仍是计划？** |
| `blueprint/docs/plans/2026-04-22-collection-independent-deployment-plan.md` | 同上对应的计划文档 |
| 工作区根 `.pytest_cache/` 与 `backend/.pytest_cache/` | 工作区根为何也有？是否曾在根目录跑过 pytest？ |
| `.playwright-mcp/`（工作区根，146 项） | Playwright MCP 截图与 console log——是否仍在用？可否清理？ |

---

## 13. 顶层散落文件

| 路径 | 类型 |
| --- | --- |
| `README.md`（工作区根） | `[DOCS]` 工作区导航（418 字节） |
| `AGENTS.md`（工作区根） | `[DOCS]` 给所有代理的硬约束（本次新增） |
| `CLAUDE.md`（工作区根） | `[DOCS]` Claude 专用补充（本次新增） |
| `opencode.json`（工作区根） | `[CONFIRM?]` 见 §12 |
| `.gitignore`（工作区根） | 配置（本次新增） |
| `.DS_Store`（多处） | macOS 元数据，已在 .gitignore |

---

## 14. 总览统计

| 分类 | 数量 / 体量 |
| --- | --- |
| 前端 ts/tsx/js | 208 |
| 后端 .py（app/） | 83 |
| 后端测试 .py | 25 |
| 后端 scripts | 9 |
| Alembic 迁移 | 13 |
| docs/ 根级 md | 8 |
| docs/ 子目录文件 | 59 |
| blueprint 根级 md | 3 |
| blueprint 00–09 + machine_readable + docs | ~56 |
| backend/docs | 7 |
| 部署脚本/配置 | 8 |
| .env / .env.* | 7（详见 §11） |
| 高风险文件 | 1 真实 .env + 1 待确认 json |
| 工作区根 git 提交 | 2（59f8a78, a618e8a） |
