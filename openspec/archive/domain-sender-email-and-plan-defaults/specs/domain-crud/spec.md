## ADDED Requirements

### Requirement: Admin SHALL 在创建域名时维护发件邮箱

创建域名时 `sender_email` 为可选字段，接受完整邮箱格式（如 `sales@example.com`）。一个域名最多维护一个发件邮箱。

**API 变更**: `POST /admin/api/v1/tenants/{tenant_id}/domains`
- 请求新增字段: `sender_email` (string, 可选)
- 响应新增字段: `sender_email` (string | null)

#### Scenario: 创建域名并填写发件邮箱
- **GIVEN** Admin 在添加域名表单
- **WHEN** 填入域名 `example.com`、选择暖机档位、填入发件邮箱 `sales@example.com` 并提交
- **THEN** 域名创建成功，返回数据中 `sender_email` 为 `sales@example.com`

#### Scenario: 创建域名不填发件邮箱
- **GIVEN** Admin 在添加域名表单
- **WHEN** 填入域名和暖机档位但未填发件邮箱并提交
- **THEN** 域名创建成功，`sender_email` 为 null

### Requirement: Admin SHALL 编辑域名的发件邮箱和暖机配置

Admin 可修改域名的 `sender_email`、`warmup_rule_id`、`warmup_level`。域名本身（`domain` 字段）不可修改。修改暖机规则/档位时 `daily_limit` 根据新档位重算。

**API**: `PATCH /admin/api/v1/tenants/{tenant_id}/domains/{domain_id}`
- 请求字段: `sender_email` (string | null, 可选), `warmup_rule_id` (string, 可选), `warmup_level` (int, 可选)
- 响应: 更新后的完整域名对象

#### Scenario: 修改发件邮箱
- **GIVEN** 域名 `example.com` 的 sender_email 为 `old@example.com`
- **WHEN** Admin PATCH 将 sender_email 改为 `new@example.com`
- **THEN** 返回的域名对象中 sender_email 为 `new@example.com`

#### Scenario: 修改暖机档位触发 daily_limit 重算
- **GIVEN** 域名当前暖机档位为 1（daily_limit=50）
- **WHEN** Admin PATCH 将 warmup_level 改为 3
- **THEN** `daily_limit` 更新为档位 3 对应的限额值

#### Scenario: 尝试修改域名本身
- **GIVEN** 域名为 `example.com`
- **WHEN** Admin PATCH 请求中包含 `domain` 字段
- **THEN** `domain` 字段被忽略，不生效

### Requirement: Admin SHALL 删除域名且 MUST 检查所有 FK 关联

Admin 可删除域名，但当域名被 `domain_daily_usage` 或 `sending_plans` 表中的任何记录引用时，系统 MUST 拒绝删除并返回错误提示。`domain_warmup_history` 通过 CASCADE 自动清理。

**API**: `DELETE /admin/api/v1/tenants/{tenant_id}/domains/{domain_id}`
- 成功: 204 No Content
- 被引用: 409 Conflict，message 说明域名存在关联数据无法删除

#### Scenario: 删除无任何关联的域名
- **GIVEN** 域名 `example.com` 无 `domain_daily_usage` 和 `sending_plans` 记录
- **WHEN** Admin 确认删除该域名
- **THEN** 域名及关联的 warmup_history 被删除（CASCADE）

#### Scenario: 删除有发送计划引用的域名
- **GIVEN** 域名 `example.com` 被一个 sending_plan 引用（任何状态）
- **WHEN** Admin 尝试删除该域名
- **THEN** 系统返回 409 错误，提示"该域名存在关联数据，无法删除"

#### Scenario: 删除有使用记录的域名
- **GIVEN** 域名 `example.com` 在 `domain_daily_usage` 中有历史记录
- **WHEN** Admin 尝试删除该域名
- **THEN** 系统返回 409 错误，提示"该域名存在关联数据，无法删除"

### Requirement: Admin 域名 tab 前端交互规格

**表格布局：** 列顺序为 域名 → 发件邮箱 → 验证状态 → 预热档位 → 每日上限 → 已发送 → 操作。表格最小宽度从 760px 调整为 880px。

**添加表单：** 保持 `sm:grid-cols-2` 布局，新增发件邮箱输入框（placeholder="sales@example.com"，可选字段无 `*` 标记）。

**行操作：** 使用 DropdownMenu（三点图标 MoreHorizontal），菜单项：验证域名、编辑、删除（destructive 样式）。

**编辑弹窗：**
- DialogTitle: "编辑域名"
- DialogDescription: "编辑 {domain} 的配置"（域名作为上下文，非可编辑字段）
- 表单字段垂直单列排列：发件邮箱（Input）→ 预热规则（Select）→ 预热档位（Select）
- 保存按钮 loading 状态，失败用 toast.error

**删除确认：**
- AlertDialog，标题 "删除域名"，描述 "确定要删除域名 {domain} 吗？此操作不可恢复。"
- 409 时弹窗保持打开，显示红色 destructive 错误文本 "该域名存在关联数据，无法删除"
- 确认按钮使用 destructive variant，loading 状态

### Requirement: 域名列表 API MUST 返回 sender_email 字段

Admin 和 tenant 端的域名列表 API 返回值中 MUST 包含 `sender_email` 字段。

**API 变更**:
- `GET /admin/api/v1/tenants/{tenant_id}/domains` — 响应新增 `sender_email`
- `GET /t/{slug}/api/v1/domains` — 响应新增 `sender_email`

#### Scenario: 获取含发件邮箱的域名列表
- **GIVEN** tenant 有域名 A（sender_email=`a@a.com`）和域名 B（sender_email=null）
- **WHEN** 请求域名列表
- **THEN** 返回列表中域名 A 的 sender_email 为 `a@a.com`，域名 B 的 sender_email 为 null
