---
date: 2026-06-13
topic: dual-rating-system-unification
---

# 双评级体系统一与系统评分引擎

## Summary

将现有的 AI 大模型评级（X/A/B）与评分模板评级（S/A/B/C/D）统一命名，在 admin 和 tenant 端并行展示为「大模型评级/大模型评分」与「系统评级/系统评分」四列。同时构建基于 `scoring_templates` 维度规则的自动评分引擎，增强两端评分模板管理能力，实现平台模板到租户的自动同步。

---

## Problem Frame

系统中存在两套独立的评级体系，命名混乱且功能不完整：

大模型评级（X/A/B）存储在 `waimaotong_clean_companies.grade/score`，由 AI 模型在数据清洗阶段打分，评估公司与 PCB 行业的相关性。生产库 10,747 家公司已有评级，其中 X 级 7,154 家（低相关）、B 级 2,108 家、A 级 1,484 家。

评分模板体系（S/A/B/C/D）基于 `scoring_templates` 定义的多维度规则评分。平台模板和租户模板结构已就绪，但评分引擎从未实际运行——`company_scores` 表和 `scoring_jobs` 表均为空。

两套体系在前端列表中共用一个「评级」列名，前端 `GRADE_COLORS` 在 admin 和 tenant 各页面各自定义且颜色不一致。tenant 端的评分模板管理极简，只能修改第一个维度的权重。

---

## Key Decisions

**命名规范。** 现有 X/A/B 体系统一称为「大模型评级/大模型评分」，新 S/A/B/C/D 体系称为「系统评级/系统评分」。

**评分引擎只支持 rule 类型维度。** 生产库存在一个 LLM 类型维度（刘辉租户的「产品匹配度」），但该模板是历史遗留（创建后从未编辑或产生过评分），将替换为平台模板副本。LLM 维度评分不在本次范围。

**评分维度按租户隔离。** 每个租户使用自己的 `scoring_templates` 评分，admin 端使用 `platform_scoring_templates` 评分。同一公司在不同租户下可能获得不同系统评级。

**Tenant 端编辑边界。** 租户可调整所有维度的权重和等级阈值，但不能增删维度或修改条件规则。维度结构由平台模板定义并自动同步。

---

## Requirements

**命名与展示统一**

R1. admin 和 tenant 端所有公司列表页面中，现有「评级」列重命名为「大模型评级」，现有「评分」列重命名为「大模型评分」。

R2. 新增「系统评级」列（显示 S/A/B/C/D）和「系统评分」列（显示总分数值），与大模型评级/评分并排展示。

R3. 涉及页面：admin 客户数据页（`frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx`）、tenant 公司列表页（`frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`）、tenant 精选客户页（`frontend/apps/tenant/src/app/(dashboard)/curated-customers/page.tsx`）、tenant 添加公司弹窗（`frontend/apps/tenant/src/app/(dashboard)/curated-customers/add-company-modal.tsx`）。

R4. 前端评级颜色定义收拢到 `frontend/packages/shared-ui/src/RatingTag.tsx`，各页面不再各自定义 `GRADE_COLORS`。大模型评级（X/A/B）和系统评级（S/A/B/C/D）使用不同的色系以便区分。

**评分计算引擎**

R5. 构建规则型评分引擎：读取评分模板的维度定义（`dimensions`），逐维度匹配公司数据，计算各维度得分，加权求和得到总分，按 `grade_thresholds` 映射为 S/A/B/C/D 等级。

R6. 评分引擎只处理 `type=rule` 的维度，遇到 `type=llm` 维度跳过计分（该维度得分为 0）。

R7. 评分结果写入 `company_scores` 表，包含 `tenant_id`、`tenant_company_id`、`template_id`、`template_version_id`、`total_score`、`grade`、`dimension_scores`。

R8. 公司入库（写入 `tenant_companies`）时自动触发评分计算。

R9. admin 端使用 `platform_scoring_templates` 对 `waimaotong_clean_companies` 评分，评分结果独立于租户维度存储。

R10. 部署时对存量 27,011 家 `tenant_companies` 一次性回填评分（迁移脚本或一次性后台任务）。

**评分模板管理增强 — Admin 端**

R11. 修复 Admin 端 DimensionEditor，使其能正确读取和保存完整的条件类型结构（`condition`、`value`、`min`、`max` 等字段），而非只存 `{label, score}` 导致编辑后丢失匹配规则。

