# ClientGet 后端从 0 实现交付包（修复版）

> 目标：把用户提供的需求 Spec、现有系统说明、数据库/API/前端/采集/AI/迁移设计文档统一修复为一套可直接交给 Codex / Claude Code 继续写后端代码的最终文档。

## 这次交付的边界

当前没有后端源码仓库，因此本包不包含代码 diff，也不声称已经改过后端代码。本包交付的是：

1. **修复后的最终需求与设计文档**：已把原文档之间的冲突、缺表、缺字段、状态机不一致、API/前端映射缺口统一为单一口径。
2. **从 0 写后端的架构蓝图**：FastAPI + PostgreSQL + RLS + 独立采集服务 + OpenRouter AI 计费 + EngageLab 发送/Webhook。
3. **数据库 Schema 草案**：`03_database/schema.sql` 可作为 Alembic 迁移的蓝本，不建议直接一次性裸跑到生产。
4. **API 合同与前端对应关系**：Codex/Claude Code 可据此生成 routers / schemas / services / repositories。
5. **开发计划、任务清单、验收测试**：按 P0/P1/P2 分阶段实现。

## 阅读顺序

建议让代码 Agent 按以下顺序阅读：

1. `07_implementation_plan/CODEX_CLAUDE_MASTER_PROMPT.md`
2. `00_SOURCE_OF_TRUTH_DECISIONS.md`
3. `01_final_repaired_docs/07_REQUIREMENTS_SPEC_REPAIRED.md`
4. `02_architecture/BACKEND_ARCHITECTURE.md`
5. `03_database/schema.sql`
6. `04_api/API_CONTRACT.md`
7. `06_frontend_alignment/FRONTEND_BACKEND_ALIGNMENT.md`
8. `07_implementation_plan/DEVELOPMENT_PLAN.md`
9. `03_database/RLS_POLICY_MATRIX.md`
10. `04_api/FASTAPI_ROUTE_ORDERING.md`
11. `09_self_audit/SELF_AUDIT_REPORT.md`
12. `07_implementation_plan/ACCEPTANCE_TEST_PLAN.md`

## 目录说明

| 目录 | 内容 |
|---|---|
| `00_original_sources/` | 用户上传的原始 00-14 文档与 `business-flows-v2.html`，仅作追溯引用。 |
| `01_final_repaired_docs/` | 修复后的最终文档，作为实现真源。 |
| `02_architecture/` | 后端架构、安全/RLS/认证、服务边界。 |
| `03_database/` | 最终 Schema、迁移顺序、DDL 注意事项。 |
| `04_api/` | Admin/Tenant/Internal/Webhook API 合同与路由矩阵。 |
| `05_services/` | 采集、评分、AI 计费、发送/Webhook 服务逻辑。 |
| `06_frontend_alignment/` | 前端页面与后端 API 一一对应矩阵。 |
| `07_implementation_plan/` | 开发计划、任务清单、代码 Agent 提示词、验收测试。 |
| `08_references/` | 溯源、注意事项、待 Owner 确认问题。 |
| `09_self_audit/` | 交付包自审报告，记录发现并已修复的问题。 |
| `machine_readable/` | YAML/JSON 形式的任务、实体、状态机、API 路由，便于 Agent 解析。 |

## 最重要的实现约束

- Phase 1 后端可以是单 FastAPI 进程，但必须按 Admin / Tenant / Internal / Webhook 四类入口隔离。
- Tenant API 必须使用 PostgreSQL RLS；所有请求通过 URL slug 与 JWT `tid` 交叉校验。
- 前端路由不承载 slug；只有 Tenant API 使用 `/t/{slug}/api/v1/*`。
- Admin 端使用平台身份 `platform_admin`，不要塞进租户 `user_roles` 的 `admin/operator/viewer` 枚举。
- 发送计划只负责发送，不再承载采集/清洗/生成 9 状态流水线。
- AI 计费必须使用“预授权 hold → provider 调用 → 实际 token 结算 → 差额补扣/释放”的状态机。
- 分区表（emails / audit_logs / intelligence_articles）分页必须使用 `(created_at, id)` 双字段游标。
- 采集服务不可信任外部上传的 tenant_ids；主系统必须基于本地 `collection_task_keywords` 反解租户归属。

## 当前仍需业务确认的点

详见 `08_references/OWNER_OPEN_QUESTIONS.md`。若没有进一步确认，本包已给出 Phase 1 推荐默认值，代码 Agent 可先按默认值实现。


## 自审状态

已完成一轮结构化自审，并将发现的问题修入本包。重点补齐：RLS 覆盖漏项、AI 计费状态机与 schema 不一致、FastAPI 静态/动态路由注册顺序、机器可读 API 路由不完整。详见 `09_self_audit/SELF_AUDIT_REPORT.md`。
