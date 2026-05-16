# V3 模块功能矩阵 — DRAFT 颗粒度样例

> **状态**：🟡 DRAFT — 仅含骨架 + admin/Tenants 1 个示例模块（拆 3 子模块）。**用户审颗粒度后再铺开**。
>
> **目的**：单一对照表"后台模块 × 子模块（页面 / Modal / Drawer）× 功能 × 字段 × API × 权限 × 决策号 × V3 状态"，作为 V3 Slice 0 模块清点的真源。
>
> **来源融合**：
> - [`00-v3-business-goals.md`](00-v3-business-goals.md) §5 业务规则（**单一真源**：业务字段要求）
> - [`00-v3-target-spec.md`](00-v3-target-spec.md) §0.A 33 项决策（功能/字段/页面级要求）
> - [`03-r1-readiness-matrix.md`](03-r1-readiness-matrix.md)（33 UC × 状态）
> - 实际前端 `frontend/apps/{admin,tenant}/src/pages/`
> - 实际 `_control/inputs/database/schema.sql`（54 张表字段）
>
> **生成**：2026-05-06

---

## 0. 状态枚举

| 状态 | 含义 |
| --- | --- |
| **PASS** | 功能完整可用 |
| **PARTIAL** | 主路径在，缺关键分支 / 配置入口 / 字段 |
| **MISSING** | 完全没找到 |
| **NEW-IN-V3** | V3 新增模块（实际 pages 目录还没有） |
| **WORKER-NOT-DEPLOYED** | 代码已实现但 worker 未部署 |

## 1. 模块总览

> 由实际前端 pages 目录扫描得出。

### 1.1 Admin 端 11 个现有模块 + 1 个 V3 新增

| # | 模块 | pages 目录 | 主要决策 |
| --- | --- | --- | --- |
| A-01 | **Tenants** | `admin/Tenants/` | D-002 / D-013 / D-024 / D-028 / D-030 / D-031 |
| A-02 | **WarmupRules** | `admin/WarmupRules/` | D-013 |
| A-03 | **DataSources** | `admin/DataSources/` | D-016 |
| A-04 | **CollectionDashboard** | `admin/CollectionDashboard/` | UC-15 |
| A-05 | **CollectionTasks** | `admin/CollectionTasks/` | UC-10 |
| A-06 | **CollectionArchive** | `admin/CollectionArchive/` | — |
| A-07 | **IntelligenceSources** | `admin/IntelligenceSources/` | — |
| A-08 | **EmailTemplates** | `admin/EmailTemplates/` | — |
| A-09 | **ScoringTemplates** | `admin/ScoringTemplates/` | D-039 / D-039-X.1 |
| A-10 | **AIConfig** | `admin/AIConfig/` | — |
| A-11 | **CleanupHealth** | `admin/CleanupHealth/` | D-008-B |
| A-12 | **ContactClassification** 🆕 | （V3 新增） | D-037 |

### 1.2 Tenant 端 9 个现有模块

| # | 模块 | pages 目录 | 主要决策 |
| --- | --- | --- | --- |
| T-01 | **Onboarding** | `tenant/Onboarding/` | UC-03 |
| T-02 | **Dashboard** | `tenant/Dashboard/` | D-029 / D-032（极简版） |
| T-03 | **Companies** | `tenant/Companies/` | D-020 / D-022 / D-038 / D-039 |
| T-04 | **CuratedCustomers** | `tenant/CuratedCustomers/` | D-020 / D-038 |
| T-05 | **Intelligence**（关键词） | `tenant/Intelligence/` | D-009 / UC-06 |
| T-06 | **SendPlans** | `tenant/SendPlans/` | D-033 / D-036 |
| T-07 | **EmailMonitor** | `tenant/EmailMonitor/` | UC-28 / D-034（无回复） |
| T-08 | **Templates** | `tenant/Templates/` | — |
| T-09 | **Settings** | `tenant/Settings/` | D-004 / UC-04 / 删 UC-08 联系人规则（D-037 搬走） |

---

## 2. 填写规范（每模块拆子模块 → 每子模块 5 张表）

