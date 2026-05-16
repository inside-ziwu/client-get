# Proposal · v3-contact-classification

> **Wave 2 附属（v3-email-delivery 引用 classify 函数）**
> 关联：[`_control/v3/02-current-implementation-gap-audit.md`](../../../_control/v3/02-current-implementation-gap-audit.md) C3

## Why

V3 业务规则 §5.4 — 联系人职位分类规则（D-037）：
- **平台运营统一配置**（admin/contact-classification），所有租户继承使用，租户无配置 UI
- 4 层模型：等级（admin 可增删，每级带"是否投递"开关）→ 类别（如"老板/创始人"，给 UI 分组+报表用）→ 关键词（如 owner/founder/CEO/...）
- 匹配规则：联系人 `position` 切词后做集合交集；命中多关键词 → 取最高等级；未命中 → 不投递
- 例：A 级（投递）：老板/创始人/高管 / 采购决策；B 级（投递）：技术工程；X 级（不投递）：销售/HR/财务/法务

当前阻塞：
- **整段从 tenant 端搬到 admin 端** — tenant/Settings/contact-rules **确实存在**（router.tsx + Settings/ContactRules + Onboarding StepContactRules + shared-api queryKeys + 后端 settings.py），需完整删除
- **3 张表 + 1 视图全部 from-scratch**（按决策池 M.1 方案 A，2026-05-06 用户拍板）
- **classify(position) 函数未实现** — UC-08 联系人优先级规则需基于此
- **业务方初始关键词清单未导入**

业务后果：邮件计划新建无法自动取联系人 → 无法正确投递 → 影响 v3-email-delivery 主链路 Slice 3.4。

## What Changes

### 引入

#### 数据模型（3 张表 + 1 视图，方案 A，决策池 M.1 真源）

- **`position_classification_levels`** — 等级（A/B/X 等），字段：id / name / display_name / sort_order / is_sendable / created_at / updated_at
- **`position_classification_categories`** — 类别（老板/创始人 / 技术工程 / 销售/HR），字段：id / level_id / name / display_name / sort_order / created_at
- **`position_classification_keywords`** — 关键词（owner / founder / CEO / engineer ...），字段：id / category_id / keyword（小写）/ created_at
- **`v_tenant_contact_classified`（视图）** — 运行时计算每联系人匹配的等级/类别，字段：sys_contact_id / level_id / category_id / is_sendable

> **不做 compiled 缓存表**（codex M-04 / B-03 用户拍板方案 A）：V3 数据量（5 租户 × 几千联系人）视图实时计算足够；admin 改规则后视图自动反映，无需重建/版本号/swap 复杂度。

#### admin/contact-classification 页面（V3 新增模块）

按 mockup `admin-contact-classification.html` 实现：
- 等级管理：增删改 + is_sendable 开关
- 类别管理：归属等级 + 增删改
- 关键词管理：归属类别 + 增删改
- 整体预览：层级树形展示

#### classify(position) 函数

- 输入：联系人 position 字符串
- 处理：切词（中英文混合 + 标点处理） → 与 keywords 表（已小写）做集合交集 → 取最高等级
- 输出：等级 + is_sendable
- 实现：直接查 `v_tenant_contact_classified` 视图（V3 数据量足够；不做 compiled 表预编译）

#### 业务方初始关键词清单导入

- A 级（投递）：老板 / 创始人 / 总裁 / CEO / Owner / Founder / President + 高管 + 采购决策
- B 级（投递）：技术工程 / Engineer / Technical / R&D
- X 级（不投递）：销售 / Sales / HR / Finance / Legal / Marketing

#### UC-08 / UC-25 邮件计划集成

- 邮件计划新建时自动调 classify(position)
- 取所有 is_sendable=true 的联系人（不限每公司数量）
- 多步骤序列：第 N 轮发未发过的其他联系人

### 修改

- tenant/SendPlans/Create UC-25 调 classify 取联系人

### 移除

- tenant/Settings/contact-rules 模块（如有）— 整段搬到 admin（D-037 / D-024 单端原则）

## Non-Goals

- ❌ 不实现 sending worker 真发（→ v3-email-delivery）
- ❌ 不实现客户库私有操作（→ v3-tenant-companies）
- ❌ 不修改现有 tenant_contacts 表结构（仅新增 position_classification_* 3 表 + 1 视图）
- ❌ 不做"主联系人"概念（V3 N-05 / D-033）

## Impact

| 维度 | 影响 |
|---|---|
| **破坏兼容** | 否 — 新建独立模块；UC-08 调用方式变化但接口兼容 |
| **DB 改动** | 是 — 新增 3 张表 + 1 视图（方案 A，B-03 拍板）|
| **Worker** | 否 — classify 是同步函数 |
| **前端** | 中 — admin 新页面 + tenant Settings 删模块 |
| **依赖** | `2026-05-09-v3-data-foundation` 已完成并归档（worker base + alembic）|
| **下游引用** | v3-email-delivery 的 T-ED-41 调 classify 函数 |

## 关联

- **能力域**：C3 联系人职位分类
- **覆盖 Slice**：附属（v3-email-delivery Slice 3.4 引用）
- **覆盖验收 ID**：贡献 Slice 5 E2E
- **决策追溯**：D-037（联系人分类整段从 tenant 搬到 admin）/ D-024（单端原则）/ UC-08（联系人优先级规则）
