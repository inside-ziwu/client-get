# Proposal · v3-tenant-companies

> **Wave 2 附属（与主链并行）**
> Slice 依赖（codex H-06 修订）：**不阻塞 Slice 3 邮件投递开发**；**阻塞 Slice 5 全 V3 E2E 验收**（D-038 10 项筛选 + D-039 评分 + D-022 私有操作均需在 PM Acceptance 前完成）
> 关联：[`_control/v3/02-current-implementation-gap-audit.md`](../../../_control/v3/02-current-implementation-gap-audit.md) C4 + C5 + C6

## Why

V3 客户库是租户日常使用频率最高的模块。当前 3 块同时缺失：

1. **C4 私有操作（UC-22 备注 + UC-23 标签 + D-020 群组管理）** — 原型已齐（`tenant-companies.html` commit `7ceb218`）；tenant/Companies Drawer 当前只展示不能编辑。UC-22/23/D-020 后端已 PASS，本 change 负责前端编辑态。UC-21 调分已彻底移出本 change。
2. **C5 客户库 10 项筛选（D-038）** — 客户列表 + 精选列表共用筛选组件，后端 filter API 不支持 9 个新维度，前端组件未建。
3. **C6 默认评分模板（D-039 + D-039-X.1）** — 当前 admin/ScoringTemplates 非按行业版；tenant Settings/Scoring 还能配规则（应改为只调权重）。需重构为 admin 配模板 / 租户调权重的两层模型。

业务后果：
- 客户库无法过滤 → 租户面对几千行数据无法定位高价值客户
- 评分体系混乱 → `model_score` / `score` 分数摘要与模板权重不能落地
- 私有状态不能改 → 租户日常需求堵死

## What Changes

### 已归档依赖

旧 tenant company 字段契约清理已移至并归档为 `2026-05-10-tenant-company-v3-contract-cleanup`。本 change 不再重复承载 `grade` / `total_score` / `notes` / `deleted_at` / `is_precise_customer` / `score_adjustment*` 的收口任务，后续只聚焦 C4 私有操作、C5 10 项筛选、C6 默认评分模板。

### 引入

#### C4 · 私有操作（UC-22 备注 + UC-23 标签 + D-020 群组）

- **tenant/Companies Drawer 私有备注 textarea**（按 mockup `noteEdit`）
- **tenant/Companies Drawer 私有标签 add/remove**（按 mockup `tagsEdit`）
- **批量加入群组**（按 mockup `showBatchAddGroup` + 加入群组 Modal）
  - 单条入口（行内按钮）+ 批量入口（顶部 batch bar）
- **enterEditMode / exitEditMode 切换** — Drawer 默认显示态，编辑按钮进入编辑态

#### C5 · 客户库 10 项筛选（D-038）

- **clean_companies +11 字段（D-038 9 + D-039 2）（已在归档 change `2026-05-09-v3-data-foundation` 完成）** — 国家/行业细分/成立时间/注册资金/产品标签/规模/数据来源/进出口额/次数/联系人数量
- **product_tags AI 回填（已在归档 change `2026-05-09-v3-data-foundation` 完成）**
- **后端 filter API** — 支持 10 维多选 OR + 档位筛
  - 多选 OR：国家 / 行业细分 / 产品标签 / 数据来源
  - 档位筛：成立时间 / 注册资金 / 公司规模 / 进出口额 / 进出口次数 / 联系人数量
  - 联系人数量档位：`0 / 1-3 / 4-10 / 11-30 / >30`
- **前端筛选组件** — 共用 Companies + CuratedCustomers（按 mockup `tenant-companies.html` + `tenant-curated-customers.html`）

#### C6 · 默认评分模板（D-039 + D-039-X.1）

- **scoring_templates 表加 industry 字段**（PCB 行业默认模板）
- **tenant_scoring_weights 表** — 租户级权重覆盖
- **admin/ScoringTemplates 按行业 UI** — PCB 7 维：工厂性质 / 工厂规模 / 进出口额 / 进出口次数 / 联系人 / 数据来源 / PCB 供应商
- **tenant/Settings/Scoring 改为"仅调权重"** — 移除规则配置，仅展示 + 调权重
- **scoring worker 输出分数摘要** — 写入 `model_score` 与 `score`
- **scoring worker 兜底** — 档位外 / 缺失 = 0 分

### 修改

- tenant/Companies/index.tsx 全面重写 Drawer + 顶部筛选栏
- tenant/CuratedCustomers/index.tsx 共用 10 项筛选组件
- tenant/Settings/Scoring 从"配规则 + 调权重"改为"仅调权重"
- admin/ScoringTemplates 加按行业模板管理
- 后端 tenant ops / scoring 查询补齐 C5/C6 所需能力

### 移除

- tenant/Settings/Scoring 规则配置 UI（搬走）

## Non-Goals

- ❌ 不重复实现已归档的 tenant company V3 contract cleanup（`2026-05-10-tenant-company-v3-contract-cleanup`）
- ❌ UC-21 调分彻底移出本 change；本 change 不实现人工调分 API 或调分 UI
- ❌ 不实现 cleanup_service 字段映射（已在 v3-data-foundation 完成 C5-G2）
- ❌ 不实现 product_tags AI 回填（已在 v3-data-foundation 完成）
- ❌ 不实现 D-008 数据库重构（已在 v3-data-foundation 完成）
- ❌ 不实现联系人分类（→ v3-contact-classification）
- ❌ 不做完整 UC-30 公司级中断（V3 N-03）
- ❌ 不做"主联系人"概念（V3 N-05 / D-033）
- ❌ 不做完整 Tenant Dashboard / 跨计划趋势（V3 N-04 / D-032）

## Impact

| 维度 | 影响 |
|---|---|
| **DB 改动** | 小 — scoring_templates / tenant_scoring_weights 调整；本次不恢复旧 tenant 字段 |
| **Worker** | 小 — scoring worker 输出 `model_score` / `score` + 兜底逻辑 |
| **前端** | 大 — 4 个核心页面（Companies / CuratedCustomers / Settings/Scoring / admin/ScoringTemplates）改动 |
| **依赖** | `2026-05-09-v3-data-foundation` 已完成并归档；`2026-05-10-tenant-company-v3-contract-cleanup` 已完成并归档 |

## 关联

- **能力域**：C4 私有操作 + C5 10 项筛选 + C6 评分模板
- **覆盖 Slice**：附属（无主 Slice），并行 Slice 3 期间完成；Slice 5 验收
- **覆盖验收 ID**：V3-UI-001（部分）+ Slice 5 E2E
- **决策追溯**：D-020（精选 = 群组）/ D-022（私有操作 V3 必做）/ D-038（10 项筛选）/ D-039（按行业评分模板）/ D-039-X.1（factory_type LLM 推断）
