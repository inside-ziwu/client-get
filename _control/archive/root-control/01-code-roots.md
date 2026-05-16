# 01 · 代码主入口

> **目的**：告诉代理"代码在哪、入口在哪、配置在哪"。**本文档不读代码内容，仅基于文件名与目录结构推断**。
> **盘点时间**：2026-05-04
> **未做的事**：未运行启动命令、未读取 `.env`、未阅读 `main.py` / `main.tsx` 内容。下表中"启动命令"是基于 `package.json` / `pyproject.toml` 的脚本字段名约定推测，**首次实际启动前需要读取这些清单文件确认**。

## 标签

| 标签 | 含义 |
| --- | --- |
| `[BASELINE?]` | 可能是当前 V3 开发基线 |
| `[CONFIRM?]` | 需要用户确认 |
| `[GIT-INDEPENDENT]` | 独立 git 仓库 |

---

## 1. 前端 `[BASELINE?]` `[GIT-INDEPENDENT]`

**仓库根**：`frontend/`
**Git**：独立仓库，main 分支，最新提交 2026-04-30 `fix(admin): T-6 align CollectionKeyword fields...`
**包管理**：pnpm monorepo（`pnpm-workspace.yaml` + `pnpm-lock.yaml`）

### 1.1 工作区结构

```
frontend/
├── package.json                    工作区根 package
├── pnpm-workspace.yaml             工作区清单
├── pnpm-lock.yaml
├── tsconfig.base.json              共享 TS 配置
├── .prettierrc / .npmrc / .gitignore / .dockerignore
├── Dockerfile.tenant               租户镜像构建
├── Dockerfile.admin                管理端镜像构建
├── .env.example                    根级环境变量模板
├── deploy/
│   ├── push-tenant.sh              推送脚本
│   └── nginx-spa.conf              SPA Nginx
├── apps/
│   ├── tenant/                     租户端 SPA
│   └── admin/                      管理端 SPA
└── packages/                       共享包
    ├── shared-api/
    ├── shared-hooks/
    ├── shared-types/
    └── shared-ui/
```

### 1.2 应用入口

| 应用 | 入口文件 | 路由 | 启动配置 |
| --- | --- | --- | --- |
| Tenant | `apps/tenant/src/main.tsx` | `apps/tenant/src/router.tsx` | `apps/tenant/vite.config.ts` + `tsconfig.json` |
| Admin | `apps/admin/src/main.tsx` | `apps/admin/src/router.tsx` | `apps/admin/vite.config.ts` + `tsconfig.json` |

每个 app 内部固定子目录：`components/ layouts/ lib/ pages/ stores/ vite-env.d.ts`。

### 1.3 共享包入口

| 包 | 入口 | 备注 |
| --- | --- | --- |
| `packages/shared-api/src/index.ts` | `client.ts` + `query-keys.ts` + `admin/` + `tenant/` | 接口客户端工厂 |
| `packages/shared-ui/src/index.ts` | 含 11 个组件（AppLayout、CompanyDetailDrawer、ExcelImporter、TemplateEditor 等）+ `theme.ts` | UI 库 |
| `packages/shared-hooks/src/index.ts` | useAuth、useCursorPagination、usePermission | hooks |
| `packages/shared-types/src/index.ts` | api.ts、auth.ts、enums.ts、models.ts | 类型 |

### 1.4 启动命令（推测，未验证）

> 🟡 `[CONFIRM?]` 本节命令未实际运行，需要先读 `frontend/package.json` 与各 app `package.json` 的 `scripts` 字段确认。

通常 pnpm + Vite 项目：

- 安装：`cd frontend && pnpm install`
- 开发（租户）：`pnpm --filter tenant dev`
- 开发（管理）：`pnpm --filter admin dev`
- 构建：`pnpm --filter tenant build` / `pnpm --filter admin build`

构建产物落在 `apps/tenant/dist/` 与 `apps/admin/dist/`（已存在，`[BUILT]`）。

### 1.5 技术栈（来自 memory + tsconfig，需复核）

React 19 + TypeScript + Ant Design 6 + Vite 7 + TanStack Query 5 + Zustand 5。

---

## 2. 后端 `[BASELINE?]` `[GIT-INDEPENDENT]`

**仓库根**：`backend/`
**Git**：独立仓库，main 分支，最新提交 2026-05-01 `test(collection): align phase1 routing expectations...`
**栈**：FastAPI + PostgreSQL + Alembic
**包管理**：uv（`pyproject.toml` + `uv.lock`）

### 2.1 仓库结构

