# V3 · Slice 0 · 开发与运行基线（dev-runtime-baseline）

> **任务**：T-DF-10 ~ T-DF-15（[`openspec/changes/v3-data-foundation/tasks.md`](../../../openspec/changes/v3-data-foundation/tasks.md)）
> **能力域**：C8 部署 / DevOps（[`02-current-implementation-gap-audit.md`](../02-current-implementation-gap-audit.md) C8-G1, G2）
> **针对验收 ID**：V3-DEPLOY-001（前置部分）
> **状态**：v1.0 已签字（2026-05-07）—— 本地验证全部通过（sending worker 已知 schema 漂移记录于 §2.3.1，不阻塞）
> **关联**：[`07-v3-scope-final.md`](../07-v3-scope-final.md) §9 9 部署单元 / [`SEALOS_DEPLOYMENT.md`](../../../backend/docs/SEALOS_DEPLOYMENT.md)（已有 8 单元，本基线补 cleanup_service 第 9 单元占位）

## 0. 元数据

| 项 | 值 |
|---|---|
| 报告版本 | v1.0（已签字） |
| 起草日期 | 2026-05-07 |
| 签字日期 | 2026-05-07 |
| 起草人 | Claude Code |
| 用户签字 | lay · 2026-05-07 |
| 触发来源 | T-DF-10 ~ T-DF-14（v3-data-foundation Slice 0） |

### 0.1 与 AGENTS.md / CLAUDE.md 的关系

按 [`AGENTS.md`](../../../AGENTS.md) §1 工作区规则，启动命令的"权威表述"位于 AGENTS.md / CLAUDE.md（人类维护者）。本文件仅记录 **AI 实测** 与 **变更建议**：

- 实测命令 / 实测路径 / 9 部署单元清单 → 写入本文件（AI 维护）
- AGENTS.md / CLAUDE.md 是否需要同步更新 → 见 §7 "人类维护者待补"

---

## 1. 当前基线

### 1.1 代码版本

| 仓库 | Git HEAD | 最新提交日期 | 备注 |
|---|---|---|---|
| 主仓库（`client_get/`） | `ceb5b84` | 2026-04-30 | superproject |
| 前端（`frontend/`） | `ceb5b84` | 2026-04-30 | 独立 git |
| 后端（`backend/`） | `8d98ff7` | 2026-05-01 | 独立 git |

### 1.2 数据库基线

- **schema 真源**：`backend/03_database/schema.sql`（44 张表，已签字）
- **Alembic 头部 revision**：`20260501_0013_drop_ai_fallback`（最新 `0013`）
- **当前 staging / 生产 alembic 版本**：__待用户确认__（可能落后于 `0013`，T-DF-20 阶段升级）

### 1.3 技术栈复核

| 层 | 栈 | 来源 |
|---|---|---|
| 前端 | Node ≥20 / pnpm ≥9 / React 19 / Vite 7 / Antd 6 / TanStack Query 5 / Zustand 5 | `frontend/package.json` `engines` + apps 子 `package.json` |
| 后端 | Python ≥3.11 / FastAPI 0.116+ / SQLAlchemy 2.0 / asyncpg 0.30 / Alembic 1.16+ / uv | `backend/pyproject.toml` |
| 数据库 | PostgreSQL 16（Sealos `Postgres`） | `docker-compose.yml` + SEALOS_DEPLOYMENT §一 |
| 容器 | docker buildx，必须 `--platform linux/amd64` | SEALOS_DEPLOYMENT §二 |

---

## 2. 启动命令（实测路径）

### 2.1 前端（`frontend/`）

工作区根 `package.json` 实测脚本：