**模块（Module）**：1 个 pages 目录 = 1 个模块。
**子模块（Sub-Module）**：1 个独立交互单元 = 1 个子模块。常见类型：
- **List**：表格视图
- **Create**：创建表单（通常 Modal）
- **Detail**：详情页 / Drawer（内部可含多 Tab + 多子 Modal）
- **Edit / Action Modal**：单独的弹窗操作

每个**子模块**产出 **5 张表**：

1. **功能矩阵**：功能 ID / 功能 / 交互形式 / V3 状态 / 决策号 / 备注 — **只描述行为，不放字段**
2. **字段对照**（按视图/Modal 拆）：UI 字段 / 必填 / 业务目标 / 决策号 / DB 字段 / 一致性 — **只描述数据**
3. **API 端点对照**：路径 / 方法 / 用途 / 关联功能 / V3 状态 / 备注
4. **权限矩阵**：功能 × 角色（平台 admin / viewer + 租户 admin / operator / viewer）
5. **V3 缺口与待办**：缺口 # / 描述 / 端 / 工作量档（S/M/L）/ 关联决策

**工作量档**（不出具体天数 — 天数估算属于 Delivery Plan 阶段）：
- **S** = 小（一两小时内）
- **M** = 中（半天到两天）
- **L** = 大（超过两天）

**字段一致性枚举**：✅ 对 / 🟡 缺（V3 要加） / 🔴 删（V3 要去） / ⚠️ 改（默认/锁定/约束修改） / ❓ 待核（schema 名待确认）

---

## 3. Admin 端模块矩阵

### 3.1 A-01 admin/Tenants（**示例完整版** — 颗粒度样例，请审）

> **职责**：平台运营管理租户全生命周期。
>
> **实际代码**：[`admin/src/pages/Tenants/index.tsx`](frontend/apps/admin/src/pages/Tenants/index.tsx)（655 行）
>
> **关联决策**：D-002 / D-013 / D-024 / D-028 / D-030 / D-031 / D-040
>
> **拆分** 3 个子模块：
> - **3.1.1 List** — 顶部租户列表
> - **3.1.2 Create** — "新建租户"按钮 → Modal
> - **3.1.3 Detail** — 行"查看"链接 → 右侧 Drawer（内部 4 Tab + 多子 Modal）

---

### 3.1.1 子模块：List 租户列表

> **入口**：进入 `/admin/tenants` 页面顶部。

#### 功能矩阵

| 功能 ID | 功能 | 交互形式 | V3 状态 | 决策号 | 备注 |
| --- | --- | --- | --- | --- | --- |
| LIST-F01 | 表格渲染 | 表格组件 | PASS | — | — |
| LIST-F02 | 顶部搜索 | 搜索框 + 回车 | PASS | — | 按名称/Slug 模糊匹配 |
| LIST-F03 | 状态过滤 | 下拉单选 | PASS | — | active / suspended / archived |
| LIST-F04 | 分页 | 表格分页栏 | PASS | — | 默认 20 / 页 |
| LIST-F05 | 行操作（查看 → Detail Drawer） | 行链接 | PASS | — | 跳转到 3.1.3 子模块 |

#### 字段对照（表格列）

| 列 | 业务目标 | DB 字段 | 一致性 |
| --- | --- | --- | :---: |
| 租户名称 | §2 | `tenants.name` | ✅ |
| Slug | 隐式 | `tenants.slug` | ✅ |
| 行业 | §6 N-13 | `tenants.industry` | ✅ |
| 状态徽标 | — | `tenants.status` | ✅ |
| 创建时间 | — | `tenants.created_at` | ✅ |
| 操作（查看链接）| — | — | ✅ |

#### API 端点

| 路径 | 方法 | 用途 | 关联功能 | V3 状态 |
| --- | --- | --- | --- | --- |
| `/api/admin/tenants` | GET | 列表（含 search / status / pagination 参数）| LIST-F01~F05 | PASS |

#### 权限矩阵

| 功能 | 平台 admin | 平台 viewer | 租户 admin | 租户 operator | 租户 viewer |
| --- | :---: | :---: | :---: | :---: | :---: |
| LIST-F01~F05 | ✅ | 👁️ 只读 | ❌ | ❌ | ❌ |

