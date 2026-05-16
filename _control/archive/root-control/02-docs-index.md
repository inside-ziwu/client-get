# 02 · 文档索引（语义层）

> **目的**：把散落在 `docs/`、`blueprint/`、`backend/docs/` 的所有文档汇成一份可检索的索引，逐文件标注用途分类。
> **原则**：只索引，不搬动；原文件保持原位置只读。
> **盘点时间**：2026-05-04
> **覆盖**：`docs/` 根级 8 份 + blueprint 根级 3 份 + blueprint 00–09 / `machine_readable/` / 内部 `docs/` 顶层 + `backend/docs/` 7 份共 ~38 份；`docs/meetings`、`docs/research`、`docs/source-materials`、`docs/archive`、blueprint 各子目录的更深层文件**未递归**——目录摘要见 §2.2。

## 标签图例

| 标签 | 含义 |
| --- | --- |
| `[BASELINE?]` | 可能是当前 V3 开发基线（活跃文档） |
| `[HISTORY]` | 可能是历史版本 / 已被取代 |
| `[DOCS]` | 文档资料 |
| `[DEPLOY]` | 部署资料 |
| `[CONFIRM?]` | 用途待确认 |
| `[CODE-AGENT]` | 给编码代理（Codex/Claude）看的入口 |

---

## 1. `docs/` 根级（活跃产品/技术文档）

| 文件 | 标签 | 一句话摘要 |
| --- | --- | --- |
| [`docs/business-flow-DRAFT.md`](../docs/business-flow-DRAFT.md) | `[DOCS]` `[BASELINE?]` | 与业务方对话的业务流梳理工作稿（更新于 2026-05-01），含用例图 UC-01~UC-33；将演化为正式 `business-flow.md` + `business-status-map.md` |
| [`docs/plan-phase1-contacts-pipeline.md`](../docs/plan-phase1-contacts-pipeline.md) | `[DOCS]` `[BASELINE?]` | Phase 1 部署前补丁（v3）：只修"外贸通联系人静默丢弃"P0 bug；其他重构推迟到 Phase 1.5 |
| [`docs/plan-phase1-implementation.md`](../docs/plan-phase1-implementation.md) | `[DOCS]` `[BASELINE?]` | Phase 1 编码任务拆分（T-1~T-6），对应 `spec-collection-module.md` v1.4 §8.1 |
| [`docs/plan-waimaotong-adapter.md`](../docs/plan-waimaotong-adapter.md) | `[DOCS]` `[BASELINE?]` | 外贸通直采 Adapter 实施规划 v2：SEARCH→DETAIL→CONTACT 三接口链 |
| [`docs/spec-collection-module.md`](../docs/spec-collection-module.md) | `[DOCS]` `[BASELINE?]` | 采集模块主规范 v1.4：外贸通直采 + 腾道反推 + PG Outbox 异步清洗管道 |
| [`docs/spec-collection-module-review.md`](../docs/spec-collection-module-review.md) | `[DOCS]` `[HISTORY]` | 采集模块 spec v1.1 的 CEO+Eng 双视角审查报告（针对旧版本） |
| [`docs/spec-phase1.5-collection-pipeline-refactor.md`](../docs/spec-phase1.5-collection-pipeline-refactor.md) | `[DOCS]` `[BASELINE?]` | Phase 1.5 清洗管道重构 spec：集中处理多租户关联、cleanup_queue 缺口等结构性债务 |
| [`docs/spec-tendata-provider.md`](../docs/spec-tendata-provider.md) | `[DOCS]` `[BASELINE?]` | 腾道 Provider spec v1.0：废弃 open-api，改 Cookie 会话 HTTP 爬取 |

## 2. `docs/` 子目录

### 2.1 入口指引

| 目录 | 文件数 | 标签 | 角色 |
| --- | --- | --- | --- |
| [`docs/guide/`](../docs/guide/) | 1 | `[DOCS]` | 含「项目目录导航.md」 |
| [`docs/meetings/`](../docs/meetings/) | 22 | `[DOCS]` `[HISTORY]` | 会议记录（最大子目录） |
| [`docs/research/`](../docs/research/) | 16 | `[DOCS]` `[BASELINE?]` | 调研材料（含 tendata-field-mapping、爬虫 captures） |
| [`docs/source-materials/`](../docs/source-materials/) | 4 | `[DOCS]` | 原始材料 |
| [`docs/session-records/`](../docs/session-records/) | 1 | `[DOCS]` `[HISTORY]` | 历史会话 |
| [`docs/archive/`](../docs/archive/) | 15 | `[DOCS]` `[HISTORY]` | 已归档 |

### 2.2 子目录文件未递归

> 子目录文件按需补摘要——优先级建议：`research/tendata-*` > `meetings/`（按时间倒序补 5–10 份近期）> `archive/`（仅标"为何归档"）。

---

## 3. `blueprint/` 根级

