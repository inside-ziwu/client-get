# CLAUDE.md

> Claude Code 专用补充约束。**先读 [AGENTS.md](AGENTS.md)，并以 AGENTS.md 为最高约束；本文件只补充 Claude 特有项。**

## 1. 行动入口

- 实施类任务必须先确认当前对应的 plan 产物（`docs/plans/…-plan.md` 或 `docs/superpowers/plans/…`）；没有对应 plan，不得直接改代码或写新文档。
- 若尚无 plan，按 `~/Projects/CLAUDE.md`「AI 编程工作流」路径 A/B：`ce-brainstorm` →（路径 B 加 `ce-plan`）→ `writing-plans` 产出后再实施。工作流细则见 [AGENTS.md](AGENTS.md) §3/§6。

## 2. 与 Skill 的协作

- bugfix、需求、行为调整、重构、部署变更都必须走当前工作流（compound-engineering + superpowers 主链，见 [AGENTS.md](AGENTS.md) §3）；非功能开发的轻量改动除外。
- 实施前如有歧义、冲突、缺口或验收标准不清，必须先使用 AskUserQuestion 工具澄清；用户确认后写入当前 plan 产物。
- 收尾前必须调用 `verification-before-completion` skill，并输出「原始需求 → 已实现/未实现」对照。

## 3. 输出语言

中文。注释、提交信息、文档全部中文。

## 4. 不要做的事

- 不要移动或重命名 `docs/` 下的历史文档与 `docs/specs/`（工作流产物目录 `docs/plans`、`docs/brainstorms`、`docs/superpowers`、`docs/handovers` 由对应 skill 正常写入，不在此列）。
- 不要凭记忆引用文件路径；先 grep / read 再说。
- 不要把历史文档、现状代码、口头推测直接当作实施命令；必须先沉淀到当前 plan 产物。
- 不要在当前 plan 产物之外写过程性决策、计划、调研。

## 5. 模块说明

单一 monorepo，所有代码和 PM 资产在同一个 git 历史中。入口以实际目录和当前 plan 产物为准；

- 前端：[`frontend/apps/tenant/`](frontend/apps/tenant/)（租户端）+ [`frontend/apps/admin/`](frontend/apps/admin/)（管理端）+ [`frontend/packages/`](frontend/packages/) 共享包
- 后端 API：[`backend/app/main.py`](backend/app/main.py)，路由分布在 [`backend/app/api/`](backend/app/api/)
- 后端分层：[`backend/app/services/`](backend/app/services/)（业务逻辑+SQL）、[`backend/app/schemas/`](backend/app/schemas/)、[`backend/app/integrations/`](backend/app/integrations/)、[`backend/app/db/`](backend/app/db/)（连接池+RLS）
- Worker：[`backend/app/workers/`](backend/app/workers/)；启动脚本在 [`backend/scripts/`](backend/scripts/)
- 数据库：Alembic 入口 [`backend/alembic/`](backend/alembic/)；迁移文件以 [`backend/alembic/versions/`](backend/alembic/versions/) 实际内容为准
- 部署脚本：后端 [`backend/scripts/push-backend.sh`](backend/scripts/push-backend.sh)，前端 [`frontend/deploy/push-admin.sh`](frontend/deploy/push-admin.sh) / [`frontend/deploy/push-tenant.sh`](frontend/deploy/push-tenant.sh)

## 6. 环境与部署

### 环境变量

- 各端在自己根目录维护 `.env`，互不干扰：
  - `backend/.env` — `CLIENTGET_DEV_DATABASE_URL`（Neon）+ `CLIENTGET_PROD_DATABASE_URL`（Sealos）
  - `frontend/apps/tenant/.env` — `NEXT_PUBLIC_API_BASE_URL`
  - `frontend/apps/admin/.env` — `NEXT_PUBLIC_ADMIN_API_BASE_URL`
- `.env` 值由用户手动维护，不得自动修改。
- 开发环境和生产环境完全隔离，没有"切换"动作。

### 开发环境

- 数据库：Neon 云数据库（`CLIENTGET_DEV_DATABASE_URL`）
- 后端：本地 `uvicorn`
- 前端：本地 `next dev`

### 生产环境

- 数据库：Sealos PostgreSQL（环境变量由 Sealos 控制台注入容器）
- 后端 + 前端：均为 Sealos 容器，镜像托管在阿里云 ACR

### 部署流程（开发验证通过后）

1. 代码推送到 GitHub
2. 在 GitHub Actions 手动触发 `workflow_dispatch`（选择 service：admin / tenant / backend）
3. GitHub Actions 在 amd64 runner 上构建 Docker 镜像并推送到阿里云 ACR
4. 在 Sealos 控制台更新对应服务的镜像 tag

- 本地 `push-*.sh` 脚本仅用于本地调试验证，不用于正式发布（本机 ARM 交叉编译 amd64 很慢）。
- 前端 API 地址在构建时通过 `--build-arg` 注入（`https://api.xinanpcb.com`），不走 `.env`。
- 后端镜像启动时 `/start.sh` 自动执行 `alembic upgrade head`。
- 同步生产快照属于外部副作用，必须由用户明确触发，不得因普通实施任务自动执行。

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