#### V3 缺口

无（PASS）。

---

### 3.1.2 子模块：Create 创建租户 Modal

> **入口**：列表页顶部"新建租户"按钮 → 弹出 Modal → 提交 → 关 Modal + 列表刷新。
> **代码**：[`Tenants/index.tsx:538-569`](frontend/apps/admin/src/pages/Tenants/index.tsx)

#### 功能矩阵

| 功能 ID | 功能 | 交互形式 | V3 状态 | 决策号 | 备注 |
| --- | --- | --- | --- | --- | --- |
| CREATE-F01 | 打开 Modal | "新建租户"按钮 | PASS | — | — |
| CREATE-F02 | 字段校验 | antd Form rules | PASS | — | name / industry / admin_email / admin_name / admin_password 必填 |
| CREATE-F03 | 提交创建 | API POST | **PARTIAL** | D-031 | V3 改：事务里同步建 `users` + `domain_warmup_status` |
| CREATE-F04 | 关闭 Modal + 列表刷新 | 提交成功后 | PASS | — | — |

#### 字段对照（表单字段）

| UI 字段 | 必填 | 业务目标 | 决策号 | DB 字段（`tenants`） | DB 字段（关联表） | 一致性 |
| --- | :---: | --- | --- | --- | --- | :---: |
| 租户名称 | ✓ | §2 | — | `name` | — | ✅ |
| 行业 | ✓ | §6 N-13 | D-040 | `industry` | — | ⚠️ V3 UI 默认锁 PCB |
| 联系人 | — | — | — | `contact_name` | — | ✅ |
| 联系电话 | — | — | — | `contact_phone` | — | ✅ |
| 管理员邮箱 | ✓ | §3 | D-030 | — | `users.email` | ✅ |
| 管理员姓名 | ✓ | — | — | — | `users.name` | ✅ |
| 管理员密码 | ✓ | — | D-030 | — | `users.password_hash` | ✅ |
| **发件域名** 🆕 | ✓ | §5.4 | D-002 / D-031 | — | `domain_warmup_status.domain` | 🟡 V3 加 |
| **起始预热档位** 🆕 | ✓ | §5.4 | D-013 / D-031 | — | `domain_warmup_status.warmup_level` (1-6) | 🟡 V3 加 |

> **澄清 D-030**：现表单原本就没邀请邮件 + 临时密码字段；V3 仅明确不新增此流程。

#### API 端点

| 路径 | 方法 | 用途 | 关联功能 | V3 状态 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `/api/admin/tenants` | POST | 创建租户 | CREATE-F03 | **PARTIAL** | V3 改：body 加 `domain` + `warmup_level`；事务里同步建 `users` + `domain_warmup_status` |

> 路径仅为示例 — V3 实施前需查 backend 实际路由。

#### 权限矩阵

| 功能 | 平台 admin | 平台 viewer | 租户 admin | 租户 operator | 租户 viewer |
| --- | :---: | :---: | :---: | :---: | :---: |
| CREATE-F01~F04 | ✅ | ❌ | ❌ | ❌ | ❌ |

#### V3 缺口

| # | 缺口 | 端 | 工作量 | 关联 |
| --- | --- | --- | :---: | --- |
| CREATE-G1 | 表单加"发件域名 + 起始预热档位"字段 | 前端 | S | D-031 |
| CREATE-G2 | 创建 API 改：事务里同步建 `domain_warmup_status` | 后端 | M | D-031 |
| CREATE-G3 | 行业字段默认锁 PCB | 前端 | S | D-040 |

---

### 3.1.3 子模块：Detail 详情 Drawer

> **入口**：列表行"查看"链接 → 右侧 Drawer 滑出。
> **结构**：Drawer 内含**顶部状态切换按钮区** + **4 个 Tab** + **多个子 Modal**。
> **代码**：[`Tenants/index.tsx:429-536`](frontend/apps/admin/src/pages/Tenants/index.tsx)

#### 功能矩阵（按 Tab 分组）