| 文件 | 标签 | 一句话摘要 |
| --- | --- | --- |
| [`README.md`](../blueprint/README.md) | `[DOCS]` | 蓝图包总入口：交付边界与建议阅读顺序 |
| [`00_SOURCE_OF_TRUTH_DECISIONS.md`](../blueprint/00_SOURCE_OF_TRUTH_DECISIONS.md) | `[DOCS]` `[BASELINE?]` | **最高优先级真源**：解决 business-flows-v2 / 00-06 旧文档 / 07-14 设计文档之间的冲突 |
| [`CODEX_START_HERE.md`](../blueprint/CODEX_START_HERE.md) | `[CODE-AGENT]` `[BASELINE?]` | 给 Codex 的从零开发启动说明，含文档优先级判断顺序 |

## 4. blueprint 00–09 顶层

### `00_original_sources/`（17 项） · `[HISTORY]`

原始资料，**不作实现依据**，保留追溯。已被 `01_final_repaired_docs/` 整体取代。

### `01_final_repaired_docs/`（10 项） · `[BASELINE?]`

| 文件 | 摘要 |
| --- | --- |
| `00_TO_06_EXISTING_SYSTEM_REPAIR_NOTES.md` | 旧系统 00-06 文档的修订说明 |
| `07_REQUIREMENTS_SPEC_REPAIRED.md` | 修订后的需求 spec（实现真源） |
| `08_UI_SPEC_REPAIRED_BACKEND_ALIGNMENT.md` | UI spec 修订 + 后端对齐 |
| `09_DATABASE_DESIGN_REPAIRED.md` | 数据库设计修订 |
| `10_API_DESIGN_REPAIRED.md` | API 设计修订 |
| `11_FRONTEND_ARCHITECTURE_REPAIRED.md` | 前端架构修订 |
| `12_COLLECTION_SERVICE_REPAIRED.md` | 采集服务设计修订 |
| `13_AI_INTEGRATION_REPAIRED.md` | AI 集成修订 |
| `14_DATA_MIGRATION_REPAIRED.md` | 数据迁移修订 |
| `REPAIR_COVERAGE_FOR_ALL_UPLOADED_DOCS.md` | 修订覆盖度自检 |

### `02_architecture/` · `[BASELINE?]`

| 文件 | 摘要 |
| --- | --- |
| `BACKEND_ARCHITECTURE.md` | 后端整体架构：FastAPI + PG + RLS + 独立采集 + OpenRouter + EngageLab |
| `SECURITY_RLS_AUTH_ARCHITECTURE.md` | 安全 / RLS / 鉴权架构 |

### `03_database/` · `[BASELINE?]`

| 文件 | 摘要 |
| --- | --- |
| `schema.sql` | 数据库 schema 草案（与 `backend/03_database/schema.sql` MD5 相同——重复） |
| `MIGRATION_ORDER_AND_NOTES.md` | 迁移顺序与注意事项 |
| `RLS_POLICY_MATRIX.md` | 行级安全策略矩阵 |

### `04_api/` · `[BASELINE?]`

| 文件 | 摘要 |
| --- | --- |
| `API_CONTRACT.md` | API 合同主文档 |
| `API_ROUTE_MATRIX.md` | 路由矩阵 |
| `FASTAPI_ROUTE_ORDERING.md` | FastAPI 路由顺序约定 |

### `05_services/` · `[BASELINE?]`

| 文件 | 摘要 |
| --- | --- |
| `AI_BILLING_SERVICE_SPEC.md` | AI 计费服务规范（OpenRouter） |
| `COLLECTION_SERVICE_SPEC.md` | 采集服务规范 |
| `INTELLIGENCE_SERVICE_SPEC.md` | 情报服务规范 |
| `SCORING_SERVICE_SPEC.md` | 评分服务规范 |
| `SENDING_WEBHOOK_SERVICE_SPEC.md` | 邮件发送 + Webhook 服务规范（EngageLab） |

### `06_frontend_alignment/` · `[BASELINE?]`

| 文件 | 摘要 |
| --- | --- |
| `FRONTEND_BACKEND_ALIGNMENT.md` | 前后端对齐主文档 |
| `LIVE_FRONTEND_CHECK_NOTES.md` | 实际前端核对笔记 |

### `07_implementation_plan/` · `[BASELINE?]`

| 文件 | 摘要 |
| --- | --- |
| `CODEX_CLAUDE_MASTER_PROMPT.md` | 给 Codex/Claude 的主提示词，是阅读顺序的第 1 步 |
| `DEVELOPMENT_PLAN.md` | 开发计划（P0/P1/P2 分阶段） |
| `ACCEPTANCE_TEST_PLAN.md` | 验收测试计划 |
| `TASKS.yaml` | 实施任务（机读） |

### `08_references/`

| 文件 | 摘要 |
| --- | --- |
| `OWNER_OPEN_QUESTIONS.md` | 业主未决问题 |
| `SOURCE_TRACEABILITY.md` | 各结论的来源追溯 |

