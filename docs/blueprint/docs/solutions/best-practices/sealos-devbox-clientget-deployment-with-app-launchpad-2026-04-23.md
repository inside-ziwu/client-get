---
title: Sealos DevBox 部署 ClientGet 并与应用管理配合上线
date: 2026-04-23
category: best-practices
module: clientget_deployment
problem_type: best_practice
component: development_workflow
severity: medium
applies_when:
  - 使用 Sealos DevBox 部署多单元项目
  - 需要将 backend、admin、tenant 通过 DevBox 发版并最终上线
  - 需要让 DevBox 与应用管理协同，而不是完全绕开应用管理
  - 遇到 Vite preview host 白名单、端口占用、entrypoint、域名与健康检查问题
tags: [sealos, devbox, deployment, app-launchpad, vite-preview, alembic, entrypoint]
---

# Sealos DevBox 部署 ClientGet 并与应用管理配合上线

## Context
这次上线链路同时覆盖了 3 个 DevBox 项目和 1 个 Sealos PostgreSQL：`clientget-backend`、`clientget-admin`、`clientget-tenant`。真实踩坑点集中在：

- 后端最初不是独立 Git 仓，DevBox 无法直接 clone
- GitHub 私有仓在 DevBox 里必须用 `PAT` 或 SSH，不能用密码
- `uv sync` 会被旧进程的 `.venv/.lock` 卡住
- DevBox 环境变量入口不稳定时，后端用仓库根目录 `.env` 更直接
- 后端拆独立仓后，Alembic 仍引用旧蓝图目录，迁移会找不到 `03_database/schema.sql`
- fresh DB 上，基线 schema 和增量迁移重复建表，导致迁移非幂等
- `vite preview` 会拦正式域名 host，也会因为旧进程占端口偷偷漂移到新端口
- backend 正式上线时，在应用管理里乱覆写启动命令，反而比默认入口更容易把容器搞挂

这次最终收口后的稳定结论是：

- `DevBox` 负责开发、调试、构建、发版
- `应用管理` 负责正式运行常驻单元
- `PostgreSQL` 直接用 Sealos 数据库产品

对 ClientGet 这类 `backend + admin + tenant + workers` 结构，最稳的拆分是：

- DevBox：`clientget-backend`、`clientget-admin`、`clientget-tenant`
- 应用管理：`clientget-scoring-worker`、`clientget-sending-worker`

## Guidance
### 1. 先把后端变成独立可 clone 仓库，再谈 DevBox 部署
如果后端目录不是 git 仓，DevBox 的第一步就会失败。先把后端推成独立仓，例如：

```bash
https://github.com/inside-ziwu/clientget-api.git
```

然后在 DevBox 中：

```bash
cd ~/project
git clone https://github.com/inside-ziwu/clientget-api.git
cd ~/project/clientget-api
```

私有仓不要再用 GitHub 密码，必须用 `PAT` 或 SSH。

### 2. `uv sync` 卡住时，先查锁，不要反复重跑
典型现象是：

```text
INFO Waiting to acquire exclusive lock for `.venv` at `.venv/.lock`
```

这通常说明前一个 `uv sync` 还活着。先查再杀：

```bash
ps -ef | grep '[u]v'
kill <PID>
rm -f .venv/.lock
uv sync -v
```

不要在锁还没释放时继续开新的 `uv sync`。

### 3. 后端优先让应用直接读仓库内 `.env`
Sealos DevBox 的编辑页不一定能稳定找到环境变量入口。对 FastAPI 后端，最稳的是直接在仓库根目录写 `.env`，因为配置层会自动读取它。

必须至少覆盖这些值：

```env
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://postgres:...@clientgetdb-postgresql.ns-3umexz0o.svc:5432/clientget
SYNC_DATABASE_URL=postgresql+psycopg://postgres:...@clientgetdb-postgresql.ns-3umexz0o.svc:5432/clientget
ALLOWED_ORIGINS=https://admin.xinanpcb.com,https://tenant.xinanpcb.com
JWT_SECRET=...
DATA_SOURCE_ENCRYPTION_KEY=...
INTERNAL_SERVICE_SECRET=...
ENGAGELAB_WEBHOOK_SECRET=...
```

如果环境变量丢失，Alembic 和 bootstrap 会回退到默认值 `localhost:5432`，直接报数据库连不上。

### 4. 独立后端仓的 Alembic 迁移必须和基线 schema 对齐
这次独立后端仓首轮失败不是数据库问题，而是迁移链和仓库拆分没对齐。

先修了两处：

- `20260421_0001_canonical_schema.py` 必须能在独立仓里找到 `03_database/schema.sql`
- `20260422_0004_tenant_ai_provider.py` 必须对 fresh DB 幂等，不能重复创建 `tenant_ai_provider_configs`

最终可工作的关键点是：

```python
# 0001
schema_path = Path(__file__).resolve().parents[2] / "03_database" / "schema.sql"
```

```python
# 0004
inspector = inspect(bind)
tables = set(inspector.get_table_names())

if "tenant_ai_provider_configs" not in tables:
    op.execute(...)
```

结论：如果基线 schema 已经包含某张表，后续增量迁移必须先探测现状再执行，不能假设目标库一定来自旧版本。

### 5. 前端在 DevBox 上一律用 `vite preview + strictPort`
必须同时处理两件事：

一是 host 白名单：