| 功能 ID | 位置 | 功能 | 交互形式 | V3 状态 | 决策号 | 备注 |
| --- | --- | --- | --- | --- | --- | --- |
| DET-F01 | 顶部 | 状态切换 | 操作按钮 | PASS | — | active / suspended / archived |
| DET-F02 | Tab A 基本信息 | 显示租户基本字段 | Descriptions | PASS | — | — |
| DET-F03 | Tab B 域名管理 | 域名列表 | 表格 | PASS | — | — |
| DET-F04 | Tab B | 添加域名 | 子 Modal | **PARTIAL** | D-002 / D-024 | 现状仅 1 字段；V3 改后端调 EngageLab |
| DET-F05 | Tab B | 触发域名验证 | 按钮 + 状态轮询 | **MISSING** | D-002 / D-024 | V3 新加 |
| DET-F06 | Tab B | 一键复制 DNS 记录 | clipboard 按钮 | **MISSING** | D-028 | V3 新加 |
| DET-F07 | Tab B | 调整预热档位 | 表单 | PASS | D-013 | — |
| DET-F08 | Tab C 团队成员 | 用户列表 | 表格 | PASS | UC-09 | — |
| DET-F09 | Tab C | 添加用户 | 子 Modal | PASS | UC-09 | — |
| DET-F10 | Tab C | 重置用户密码 | 子 Modal | PASS | — | — |
| DET-F11 | Tab D AI 配置 | 显示 OpenRouter 配置 | Descriptions | PASS | UC-04 | — |
| DET-F12 | Tab D | 配置 OpenRouter | 子 Modal | PASS | UC-04 | — |

#### 字段对照 — Tab A 基本信息（展示字段）

| 显示字段 | 业务目标 | DB 字段 | 一致性 |
| --- | --- | --- | :---: |
| 状态 | — | `tenants.status` | ✅ |
| 行业 | §6 N-13 | `tenants.industry` | ✅ |
| 联系人 | — | `tenants.contact_name` | ✅ |
| 联系电话 | — | `tenants.contact_phone` | ✅ |
| 联系邮箱 | — | `tenants.contact_email` | ✅ |
| 登录入口（前端拼接 slug） | — | — | ✅ |

#### 字段对照 — Tab B 域名管理：表格列

| 列 | 业务目标 | DB 字段（`domain_warmup_status`） | 一致性 |
| --- | --- | --- | :---: |
| 域名 | §5.4 | `domain` | ✅ |
| 验证状态徽标 | §5.4 | `verification_status` (pending/verifying/verified/failed) | ✅ |
| 预热档位 | §5.4 | `warmup_level` (1-6) | ✅ |
| 日发上限 | — | `daily_limit` | ✅ |
| 累计已发 | — | `total_sent` | ✅ |
| 验证时间 | — | `dns_verified_at` | ✅ |

#### 字段对照 — Tab B 域名管理：DNS 记录展开行

| 字段 | 业务目标 | 决策号 | DB 字段 | 一致性 |
| --- | --- | --- | --- | :---: |
| SPF 记录（只读 + 复制按钮） | §5.4 | D-002 / D-028 | `domain_warmup_status.spf_record` | 🟡 V3 加 clipboard |
| DKIM 记录（只读 + 复制按钮） | §5.4 | D-002 / D-028 | `domain_warmup_status.dkim_record` | 🟡 同上 |
| DMARC 记录（只读 + 复制按钮） | §5.4 | D-002 / D-028 | `domain_warmup_status.dmarc_record` | 🟡 同上 |

#### 字段对照 — Tab B 域名管理：子 Modal "添加域名"

| UI 字段 | 必填 | DB 字段 | 一致性 |
| --- | :---: | --- | :---: |
| 域名 | ✓ | `domain_warmup_status.domain` | ✅ 现状仅此 1 字段 |

> 注：V3 起始预热档位放到 3.1.2 Create Modal（创建租户时同步配置），本 Modal 仅用于追加域名。

#### 字段对照 — Tab C 团队成员：表格列