### `09_self_audit/` · `[BASELINE?]`

| 文件 | 摘要 |
| --- | --- |
| `SELF_AUDIT_REPORT.md` | 蓝图自审报告（在文档优先级中位列第 2，仅次于 SOT） |

### `machine_readable/` · `[BASELINE?]`

| 文件 | 摘要 |
| --- | --- |
| `api_routes.yaml` | API 路由（机读） |
| `entities.yaml` | 实体定义（机读） |
| `implementation_tasks.yaml` | 实施任务（机读） |
| `status_machines.yaml` | 状态机定义（机读） |

### `blueprint/docs/`（蓝图内的辅助文档）

| 文件/目录 | 标签 | 摘要 |
| --- | --- | --- |
| `AGENT_PROGRESS.md` | `[CONFIRM?]` | 代理工作进度记录——是否仍准确？ |
| `ASSUMPTIONS.md` | `[DOCS]` | 已做假设清单 |
| `NEXT_SESSION_PROMPT.md` | `[CONFIRM?]` | 下一次会话承接提示——是否还在用？ |
| `OPEN_QUESTIONS.md` | `[DOCS]` | 蓝图内开放问题（与 `08_references/OWNER_OPEN_QUESTIONS.md` 不同名同概念，**待核对** `[CONFIRM?]`） |
| `plans/2026-04-22-collection-independent-deployment-plan.md` | `[DOCS]` `[CONFIRM?]` | "采集独立部署"计划——是否仍执行？ |
| `solutions/best-practices/sealos-direct-deployment-from-local-ghcr-images-2026-04-23.md` | `[DEPLOY]` `[HISTORY]` | Sealos 从本地 GHCR 镜像直接部署 |
| `solutions/best-practices/sealos-devbox-clientget-deployment-with-app-launchpad-2026-04-23.md` | `[DEPLOY]` `[HISTORY]` | Sealos Devbox + AppLaunchpad 部署 |
| `superpowers/specs/2026-04-22-collection-independent-deployment-design.md` | `[DOCS]` `[CONFIRM?]` | 采集独立部署设计 |

---

## 5. `backend/docs/` 工程文档

| 文件 | 标签 | 摘要 |
| --- | --- | --- |
| `ASSUMPTIONS.md` | `[DOCS]` | 后端实现假设 |
| `IMPLEMENTATION_NOTES.md` | `[DOCS]` `[BASELINE?]` | 实现笔记 |
| `DEPLOYMENT.md` | `[DEPLOY]` `[BASELINE?]` | 通用部署文档 |
| `LAUNCH_CHECKLIST.md` | `[DEPLOY]` `[BASELINE?]` | 上线 checklist |
| `ROLLBACK.md` | `[DEPLOY]` `[BASELINE?]` | 回滚预案 |
| `SEALOS_DEPLOYMENT.md` | `[DEPLOY]` `[BASELINE?]` | Sealos 部署文档（9KB） |
| `legacy_migration_report.json` | `[CONFIRM?]` | 历史迁移报告 JSON——**未读取**，可能含数据样本 |

---

## 6. 写代码冲突时的优先级（来自 `CODEX_START_HERE.md`）

```
00_SOURCE_OF_TRUTH_DECISIONS.md
> 09_self_audit/SELF_AUDIT_REPORT.md
> 01_final_repaired_docs/*
> 02_architecture/*
> 03_database/schema.sql + RLS_POLICY_MATRIX.md
> 04_api/API_CONTRACT.md + FASTAPI_ROUTE_ORDERING.md
> 05_services/*
> 06_frontend_alignment/*
> 07_implementation_plan/*
> 00_original_sources/*
```

> ⚠️ **关键冲突警示**：`docs/spec-*` 与 `docs/plan-phase1-*` 系列是 **2026-04-30 之后**的活跃工作产物（外贸通直采 / Phase 1 / Phase 1.5），可能已经超越或修订了 blueprint 的 `12_COLLECTION_SERVICE_REPAIRED.md` / `05_services/COLLECTION_SERVICE_SPEC.md`。**两套文档的权威关系待用户确认**——见 [`04-open-questions.md`](04-open-questions.md) #2。

---

## 7. 待办（语义层增量）

- [ ] 递归 `docs/research/` 下 `tendata-field-mapping*` 与 captures 文件
- [ ] 给 `docs/meetings/` 22 份按时间倒序补摘要（重要性低，按需）
- [ ] 核对 blueprint 内 `docs/OPEN_QUESTIONS.md` 与 `08_references/OWNER_OPEN_QUESTIONS.md` 是否重复
- [ ] 给 `docs/archive/` 标"为何归档"
- [ ] 核对 `docs/spec-*`（活跃）与 blueprint `12_COLLECTION_SERVICE_REPAIRED.md` 的 supersession 关系