| 命令 | 用途 |
|---|---|
| `pnpm install` | 安装 monorepo 依赖（首次/lock 变化时） |
| `pnpm dev:admin` | 启动 admin 开发服务（Vite，默认 4174 / 见 `apps/admin/vite.config.ts`） |
| `pnpm dev:tenant` | 启动 tenant 开发服务（Vite，默认 4173 / 见 `apps/tenant/vite.config.ts`） |
| `pnpm build:admin` | 构建 admin 静态产物 → `apps/admin/dist/` |
| `pnpm build:tenant` | 构建 tenant 静态产物 → `apps/tenant/dist/` |
| `pnpm build` | `pnpm -r build`（全工作区） |
| `pnpm type-check` | `pnpm -r type-check`（每个 app 内 `tsc --noEmit`） |
| `pnpm lint` | `eslint . --ext .ts,.tsx` |
| `pnpm format` | `prettier --write` |
| `pnpm clean` | 删除 `dist` 与 `node_modules` |

### 2.2 后端 API（`backend/`）

| 步骤 | 命令 |
|---|---|
| 同步依赖 | `uv sync` |
| 数据库迁移 | `uv run alembic -c alembic.ini upgrade head` |
| 启动 API（开发） | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |
| 启动 API（生产 / Sealos 容器内） | `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| 跑测试 | `uv run pytest` |
| ruff 检查 | `uv run ruff check` |
| 引导平台管理员（首次） | `uv run python scripts/bootstrap_platform_admin.py` |
| 演示数据（可选） | `uv run python scripts/seed_demo_data.py` |

### 2.3 4 worker（已有，全部位于 `backend/scripts/`）

> 全部 worker 共用 **同一后端镜像**，仅 `command:` 不同（见 §4.1）。

| Worker | 模块 | 启动脚本 | 默认 sleep | lease |
|---|---|---|---|---|
| **collection** | `app/workers/collection.py` | `scripts/run_collection_worker.py` | 10s | 300s |
| **collection_scheduler** | `app/workers/collection_scheduler.py` | `scripts/run_collection_scheduler_worker.py` | 30s | — |
| **scoring** | `app/workers/scoring.py` | `scripts/run_scoring_worker.py` | 10s | — |
| **sending** | `app/workers/sending.py` | `scripts/run_sending_worker.py` | 10s | — |

实测启动（本地）：

```bash
cd backend

# collection worker（长期）
uv run python scripts/run_collection_worker.py \
  --sleep-seconds 10 \
  --lease-seconds 300 \
  --limit 20 \
  --heartbeat-interval-seconds 30

# collection scheduler worker（长期）
uv run python scripts/run_collection_scheduler_worker.py --sleep-seconds 30

# scoring worker（长期）
uv run python scripts/run_scoring_worker.py --sleep-seconds 10