| 列 | DB 字段 | 一致性 |
| --- | --- | :---: |
| 邮箱 | `users.email` | ✅ |
| 姓名 | `users.name` | ✅ |
| 角色 | `user_roles.role` (admin/operator/viewer) | ✅ |
| 状态 | `users.status` | ✅ |
| 创建时间 | `users.created_at` | ✅ |

#### 字段对照 — Tab C 团队成员：子 Modal "添加用户"

| UI 字段 | 必填 | DB 字段 | 一致性 |
| --- | :---: | --- | :---: |
| 邮箱 | ✓ | `users.email` | ✅ |
| 姓名 | ✓ | `users.name` | ✅ |
| 密码 | ✓ | `users.password_hash` | ✅ |
| 角色 | ✓ | `user_roles.role` | ✅ |
| 状态 | — | `users.status` | ✅ |

#### 字段对照 — Tab C 团队成员：子 Modal "重置密码"

| UI 字段 | 必填 | DB 字段 | 一致性 |
| --- | :---: | --- | :---: |
| 新密码 (≥6 位) | ✓ | `users.password_hash` | ✅ |

#### 字段对照 — Tab D AI 配置：展示字段

> ❓ Tab D 字段名待 grep schema 确认 — 以下基于前端 `providerDetail?.xxx` 反推，未对照 schema.sql

| 显示字段 | DB 字段（**待核**） | 一致性 |
| --- | --- | :---: |
| 状态 | `?openrouter_providers.status` | ❓ 待核 schema |
| Key 掩码 | `?openrouter_providers.secret_masked` | ❓ |
| 可判定余额 | `?openrouter_providers.balance_amount` | ❓ |
| 余额来源 | `?openrouter_providers.balance_source` | ❓ |
| 最近刷新 | `?openrouter_providers.balance_checked_at` | ❓ |
| 最近轮换 | `?openrouter_providers.last_rotated_at` | ❓ |
| 最后修改人 | `?openrouter_providers.updated_by` | ❓ |
| 状态消息 | `?openrouter_providers.status_message` | ❓ |

#### 字段对照 — Tab D AI 配置：子 Modal "配置 OpenRouter"

| UI 字段 | 必填 | DB 字段（**待核**） | 一致性 |
| --- | :---: | --- | :---: |
| OpenRouter API key | ✓ | `?openrouter_providers.api_key`（加密） | ❓ 待核 |

#### API 端点

> 路径仅为示例 — V3 实施前需查 backend 实际路由。

| 路径 | 方法 | 用途 | 关联功能 | V3 状态 | 备注 |
| --- | --- | --- | --- | --- | --- |
| `/api/admin/tenants/{id}` | GET | 详情 | DET-F02 ~ F12 | PASS | — |
| `/api/admin/tenants/{id}/status` | PATCH | 状态切换 | DET-F01 | PASS | — |
| `/api/admin/tenants/{id}/domains` | POST | 添加域名 | DET-F04 | **PARTIAL** | V3 改：调 EngageLab Domain API 写 SPF/DKIM/DMARC |
| `/api/admin/tenants/{id}/domains/{domain}/verify` | POST | 触发域名验证 | DET-F05 | **MISSING** | V3 新增 |
| `/api/admin/tenants/{id}/domains/{domain}/warmup` | PATCH | 调整预热档位 | DET-F07 | PASS | — |
| `/api/admin/tenants/{id}/users` | POST | 添加用户 | DET-F09 | PASS | — |
| `/api/admin/tenants/{id}/users/{user_id}/reset-password` | POST | 重置密码 | DET-F10 | PASS | — |
| `/api/admin/tenants/{id}/openrouter` | PUT | 配 OpenRouter | DET-F12 | PASS | — |

#### 权限矩阵

| 功能组 | 平台 admin | 平台 viewer | 租户 admin | 租户 operator | 租户 viewer |
| --- | :---: | :---: | :---: | :---: | :---: |
| DET-F01（状态切换） | ✅ | ❌ | ❌ | ❌ | ❌ |
| DET-F02（基本信息显示）| ✅ | 👁️ 只读 | ❌ | ❌ | ❌ |
| DET-F03~F07（域名 Tab）| ✅ | 👁️ 只读 | ❌ | ❌ | ❌ |
| DET-F08~F10（团队 Tab）| ✅ | 👁️ 只读 | ❌ | ❌ | ❌ |
| DET-F11~F12（AI Tab）| ✅ | 👁️ 只读 | ❌ | ❌ | ❌ |

