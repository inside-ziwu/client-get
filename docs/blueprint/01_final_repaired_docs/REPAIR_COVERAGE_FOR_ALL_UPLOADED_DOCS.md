# 全部上传文档修复覆盖说明

本文件说明每个原始文档在本交付包中的修复方式。原始文档保留在 `00_original_sources/`；实现时不要直接从原始文档中拼口径，而应使用本包修复后的最终文档。

| 原文档 | 原用途 | 修复后使用方式 |
|---|---|---|
| `business-flows-v2.html` | 原始业务流程 Spec | 已吸收到 `07_REQUIREMENTS_SPEC_REPAIRED.md`；其中“公司名称唯一键”“固定天数预热”“Phase 1 自助充值”等与后续确认冲突的内容已修正。 |
| `00_SYSTEM_OVERVIEW.md` | 旧系统总览 | 作为迁移参考；新系统总览见 `02_architecture/BACKEND_ARCHITECTURE.md`。 |
| `01_DATA_MODEL.md` | 旧 12 表数据模型 | 作为迁移输入；新 Schema 见 `03_database/schema.sql`。 |
| `02_API_REFERENCE.md` | 旧 API 参考 | 旧 API 不直接复用；新 API 见 `04_api/API_CONTRACT.md`。 |
| `03_WORKFLOW_ENGINE.md` | 旧 Prefect Flow | 已拆分为采集/评分/发送/AI 服务规格，见 `05_services/*`。 |
| `04_FRONTEND_MAP.md` | 旧单前端页面地图 | 新双前端对齐见 `06_frontend_alignment/FRONTEND_BACKEND_ALIGNMENT.md`。 |
| `05_EXTERNAL_INTEGRATIONS.md` | 外部集成依赖 | 已吸收到采集、AI、发送服务规格。 |
| `06_PRODUCTIZATION_GAP.md` | 产品化差距 | 已转成 `07_implementation_plan/DEVELOPMENT_PLAN.md` 的 P0/P1/P2 计划。 |
| `07_REQUIREMENTS_SPEC.md` | 产品化需求 | 已修复为 `07_REQUIREMENTS_SPEC_REPAIRED.md`。 |
| `08_UI_SPEC.md` | UI 规格 | 已修复为 `08_UI_SPEC_REPAIRED_BACKEND_ALIGNMENT.md` 与前端对齐矩阵。 |
| `09_DATABASE_DESIGN.md` | 数据库设计 | 已修复为 `09_DATABASE_DESIGN_REPAIRED.md` 与 `schema.sql`。 |
| `10_API_DESIGN.md` | API 设计 | 已修复为 `10_API_DESIGN_REPAIRED.md` 与 `API_CONTRACT.md`。 |
| `11_FRONTEND_ARCHITECTURE.md` | 前端架构 | 已修复为 `11_FRONTEND_ARCHITECTURE_REPAIRED.md`。 |
| `12_COLLECTION_SERVICE.md` | 采集服务 | 已修复为 `12_COLLECTION_SERVICE_REPAIRED.md`。 |
| `13_AI_INTEGRATION.md` | AI 集成 | 已修复为 `13_AI_INTEGRATION_REPAIRED.md`。 |
| `14_DATA_MIGRATION.md` | 数据迁移 | 已修复为 `14_DATA_MIGRATION_REPAIRED.md`。 |

## 实现真源

从 0 写代码时的唯一真源是：

1. `00_SOURCE_OF_TRUTH_DECISIONS.md`
2. `01_final_repaired_docs/*`
3. `02_architecture/*`
4. `03_database/*`
5. `04_api/*`
6. `05_services/*`
7. `06_frontend_alignment/*`
8. `07_implementation_plan/*`