# sending worker（长期）
uv run python scripts/run_sending_worker.py --sleep-seconds 10
```

> **关于 `run_collection_scheduler.py`（`[CONFIRM?]` 已澄清）**：该脚本是"一次性调度"命令（`schedule_due_tasks(conn)` 跑完即退出，可被 cron 拉起），与 `run_collection_scheduler_worker.py`（长期循环）职责不同。**Sealos 部署只用后者**（长期 worker），前者保留给排障 / 手动触发。**复核 [`_control/01-code-roots.md`](../../01-code-roots.md) §3 待确认项**：可关闭。

### 2.3.1 sending worker 已知 schema 漂移（不阻塞 Slice 0）

> **实测发现（2026-05-07）**：`sending_worker --once` 报 `operator does not exist: bigint = uuid`。

| 项 | 详情 |
|---|---|
| 根因 | migration `0009` 把 `tenant_companies` 重建为 `id bigserial`；而 `sending_plan_recipients.tenant_company_id uuid` 仍指 uuid；JOIN 时类型不匹配 |
| 影响范围 | `sending_plan_recipients`、`sequence_enrollments` 等邮件相关 JOIN 全部报错 |
| 分类 | **C1-G1 已知 schema 漂移**（[`02-current-implementation-gap-audit.md`](../02-current-implementation-gap-audit.md) C1 数据库重构缺口） |
| 修复时机 | **Slice 1.B（T-DF-31）**：迁移 `tenant_companies` 到 V3 schema（`id uuid`，参照 [`design.md`](../../../openspec/changes/v3-data-foundation/design.md) §2.2）|
| Slice 0 结论 | ✅ **不阻塞**。sending worker 在 Slice 1.B 之前不可用是预期行为 |

### 2.4 cleanup_service（Slice 1.B 才会建）

| 项 | 约定（Slice 0 占位） |
|---|---|
| Worker 模块 | `app/workers/cleanup_service.py`（**T-DF-40 ~ T-DF-47 才会创建**） |
| 启动脚本 | `scripts/run_cleanup_worker.py`（同上，Slice 1.B 创建） |
| 启动命令（约定） | `uv run python scripts/run_cleanup_worker.py --sleep-seconds 10 --lease-seconds 300` |
| 镜像 | 复用 backend Dockerfile（同 §4.1） |
| 健康检查 | 待 Slice 4（T-DF-50 worker base class）补 `/health` 端点 |
| Sealos 应用名 | `clientget-cleanup-service`（约定，第 9 单元，见 §5） |

### 2.5 docker-compose 起本地全栈（一行式）

```bash
cd backend
cp .env.example .env       # 用户填密钥
docker compose up -d       # 仅 postgres + backend（开发）
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d  # 加 4 worker
```

> **现状**：`docker-compose.prod.yml` 已覆盖 4 worker。**cleanup_service 占位 Slice 1.B 添加** —— 见 §4.3。

---

## 3. 本地启动验证清单（用户任务，T-DF-11）

> AI **不实际启动**（无 `.env` / 无 EngageLab key / 无 OpenRouter）。本表给用户排查清单。**勾选后回报 AI**。

### 3.1 前置（用户准备）

- [ ] 本地 PostgreSQL 16 已起（或 `docker compose up -d postgres`）
- [ ] `backend/.env` 已从 `.env.example` 拷贝并填好：
  - `DATABASE_URL` / `SYNC_DATABASE_URL` / `TEST_*`
  - `JWT_SECRET` / `ADMIN_EMAIL` / `ADMIN_PASSWORD`
  - `DATA_SOURCE_ENCRYPTION_KEY`（32 字节）
  - `INTERNAL_SERVICE_SECRET` / `ENGAGELAB_WEBHOOK_SECRET`
  - **EngageLab 真值** Slice 3 才需要，Slice 0 不阻塞

### 3.2 后端启动

- [ ] `uv sync` 无错（`uv.lock` 已对齐 `pyproject.toml`）
- [ ] `uv run alembic -c alembic.ini upgrade head` 升到 `20260501_0013_drop_ai_fallback`
- [ ] `uv run python scripts/bootstrap_platform_admin.py` 创建平台管理员成功
- [ ] `uv run uvicorn app.main:app --reload` 起 8000 端口，`curl http://localhost:8000/health` 返回 200

### 3.3 4 worker 启动（每条独立验证）

- [ ] `uv run python scripts/run_collection_worker.py --once`（一次性跑通，无异常）
- [ ] `uv run python scripts/run_collection_scheduler_worker.py --once`（一次性跑通）
- [ ] `uv run python scripts/run_scoring_worker.py --once`（一次性跑通）
- [ ] `uv run python scripts/run_sending_worker.py --once`（一次性跑通）

> 4 个 worker 都支持 `--once` 标志（实测 `scripts/*.py` 已加 `--once` argparse），可作健康自检入口。

### 3.4 前端启动

- [ ] `cd frontend && pnpm install` 无错
- [ ] `pnpm dev:admin` 起，浏览器打开默认端口可加载登录页
- [ ] `pnpm dev:tenant` 起，浏览器打开默认端口可加载登录页
- [ ] `pnpm type-check` / `pnpm lint` 无错

### 3.5 DB 连通

- [ ] 后端 `/health` 返回 200 表示 DB 连通
- [ ] alembic head = `0013`，`SELECT current_database()` = `clientget`

### 3.6 验证完成回报

请在以下回报：

```
本地启动验证：[全部通过 ✅ / 失败项 N 项]
失败项详情（如有）：
1. ...
```

---

## 4. 容器化（Dockerfile，T-DF-12）

### 4.1 后端镜像（共享）

**已存在**：[`backend/Dockerfile`](../../../backend/Dockerfile)