```ts
preview: {
  host: '0.0.0.0',
  allowedHosts: ['.sealosbja.site', '.xinanpcb.com'],
}
```

必要时再加运行时兜底：

```bash
__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS=admin.xinanpcb.com
```

二是端口漂移。必须加 `--strictPort`：

```bash
vite preview --host 0.0.0.0 --port 3000 --strictPort
```

否则一旦 `3000` 被旧进程占着，Vite 会跳到 `3004`，但 DevBox 公网映射还是 `3000`，外部看到的就永远是旧服务。

### 6. DevBox 只做 `backend/admin/tenant`，worker 放应用管理
这次落地后的稳定结论：

- `backend/admin/tenant` 需要调试、构建、预览、发版，适合 DevBox
- `scoring-worker/sending-worker` 只需要常驻运行，适合应用管理

不要为了“统一”把 worker 也塞进 DevBox。

### 7. backend 正式上线时，优先使用 DevBox 根目录 `entrypoint.sh`
这次最容易把服务搞挂的一步，是在应用管理里手写这些高风险覆盖：

```bash
/bin/bash -c ...
/bin/bash -lc ...
/home/devbox/project/entrypoint.sh prod
```

这些做法在 Sealos 的参数拆分里非常容易出错，直接进入 crash loop。

稳定做法是：

- DevBox 根目录放好 `entrypoint.sh`
- 重新发布 backend 版本
- 应用管理里清空手工覆写命令
- 让应用使用默认入口
- 健康检查走 `/health`

后端项目根目录脚本形态：

```bash
#!/bin/bash
set -e
cd /home/devbox/project/clientget-api
exec .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

### 8. 健康检查永远打 `/health`，不是 `/`
FastAPI 根路径 `/` 返回 `404` 是正常的。真正健康检查是：

```bash
https://api.xinanpcb.com/health
```

只有这个返回：

```json
{"data":{"status":"ok"}}
```

才算 backend 正常。

## Why This Matters
这套经验的价值不在“把服务跑起来一次”，而在于避免反复掉进同一类部署坑里：

- 没独立仓，DevBox 无法标准化 clone 与发版
- 没有迁移幂等，fresh DB 上线会直接炸
- 前端 preview 不控 host 和端口，域名接好了也像没接好
- 在应用管理里硬改启动命令，问题会从“应用没起来”升级成“容器反复重启”
- worker 放错位置，会显著增加部署和维护复杂度

换句话说，这不是“某次偶然修通”，而是一套已经被真实错误反复验证过的部署收口方式。

## When to Apply
- 用 Sealos DevBox 发布多应用项目，而不是单体静态站点
- 后端仓和前端仓分离，且前端需要 Vite preview 暂时承载
- 应用要挂正式域名，同时还要先经过 Sealos 的 `*.sealosbja.site` 公网调试域名
- 数据库不跑在 DevBox 内，而是独立的 Sealos PostgreSQL
- 需要把 DevBox 发版与应用管理长期运行单元配合起来

## Examples
### 后端最小可用路径
```bash
cd ~/project
git clone https://github.com/inside-ziwu/clientget-api.git
cd ~/project/clientget-api
~/.local/bin/uv sync

cat > .env <<'EOF'
APP_ENV=production
DEBUG=false
DATABASE_URL=postgresql+asyncpg://postgres:...@clientgetdb-postgresql.ns-3umexz0o.svc:5432/clientget
SYNC_DATABASE_URL=postgresql+psycopg://postgres:...@clientgetdb-postgresql.ns-3umexz0o.svc:5432/clientget
ALLOWED_ORIGINS=https://admin.xinanpcb.com,https://tenant.xinanpcb.com
EOF

.venv/bin/python -m alembic -c alembic.ini upgrade head
.venv/bin/python scripts/bootstrap_platform_admin.py
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Admin DevBox 预览命令
```bash
cd ~/project/client-get
git pull
pnpm build:admin
__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS=admin.xinanpcb.com \
pnpm --filter @apps/admin exec vite preview --host 0.0.0.0 --port 3000 --strictPort
```

### Tenant DevBox 预览命令
```bash
cd ~/project/client-get
git pull
pnpm build:tenant
__VITE_ADDITIONAL_SERVER_ALLOWED_HOSTS=tenant.xinanpcb.com \
pnpm --filter @apps/tenant exec vite preview --host 0.0.0.0 --port 3001 --strictPort
```

### 不要再用的做法
```bash
git clone https://github.com/... .
```

前提是当前目录必须是空的，否则直接失败。

```bash
GitHub 用户名 + 密码
```

Git 操作已经不支持密码，私有仓要用 `PAT` 或 SSH。

```bash
pnpm ... preview --port 3000
```

但不加 `--strictPort`。这会导致端口漂移。

```bash
/bin/bash -c
/home/devbox/project/entrypoint.sh prod
```

这种在应用管理里覆写命令的方式不要再用。

## Related
- [backend/docs/SEALOS_DEPLOYMENT.md](/Users/lay/Documents/Github/client_get/backend/docs/SEALOS_DEPLOYMENT.md:1)
- [docs/AGENT_PROGRESS.md](/Users/lay/Documents/Github/client_get/blueprint/docs/AGENT_PROGRESS.md:1)
- [docs/NEXT_SESSION_PROMPT.md](/Users/lay/Documents/Github/client_get/blueprint/docs/NEXT_SESSION_PROMPT.md:1)