```
backend/
├── pyproject.toml                  Python 项目定义
├── uv.lock                         锁文件
├── alembic.ini                     Alembic 配置
├── Dockerfile                      后端镜像
├── docker-compose.yml              本地开发
├── docker-compose.prod.yml         生产 compose
├── .env                            🔴 真实环境变量（敏感）
├── .env.example                    模板
├── README.md
├── 03_database/
│   └── schema.sql                  与 blueprint 顶层同 MD5（重复）
├── alembic/
│   ├── env.py                      Alembic 入口
│   └── versions/                   13 个迁移
├── app/                            应用代码（83 个 .py）
│   ├── main.py                     FastAPI 入口
│   ├── dependencies.py
│   ├── api/                        路由
│   ├── core/                       配置
│   ├── db/                         DB 连接
│   ├── models/                     ORM
│   ├── repositories/               仓储
│   ├── schemas/                    Pydantic
│   ├── security/                   鉴权
│   ├── services/                   业务逻辑
│   ├── integrations/               外部集成
│   ├── utils/
│   └── workers/                    见 §3
├── tests/                          25 个测试 .py
├── scripts/                        9 个运维脚本（见 §3 与 §4）
└── docs/                           工程文档（见 02-docs-index.md）
```

### 2.2 应用入口

| 入口 | 文件 |
| --- | --- |
| FastAPI 主应用 | `backend/app/main.py` |
| 依赖注入 | `backend/app/dependencies.py` |
| 数据库迁移 | `backend/alembic.ini` + `backend/alembic/env.py` |

### 2.3 启动命令（推测，未验证）

> 🟡 `[CONFIRM?]` 未读 `pyproject.toml` 的 `[project.scripts]` 与 `[tool.uv]` 段，本节为通用 uv + FastAPI 约定。

- 同步依赖：`cd backend && uv sync`
- 数据库迁移：`uv run alembic upgrade head`
- 启动 API：`uv run uvicorn app.main:app --reload`
- 跑测试：`uv run pytest`

或通过 `docker-compose.yml` / `docker-compose.prod.yml` 容器化启动。

---

## 3. Worker 入口 `[BASELINE?]`

| Worker 模块 | 启动脚本 |
| --- | --- |
| `backend/app/workers/collection.py` | `backend/scripts/run_collection_worker.py` |
| `backend/app/workers/collection_scheduler.py` | `backend/scripts/run_collection_scheduler.py` 与 `backend/scripts/run_collection_scheduler_worker.py` `[CONFIRM?]` |
| `backend/app/workers/scoring.py` | `backend/scripts/run_scoring_worker.py` |
| `backend/app/workers/sending.py` | `backend/scripts/run_sending_worker.py` |

> 🟡 `[CONFIRM?]` `run_collection_scheduler.py` 与 `run_collection_scheduler_worker.py` 命名近似，未读代码，无法判断职责差异。

---

## 4. 运维 / 数据脚本

`backend/scripts/`：

| 脚本 | 推测用途 |
| --- | --- |
| `bootstrap_platform_admin.py` | 引导平台管理员账号 |
| `seed_demo_data.py` | 演示数据种子 |
| `maintain_partitions.py` | 维护表分区 |
| `migrate_legacy.py` | 历史数据迁移 |

---

## 5. 数据库

详见 [`00-folder-inventory.md`](00-folder-inventory.md) §4 与 [`03-runtime-inputs.md`](03-runtime-inputs.md)。

- 迁移工具：Alembic
- 迁移目录：`backend/alembic/versions/`（13 个版本，最新 2026-05-01）
- 设计 schema：`blueprint/03_database/schema.sql`（与 backend 内拷贝同 MD5）

---

## 6. 容器与部署入口

| 用途 | 文件 |
| --- | --- |
| 租户镜像 | `frontend/Dockerfile.tenant` + `frontend/.dockerignore` |
| 管理镜像 | `frontend/Dockerfile.admin` |
| 后端镜像 | `backend/Dockerfile` |
| 本地 compose | `backend/docker-compose.yml` |
| 生产 compose | `backend/docker-compose.prod.yml` |
| 镜像推送脚本 | `frontend/deploy/push-tenant.sh` |
| 前端 Nginx | `frontend/deploy/nginx-spa.conf` |
| Sealos 文档 | `backend/docs/SEALOS_DEPLOYMENT.md` |

---

## 7. 待确认（汇总）

均已登记于 [`04-open-questions.md`](04-open-questions.md)：

- 启动命令是否与上面推测一致（需读 package.json / pyproject.toml `scripts`）
- `run_collection_scheduler.py` 与 `run_collection_scheduler_worker.py` 是否重复
- 两份 `schema.sql` 是否需要保留两份
- 前端 `Dockerfile.admin` 没有显式的 `push-admin.sh`，是否使用同一脚本
