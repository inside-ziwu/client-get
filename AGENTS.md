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

> 给所有 AI 编码代理（Claude Code / Codex / 其他）的最高工作约束。本文件只写项目身份与不可协商的安全红线；**编码约定、验证门禁、Git 流程、领域口径、运维细则全部在 `.trellis/spec/`**（按 Trellis 的 before-dev 流程在编码前读取）。架构、命令、部署与功能现状见 [README.md](README.md)；债务见 GitHub Issues（`gh issue list`，P0–P3 label）。发现本文或 spec 与代码不符时，以代码 + 测试为准，并修订文档。

## 0. 项目身份

面向外贸制造企业的多租户获客与邮件营销 SaaS（当前投产行业：PCB 出海获客）。核心链路：外部采购商数据入池 → 筛选与评分 → 序列邮件触达 → 投递状态回传。客户付费的根基是两条能力，任何改动不得削弱：

1. **租户数据隔离**；
2. **邮件发送可靠**：不重复发送、遵守收件人时区与工作日窗口、保护发信域名信誉。

**明确不做**：回信监控（收件箱回复检测/同步）——2026-07-11 拍板放弃，不提案、不实现；重启前先做邮件服务商回信检测能力调研，经用户拍板后方可从本清单移除。

## 1. 安全红线（不可协商）

- **生产数据库默认只读**。任何直接或间接写入，必须先展示具体 SQL 与影响范围，取得用户针对该次操作的明确确认（执行细则见 `.trellis/spec/guides/production-operations.md`）。
- **外部副作用由用户显式触发**：推送镜像、上线、同步线上快照、调用外部平台写接口，不得作为普通任务的附带动作自动执行。
- **`.env` 由用户手动维护，禁止自动修改**。真实凭证、客户数据、Webhook 原文不得写入代码、文档、日志样例。
- **租户隔离过滤必须显式写在 service 层 SQL 里**：租户业务表过滤 `tenant_id`，平台级表过滤 `instance_id`，两类字段兼有的表两个都带。当前 RLS 仅名义启用（policy 不全、连接角色可绕过），**不得以"数据库有 RLS"为由省略应用层过滤**；改动隔离相关代码必须保留或新增隔离测试（表分类与写法见 `.trellis/spec/backend/database-guidelines.md`）。

## 2. 规范索引（`.trellis/spec/`）

| 入口 | 内容 |
|---|---|
| [backend/index.md](.trellis/spec/backend/index.md) | 分层与路由、API 约定、数据库与迁移纪律、行为口径、worker、错误与日志、质量门禁 |
| [frontend/index.md](.trellis/spec/frontend/index.md) | workspace 与页面模式、设计系统与组件契约、状态管理、类型契约、质量门禁 |
| [guides/index.md](.trellis/spec/guides/index.md) | 跨层思考、代码复用、Git 工作流、收尾清单、生产运维 |

中文：沟通、注释、提交信息、文档一律中文。