```dockerfile
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY 03_database ./03_database
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
RUN pip install --no-cache-dir uv && uv pip install --system .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**架构特性**：

- 同一个 image 用于 **backend API + 4 worker + cleanup_service（共 6 个 Sealos 应用）**
- Sealos 应用通过 **不同 `command:`** 区分用途（见 §5）
- 不需要每个 worker 单独 Dockerfile

**Slice 0 评估**：✅ 现有 Dockerfile 已就绪，**无需改动**。cleanup_service 在 Slice 1.B 接入时只需在 `scripts/` 下加 `run_cleanup_worker.py`，会被 `COPY scripts ./scripts` 自动打入。

### 4.2 前端镜像（admin / tenant 各 1）

**已存在**：

- [`frontend/Dockerfile.admin`](../../../frontend/Dockerfile.admin)
- [`frontend/Dockerfile.tenant`](../../../frontend/Dockerfile.tenant)

两份 Dockerfile 结构相同（multi-stage：node 构建 → nginx 1.27-alpine 静态托管 + `deploy/nginx-spa.conf`）。

**Slice 0 评估**：✅ 已就绪，**无需改动**。

### 4.3 docker-compose.prod.yml 增量（Slice 1.B 触发）

现状（已实测）：覆盖 backend + 4 worker，**未覆盖 cleanup_service**。

**Slice 1.B 接入清单**（T-DF-47）：

```yaml
# docker-compose.prod.yml 拟增加：
  cleanup-service:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      postgres:
        condition: service_healthy
    env_file:
      - .env
    environment: *runtime-env
    restart: unless-stopped
    command: >
      python scripts/run_cleanup_worker.py
      --sleep-seconds ${CLEANUP_WORKER_SLEEP_SECONDS:-10}
      --lease-seconds ${CLEANUP_TASK_LEASE_SECONDS:-300}
      --limit ${CLEANUP_WORKER_LIMIT:-20}
```

> **本 Slice 不修改** `docker-compose.prod.yml`。Slice 1.B（T-DF-47）在 cleanup_service 实现完成后由实施 PR 同步。

### 4.4 Docker 构建验证（用户任务，可选）

> Apple Silicon 必须 `--platform linux/amd64`，否则 Sealos pod 报 `exec format error`。

```bash
# 后端镜像
cd backend
docker buildx build --platform linux/amd64 \
  -t local/clientget-backend:slice-0-baseline \
  --load .

# Admin 前端
cd frontend
docker buildx build --platform linux/amd64 \
  -f Dockerfile.admin \
  --build-arg VITE_API_BASE_URL=http://localhost:8000 \
  -t local/clientget-admin:slice-0-baseline \
  --load .

# Tenant 前端
docker buildx build --platform linux/amd64 \
  -f Dockerfile.tenant \
  --build-arg VITE_API_BASE_URL=http://localhost:8000 \
  -t local/clientget-tenant:slice-0-baseline \
  --load .
