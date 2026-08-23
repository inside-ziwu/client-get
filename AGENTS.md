<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

This project is managed by Trellis. The working knowledge you need lives under `.trellis/`:

- `.trellis/workflow.md` — development phases, when to create tasks, skill routing
- `.trellis/spec/` — package- and layer-scoped coding guidelines (read before writing code in a given layer)
- `.trellis/workspace/` — per-developer journals and session traces
- `.trellis/tasks/` — active and archived tasks (PRDs, research, jsonl context)

If a Trellis command is available on your platform (e.g. `/trellis:finish-work`, `/trellis:continue`), prefer it over manual steps. Not every platform exposes every command.

If you're using Codex or another agent-capable tool, additional project-scoped helpers may live in:
- `.agents/skills/` — reusable Trellis skills
- `.codex/agents/` — optional custom subagents

Managed by Trellis. Edits outside this block are preserved; edits inside may be overwritten by a future `trellis update`.

<!-- TRELLIS:END -->

# AGENTS.md

> 给所有 AI 编码代理（Claude Code / Codex / 其他）的最高工作约束。本文件只写红线、纪律与项目特有约定；架构、命令、产品口径、部署与运维等事实见 [README.md](README.md)（仓库总入口），逐条债务见 GitHub Issues（`gh issue list`，优先级为 P0–P3 label），踩坑库见 `docs/solutions/`。发现本文与代码不符时，以代码 + 测试为准，并修订本文。

## 0. 项目身份

面向外贸制造企业的多租户获客与邮件营销 SaaS（当前投产行业：PCB 出海获客）。核心链路：外部采购商数据入池 → 筛选与评分 → 序列邮件触达 → 投递状态回传。客户付费的根基是两条能力，任何改动不得削弱：

1. **租户数据隔离**；
2. **邮件发送可靠**：不重复发送、遵守收件人时区与工作日窗口、保护发信域名信誉。

**明确不做**：回信监控（收件箱回复检测/同步）——2026-07-11 拍板放弃，不提案、不实现；重启前先做邮件服务商回信检测能力调研，经用户拍板后方可从本清单移除。

## 1. 安全红线（不可协商）

- **生产数据库默认只读**。任何直接或间接写入，必须先展示具体 SQL 与影响范围，取得用户针对该次操作的明确确认。
- **外部副作用由用户显式触发**：推送镜像、上线、同步线上快照、调用外部平台写接口，不得作为普通任务的附带动作自动执行。
- **`.env` 由用户手动维护，禁止自动修改**。真实凭证、客户数据、Webhook 原文不得写入代码、文档、日志样例。
- **租户隔离过滤必须显式写在 service 层 SQL 里**：
  - 租户业务表（`tenant_companies`、`tenant_contacts`、`sending_plans`、`emails` 等）：显式过滤 `tenant_id`；
  - 平台级表（`tenants`、`platform_users`、`ai_models` 等）：显式过滤 `instance_id`；
  - 两类字段兼有的表：两个都带。
  - 当前 RLS 仅名义启用（policy 不全、连接角色可绕过），**不得以"数据库有 RLS"为由省略应用层过滤**。改动隔离相关代码时必须保留或新增对应隔离测试。

## 2. 数据库事实纪律

- `backend/03_database/schema.sql` 是手工蓝图，已知与生产存在漂移（细目见 issue #61「Schema 主权收复」与 #64「空库无法从 Alembic 基线建库」），**不得单独作为实施依据**；数据模型事实以 alembic 迁移链 + 生产核对为准。#61 ④ 的 pg_dump 化落地后 schema.sql 转为生成物，届时禁止手改（结构快照契约已先行：`backend/03_database/schema_snapshot.json`，git diff 即带外变更探测器）。
- 每次 schema 变更一个 alembic revision。backend 镜像启动会自动执行 `alembic upgrade head`，**迁移失败会直接阻断 API 启动**——迁移合并前必须核对存量数据与 FK 链。
- `waimaotong_*` 等外部直写表的 schema 主权不在本仓库：对其结构、数据或关联 FK 的任何变更，先与用户确认。

## 3. 验证纪律

- SQL 语义、时区/发送窗口、状态机推进、分区表操作**不能只靠 mock 测试**，须在隔离开发库做可回滚的断言式验证。
- 可用门禁：`uv run pytest -q`（backend）、`pnpm type-check`（frontend）。已知失效命令以 README「测试」一节的清单为准（当前：根 `pnpm lint`、tenant `test:contract`），修复前不得写入任何门禁。
- 收尾必须附验证证据（测试输出 / type-check / 手工验收记录），如实报告失败与未验证项。

## 4. 工作流

- 只读任务（分析、review、咨询、运维查询）：直接完成。轻量改动（文档、注释、配置、样式微调）：直接实施。
- 功能开发 / 行为变更 / 重构 / 数据库迁移：先给简短方案（改什么、影响面、验证方式），经用户确认后动手；遇歧义、冲突或验收标准不清，向用户澄清，不自行选边。
- 收尾三件事：① 跑与改动匹配的验证并附证据；② 债务销账走 Issues——修复 PR 描述带 `Fixes #NN` 随合并自动关闭，新发现值得单独修的问题用 `gh issue create` 登记（写明来源 / 缺口 / 验收，打 P0–P3 优先级 label）；③ 行为变更同步相关文档，新踩坑沉淀到 `docs/solutions/`。
- 多会话并行是常态：提交作业用 git worktree 隔离；提交时列出文件白名单，避免卷入其他会话的 WIP。

## 5. 编码约定

- 后端分层：api（路由/参数/权限）→ services（业务逻辑 + 手写 SQL，AsyncConnection，无 ORM 实体层）→ db/pools。route 层不写业务逻辑。
- **API 请求与响应一律用 Pydantic model 定义，禁止 `payload: dict` 裸收参**；存量裸 dict 端点在被修改时顺手改造，逐步向 OpenAPI 契约生成过渡。
- 修改后端响应结构时，同步检查 `frontend/packages/shared-types` 与 `shared-api`（前端类型目前手写，无编译期契约保证）。
- 新增静态路由必须放在动态 `/{id}` 路由之前。
- 前端：服务端状态用 React Query，认证状态用 Zustand；UI 原语一律来自 `@shared/ui`，不在 app 内重复造；改 Admin/Tenant UI 前先读 [DESIGN.md](DESIGN.md)。
- 中文：沟通、注释、提交信息、文档一律中文。命名：Python snake_case；TypeScript camelCase 变量 / PascalCase 组件。
- KISS：不做无需求的重构、不做过度防御性设计。

## 6. Git

- 新功能、bug 修复、重构、数据库迁移、API 变更：分支 → PR → 合并；分支命名 `feat/`、`fix/`、`refactor/`、`docs/` + 简短描述。文档、注释、配置等非功能改动可直推 main。
- 合并时机：功能完整、本地验证通过即可，不等完美，但不得破坏现有功能。