> **D-024 单端原则**：admin/Tenants 整模块 = 仅平台运营访问；租户端无任何 UI / API 入口。
> 租户端的"OpenRouter 配置"在 tenant/Settings 单独入口（UC-04 双入口设计）。
> `viewer` 是观察员；具体只读由后端 RLS + 前端权限指令双层控制。

#### V3 缺口

| # | 缺口 | 端 | 工作量 | 关联决策 |
| --- | --- | --- | :---: | --- |
| DET-G1 | 添加域名 API 改：调 EngageLab Domain API 写 SPF/DKIM/DMARC | 前+后 | M | D-002 / D-024 |
| DET-G2 | 域名"验证"API + 前端按钮 + 状态轮询 | 前+后 | M | D-002 / D-024 |
| DET-G3 | "一键复制 DNS 记录"clipboard 按钮 | 前端 | S | D-028 |

---

### 3.2 A-02 ~ A-12（**待铺开**）

> 颗粒度审过即铺开剩余 11 个 admin 模块。每模块按"List / Create / Detail / Action"拆子模块。

---

## 4. Tenant 端模块矩阵（**待铺开**）

> 9 个 tenant 模块。结构同上。

---

## 5. 字段一致性核对（**待铺开**）

> 三方对照：业务目标 §5 提的字段 vs 决策池 D-XXX 要的字段 vs `schema.sql` 实际字段。输出"对/缺/多/改/待核"清单。
>
> 已知大缺口预告：
> - **缺**：D-038 客户列表 10 项筛选 + D-039 评分要的 `clean_companies` 11 个新字段，schema 未实现
> - **改**：`tenant_contacts.is_default` schema 有但 D-033 V3 不写入
> - **缺**：D-037 联系人职位分类要的 4 张新表 `position_classification_*`，schema 未实现
> - **缺**：D-009 KeywordMaster 跨租户复用要的 `keyword_master` + `tenant_keyword`，schema 未实现
> - **待核**：openrouter_providers 表字段名（前端代码引用 vs schema.sql 实名）

---

## 6. V3 实施缺口汇总（**待铺开**）

> 从 §3 + §4 + §5 汇总。按"端 × 工作量档"分类。**不出具体天数**——天数估算属于 Delivery Plan 阶段。

---

## 颗粒度审核请求

本文档 §3.1 admin/Tenants 是颗粒度样例（拆 3 子模块：List / Create / Detail）。请确认：

1. **子模块拆分粒度**——admin/Tenants → 3 子模块（List / Create / Detail），合适吗？
   - Detail 内部 4 Tab 用功能矩阵的"位置"列分组，是否需要再拆成 3.1.3.A / 3.1.3.B / 3.1.3.C / 3.1.3.D 4 个孙模块？
2. **字段对照按"每个视图 / 每个 Modal 一张表"拆**——Detail 子模块拆出 9 张字段表（含 Tab D 待核 2 张），合适吗？还是按 Tab 合并到 4 张？
3. **❓ 待核标记**——对没核实的字段（如 Tab D OpenRouter）标 `❓ 待核 schema` 而不是猜，OK 吗？
4. **API 端点**——示例路径未核实实际路由，标"路径仅为示例"。这个先猜后核的处理方式 OK 吗？要不要 V3 实施前我去 grep `backend/app/api/` 全部核对一遍？
5. **权限矩阵**——5 角色（平台 admin/viewer + 租户 admin/operator/viewer）。租户端 admin/Tenants 全 ❌（D-024 单端原则）。这个矩阵在 admin 端模块基本是常量，要不要简化为模块级单行（"全模块 = 平台运营独占"）而不是每子模块重画？
6. **工作量档 S/M/L**——OK 吗？

颗粒度对了我就铺开剩余 11 admin + 9 tenant 模块 + §5 + §6。