```

**验收**：3 条 build 命令全部成功，输出 image hash。

---

## 5. Sealos 部署清单（T-DF-13）

### 5.1 现状：`SEALOS_DEPLOYMENT.md` 已有 8 单元

[`backend/docs/SEALOS_DEPLOYMENT.md`](../../../backend/docs/SEALOS_DEPLOYMENT.md) 已覆盖：

1. PostgreSQL（Sealos 数据库）
2. clientget-backend
3. clientget-collection-scheduler
4. clientget-collection-worker
5. clientget-scoring-worker
6. clientget-sending-worker
7. clientget-admin
8. clientget-tenant

每单元含：镜像、CPU/内存、端口、外网访问、启动命令、env 清单、健康检查（仅 backend `/health`）。

### 5.2 Slice 0 增量：第 9 单元 cleanup_service（占位）

| 项 | 值 |
|---|---|
| 应用名 | `clientget-cleanup-service` |
| 镜像 | 与 backend 同 image（不同 tag 时与 backend 一致） |
| 实例 | `1`（Slice 1.B 启用前可不创建） |
| CPU / 内存 | `0.5C / 512Mi` 起步 |
| 外网访问 | 关闭 |
| 启动命令（占位） | `sh -c 'python scripts/run_cleanup_worker.py --sleep-seconds 10 --lease-seconds 300 --limit 20'` |
| 环境变量 | 与 backend 同（含 `OPENROUTER_DECRYPT_KEY`，[`design.md`](../../../openspec/changes/v3-data-foundation/design.md) §11.2） |
| 健康检查 | Slice 4 加 `/health` 端点后启用 |

**操作时机**：

- **Slice 0 不创建**（cleanup_service 模块还不存在）
- **Slice 1.B 创建**（T-DF-47 实施部署）

### 5.3 9 部署单元 ↔ [`07-v3-scope-final.md`](../07-v3-scope-final.md) §9 对齐

| # | Sealos 应用名 | 类型 | Slice 0 状态 | Slice 1.B 状态 | scope-final §9 |
|---|---|---|:-:|:-:|:-:|
| 1 | `Postgres`（Sealos 内置） | 数据库 | 已部署 | 已部署 | ✅ |
| 2 | `clientget-backend` | API | 已部署 | 已部署 | ✅ |
| 3 | `clientget-collection-worker` | Worker | 已部署 | 已部署 | ✅ |
| 4 | `clientget-collection-scheduler` | Worker | 已部署 | 已部署 | ✅ |
| 5 | `clientget-scoring-worker` | Worker | 已部署 | 已部署 | ✅ |
| 6 | `clientget-sending-worker` | Worker | 已部署 | 已部署 | ✅ |
| 7 | **`clientget-cleanup-service`** | Worker | **未部署（占位）** | **新建** | ✅ |
| 8 | `clientget-admin` | 前端 | 已部署 | 已部署 | ✅ |
| 9 | `clientget-tenant` | 前端 | 已部署 | 已部署 | ✅ |

### 5.4 关于"k8s yaml" vs "Sealos 应用管理"

按 [`SEALOS_DEPLOYMENT.md`](../../../backend/docs/SEALOS_DEPLOYMENT.md)，本项目 **使用 Sealos 应用管理 UI**（不直接管 yaml）。每个应用通过 UI 表单填写：

- 镜像 / 端口 / CPU / 内存
- 启动命令
- 环境变量（批量粘贴）
- 健康检查 / 外网访问

**Slice 0 不产出独立 k8s yaml 文件**，因为 Sealos 部署不需要。`tasks.md` T-DF-13 的"Sealos k8s yaml"按 SEALOS_DEPLOYMENT.md 实际使用方式重定义为"Sealos 应用清单 + cleanup_service 第 9 单元"。**T-DF-13 在 §5.2 已完成。**

---

## 6. 健康检查与监控（C8-G5 模板，Slice 4 完整接入）

### 6.1 当前已有

| 单元 | 健康检查 |
|---|---|
| backend | `/health` 端点（[`docker-compose.prod.yml:13`](../../../backend/docker-compose.prod.yml) `python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"`）|
| 4 worker | `--once` 标志可做"启动自检"，无 HTTP 健康端点 |

### 6.2 Slice 4 完整化方向

[`02-current-implementation-gap-audit.md`](../02-current-implementation-gap-audit.md) C8-G5 + Slice 4 任务（T-DF-50）：

- worker base class（retry / heartbeat / idempotency / 结构化日志 / **HTTP `/health` 端点**）
- error_code / error_message 标准化
- 任务超时 + 幂等键（email_send_locks 等）

**Slice 0 仅记录**：上述能力 Slice 4（T-DF-50 ~ T-DF-54）实现，本基线**不修改**任何 worker 代码。

---

## 7. 人类维护者待补（建议清单）

> 按 [`AGENTS.md`](../../../AGENTS.md) §1，启动命令的"权威表述"在 AGENTS.md / CLAUDE.md（人类维护者维护）。AI 不直接改这两份。

### 7.1 AGENTS.md 建议增量

