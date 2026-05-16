# CLAUDE.md

> Claude Code 专用补充约束。**先读 [AGENTS.md](AGENTS.md)，并以 AGENTS.md 为最高约束；本文件只补充 Claude 特有项。**

## 1. 行动入口

- 实施类任务必须先确认当前 `openspec/changes/<change-id>/`；没有合适 change，不得直接改代码或写新文档。
- 若用户未指定 change，先用 `openspec list` 查看 active changes，再判断是否需要创建或补齐 change。
- `_control/` 只按任务需要读取；不再作为所有任务的固定前置真源。

## 2. 与 Skill 的协作

- bugfix、需求、行为调整、重构、部署变更都必须走 OpenSpec（`openspec/changes/`）。
- 实施前如有歧义、冲突、缺口或验收标准不清，必须先使用 AskUserQuestion 工具澄清；用户确认后写入当前 OpenSpec change。
- 收尾前必须调用 `verification-before-completion` skill，并输出「原始需求 → 已实现/未实现」对照。

## 3. 输出语言

中文。注释、提交信息、文档全部中文。

## 4. 不要做的事

- 不要移动或重命名 `docs/`、`blueprint/` 下的任何文件。
- 不要凭记忆引用文件路径；先 grep / read 再说。
- 不要把历史文档、现状代码、口头推测直接当作实施命令；必须先沉淀到当前 OpenSpec change。
- 不要在当前 OpenSpec change 之外写过程性决策、计划、调研；确需沉淀长期控制信息时，再按 AGENTS.md 读取并更新 `_control/`。

## 5. 模块说明

单一 monorepo，所有代码和 PM 资产在同一个 git 历史中。入口以实际目录和当前 OpenSpec change 为准；历史入口索引如需追溯，可查看 `_control/archive/root-control/`。

- 前端：[`frontend/apps/tenant/`](frontend/apps/tenant/)（租户端）+ [`frontend/apps/admin/`](frontend/apps/admin/)（管理端）+ [`frontend/packages/`](frontend/packages/) 共享包
- 后端 API：[`backend/app/main.py`](backend/app/main.py)，路由分布在 [`backend/app/api/`](backend/app/api/)
- 后端分层：[`backend/app/services/`](backend/app/services/)（业务逻辑+SQL）、[`backend/app/schemas/`](backend/app/schemas/)、[`backend/app/integrations/`](backend/app/integrations/)、[`backend/app/db/`](backend/app/db/)（连接池+RLS）
- Worker：[`backend/app/workers/`](backend/app/workers/)；启动脚本在 [`backend/scripts/`](backend/scripts/)
- 数据库：Alembic 入口 [`backend/alembic/`](backend/alembic/)；迁移文件以 [`backend/alembic/versions/`](backend/alembic/versions/) 实际内容为准
- 部署脚本：后端 [`backend/scripts/push-backend.sh`](backend/scripts/push-backend.sh)，前端 [`frontend/deploy/push-admin.sh`](frontend/deploy/push-admin.sh) / [`frontend/deploy/push-tenant.sh`](frontend/deploy/push-tenant.sh)

## 6. 本地数据库与线上快照同步

- 同步线上快照属于外部副作用，必须由用户明确触发，不得因普通实施任务自动执行。
- 本地开发库：`clientget`
- 每次需要用线上同数据测试前，在后端目录运行：

  ```bash
  cd backend
  ./scripts/sync_prod_db_to_local.sh
  ```