R12. Admin 端评分模板页面的现有 CRUD 功能保持不变（列表、新增、编辑、删除、预览、版本记录）。

**评分模板管理增强 — Tenant 端**

R13. Tenant 端评分配置页面增强：可编辑所有维度的权重（现在只能编辑第一个），可编辑等级阈值（S/A/B/C/D 的分数线）。

R14. Tenant 端不能增删维度、不能修改维度的条件规则（条件类型、匹配值等）。维度结构从平台模板继承。

**平台模板 → 租户同步**

R15. 平台模板更新时，自动将维度结构（新增/删除/修改的维度及其条件规则）同步到所有关联租户的 `scoring_templates`，保留租户已自定义的权重和阈值。

R16. 同步后，租户的评分模板版本号递增，并写入 `scoring_template_versions` 记录。

**数据清理**

R17. 将刘辉租户（`019e631f-5c2b-7661-88de-c050193f68b2`）的「电路板 默认评分模板」替换为从当前平台模板复制的版本。

---

## Key Flows

F1. 公司入库评分
- **Trigger:** 新公司写入 `tenant_companies`（手动添加或采集入库）。
- **Steps:** 查询该租户的 active `scoring_templates` → 逐维度匹配公司数据 → 加权求和 → 按阈值映射等级 → 写入 `company_scores`。
- **Covers R5, R6, R7, R8.**

F2. 平台模板同步
- **Trigger:** Admin 更新 `platform_scoring_templates` 的维度结构。
- **Steps:** 查找所有 `source_platform_template_id` 指向该模板的租户模板 → 同步维度结构（保留租户权重/阈值）→ 递增版本号 → 写入版本记录。
- **Covers R15, R16.**

F3. 存量回填
- **Trigger:** 部署迁移脚本执行。
- **Steps:** 遍历所有租户 → 对每个租户的所有 `tenant_companies` 执行评分 → 批量写入 `company_scores`。Admin 端对 `waimaotong_clean_companies` 使用平台模板评分。
- **Covers R9, R10.**

---

## Scope Boundaries

- LLM 类型维度的评分计算不在本次范围，遇到时跳过计分。
- 不修改大模型评级（X/A/B）的计算逻辑，只做前端命名统一。
- 不新增筛选器（系统评级筛选可作为后续迭代）。
- 不涉及评分结果对业务流程的影响（如按评级自动分配发送优先级），只做展示。

---

## Dependencies / Assumptions

- `company_scores` 表结构已存在且字段满足需求（`tenant_id`、`tenant_company_id`、`template_id`、`total_score`、`grade`、`dimension_scores` 等）。
- 评分模板的规则型条件类型有限且已知（`factory_type_in`、`employee_num_range`、`trade_amount_3y_usd_range`、`trade_count_range`、`has_contact`、`source_table_contains`、`has_china_pcb_supplier`、`default`）。
- 存量回填 27,011 家公司的评分可在部署窗口内完成（纯规则型计算，无外部 API 调用）。

---

## Outstanding Questions

**Resolve Before Planning**

- Admin 端对 `waimaotong_clean_companies` 的评分结果存储在哪里？`company_scores` 表设计为 `tenant_company_id` 外键关联 `tenant_companies`，而 admin 数据不属于任何租户。需要决定是在 `company_scores` 中用特殊 `tenant_id` 标记平台级评分，还是另建存储。
- 平台模板同步时，如果租户已自定义某个维度的权重为 0（等于禁用该维度），同步后是否保留该自定义？

---

## Sources / Research

- `waimaotong_clean_companies` 的 grade/score 分布：X=7154（avg 3.5 分）、B=2108（avg 56.8 分）、A=1484（avg 87.7 分）。
- 平台模板 `PCB 行业默认模板` 有 7 个规则型维度（工厂性质、工厂规模、进出口额、进出口次数、联系人、数据来源、PCB 供应商），阈值 `{S:90, A:70, B:40, C:10, D:0}`。
- 租户模板与平台模板通过 `source_platform_template_id` 关联，租户创建时由 `_copy_platform_scoring_template` 自动复制。
- `company_scores` 和 `scoring_jobs` 表生产库均为空，评分引擎属于全新构建。
- Tenant 端现有评分配置页面（`frontend/apps/tenant/src/app/(dashboard)/settings/scoring/page.tsx`）只能修改第一个维度的权重，mutation 逻辑硬编码 `index === 0`。