§1 工作区结构表已含 `_control/v3/slices/`（按 ce:compound 流程已加 `docs/solutions/`）。本基线不要求改 AGENTS.md。

### 7.2 [`_control/01-code-roots.md`](../../01-code-roots.md) 待复核

| 行号 | 内容 | 本基线结论 |
|---|---|---|
| §1.4 | "🟡 `[CONFIRM?]` 启动命令未实际运行" | **可移除 `[CONFIRM?]`**：本基线 §2 已与 `package.json` `scripts` 实测对齐 |
| §2.3 | "🟡 `[CONFIRM?]` 未读 `pyproject.toml`" | **可移除 `[CONFIRM?]`**：本基线 §2.2 已与 `pyproject.toml` 实测对齐 |
| §3 | "🟡 `[CONFIRM?]` `run_collection_scheduler.py` vs `run_collection_scheduler_worker.py`" | **可关闭**：本基线 §2.3 已澄清职责（一次性 vs 长期 worker） |
| §7 | "启动命令是否与上面推测一致" | **可关闭** |
| §7 | "前端 `Dockerfile.admin` 没有显式的 `push-admin.sh`" | **保留待确认**（本基线未审 push 脚本是否需要单独 push-admin.sh） |

### 7.3 [`_control/04-open-questions.md`](../../04-open-questions.md) 待登记

无新增 open question。所有 §7.2 的 `[CONFIRM?]` 待维护者批量关闭。

---

## 8. 验收

### 8.1 本基线验收（T-DF-14）

- [x] T-DF-10 `package.json` / `pyproject.toml` / 4 worker 启动脚本已读，命令记录在 §2
- [x] T-DF-11 本地验证全部通过（2026-05-07 实测）
- [x] T-DF-12 Dockerfile 评估完成（§4：现有 backend / admin / tenant Dockerfile 就绪，cleanup_service Slice 1.B 接入，无新 Dockerfile）
- [x] T-DF-13 Sealos 部署清单完成（§5：第 9 单元 cleanup_service 占位定义，§5.2）
- [x] T-DF-14 本基线报告产出
- [ ] T-DF-15 staging 验证基线（可选，Slice 1.A 前补做）

### 8.2 staging 验证（T-DF-15，用户任务）

- [ ] Sealos staging 环境登录 `clientget-backend` 应用，`/health` 返回 200
- [ ] Sealos staging 4 worker 应用全部 `running` 状态、日志无持续异常退出
- [ ] Sealos staging `clientget-admin` / `clientget-tenant` 可加载登录页
- [ ] Sealos staging Postgres 连通，`SELECT current_database()` = `clientget`
- [ ] alembic 当前版本与本基线 §1.2 一致（最新 = `20260501_0013_drop_ai_fallback`，落后则记录差距）

### 8.3 用户签字

```
本基线（Slice 0 dev-runtime-baseline v1.0）已审核：
- §1 当前基线（git / alembic / 技术栈）✅
- §2 启动命令实测 ✅
- §3 本地启动验证 ✅（2026-05-07 实测：3/4 worker 通过 + admin 3002 + tenant 3003）
- §4 容器化评估 ✅
- §5 9 部署单元清单 ✅
- §6 健康检查现状 ✅
- §7 人类维护者待补建议 ✅（知悉）
- §2.3.1 sending worker 已知漂移 ✅（已记录，Slice 1.B 修复）
- §8.2 staging 验证 ⬜（可选，Slice 1.A 前补做）

签字：lay (用户)   日期：2026-05-07
```

---

## 9. Slice 0 → Slice 1.A 解锁条件

签字本基线后，**Slice 1.A（alembic 升级，T-DF-20 ~ T-DF-23）解锁**：

- 跑 alembic 0007 ~ 0013 升级（已实测 head = `0013`，需在 staging / 生产升级到位）
- 校验真实 DB schema = `_control/inputs/database/schema.sql`
- 修正 schema.sql 漂移（F1: ORM models 空目录；F2: scoring_jobs / waimaotong_raw_contacts）
- 编写回滚 alembic 脚本

> **本基线不开始 Slice 1.A**。
