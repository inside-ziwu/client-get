---
title: "feat: 域名发件邮箱 + 新建计划默认值"
type: feat
status: active
date: 2026-05-23
origin: openspec/changes/domain-sender-email-and-plan-defaults/
depth: standard
execution_posture: tdd
---

# feat: 域名发件邮箱 + 新建计划默认值

## Overview

域名管理增加 `sender_email` 字段（一域名一邮箱），Admin 域名支持编辑（PATCH）和删除（DELETE，FK 引用阻止），Tenant 新建计划向导自动填入默认值（发件人名称=租户名称，发送域名=最早 verified 域名，发件邮箱=选中域名的 sender_email），切换域名时发件邮箱联动更新。

**执行姿态：TDD 测试驱动**。后端每个行为先写 pytest 测试再实现；前端类型/API 直接实现。每个执行单元 2-5 分钟可完成一个 RED→GREEN 周期。

---

## Problem Frame

域名只能创建和验证，无法编辑暖机配置或删除；无发件邮箱字段，Tenant 新建计划每次手动填写三个基本信息字段。(see origin: `openspec/changes/domain-sender-email-and-plan-defaults/proposal.md`)

---

## Requirements Trace

- R1. `domain_warmup_status` 新增 `sender_email varchar(255)` 可空列
- R2. Admin 创建域名时支持传入 `sender_email`
- R3. Admin 编辑域名：PATCH sender_email + warmup_rule_id + warmup_level（暖机变更重算 daily_limit + 记录 warmup_history），domain 字段忽略
- R4. Admin 删除域名：检查 `domain_daily_usage` 和 `sending_plans` 任何 FK 引用 → 409；无引用 → 物理删除（warmup_history CASCADE）
- R5. Admin/Tenant 域名列表 API 返回 `sender_email` 字段
- R6. `/me` 端点返回 `tenant_name`（从 `tenants.name`）
- R7. Tenant 新建计划：sender_name 取 tenant_name，domain_id 取最早 verified 域名，sender_email 取选中域名的 sender_email
- R8. 域名切换时 sender_email 自动联动更新
- R9. Admin 域名 tab：表格新增发件邮箱列，行操作 DropdownMenu（验证/编辑/删除），编辑弹窗（垂直布局），删除确认弹窗（409 弹窗内红色错误）

---

## Key Decisions

| ID | 决策 | 理由 |
|----|------|------|
| D1 | sender_email 直接加在 domain_warmup_status 表 | 一域名一邮箱，不值得新建表 |
| D2 | 域名物理删除 | 数据量小，删前有 FK 检查保护 |
| D3 | 暖机变更重算 daily_limit | 与创建逻辑一致 |
| D4 | 默认域名选择在前端完成 | 域名列表已返回 created_at |
| D5 | 域名切换联动发件邮箱在前端完成 | 域名列表已含 sender_email |
| D6 | 行操作使用 DropdownMenu 三点菜单 | 三个操作用菜单更整洁 |
| D7 | 409 错误在弹窗内展示 | 用户需明确知道删除失败原因 |
| D8 | 编辑弹窗域名显示在 DialogDescription | 域名是上下文非可编辑字段 |
| D9 | 编辑弹窗字段垂直单列排列 | 用户选择简单布局 |
| D10 | 新建计划页镜像 edit 页预加载模式 | loading+error+正常三种状态 |

---

## Scope Boundaries

不在本次范围：
- 不修改 Tenant 端域名 CRUD（保持只读）
- 不改动向导其他步骤
- 不做发件邮箱格式校验以外的业务校验
- 不做 Admin 前端组件测试

---

## Existing Patterns

### 后端服务层（参考 admin_config_service.py）
- `text()` 原始 SQL → `conn.execute()` → `result.mappings()` → `_serialize_domain()` 序列化
- `create_tenant_domain()`: 参数校验 → INSERT → warmup_history → audit.write
- `get_tenant_domain()`: SELECT + mappings().first() + 404 AppError

### 后端路由层（参考 admin/config.py:473-520）
- `PlatformAuthContext = Depends(get_current_platform_user)`
- `success_response()` / `paginated_response()` 包装
- payload 直接用 `dict`，无 Pydantic 入参 schema

### 后端测试（参考 test_sending_plan_status_check.py）
- pytest + `AsyncMock` + `patch.object(svc, method_name)`
- class-based 测试组织，`@pytest.mark.asyncio`
- 直接实例化 Service 类 + mock conn

### Alembic 迁移（参考 backend/alembic/versions/）
- 文件名: `YYYYMMDD_NNNN_description.py`
- `op.exec_driver_sql()` 执行原始 SQL

### 前端 API（参考 shared-api/src/admin/tenants.ts）
- factory 函数 `tenantsApi(client)` 返回方法对象
- `client.get<Type>(url)` / `client.post<Type>(url, data)`

### Tenant 前端（参考 send-plans/[id]/edit/page.tsx）
- 预加载数据 → loading/error 状态 → 构造 initialData → 传入 Wizard

---

## Implementation Units

### U1: 数据库迁移 — sender_email 列

**目标**: domain_warmup_status 新增 sender_email 可空字段

**文件**:
- `backend/alembic/versions/20260523_0100_add_sender_email_to_domain.py` (新建)

**步骤**:
1. 创建迁移文件，upgrade 执行 `ALTER TABLE domain_warmup_status ADD COLUMN sender_email VARCHAR(255)`
2. downgrade 执行 `ALTER TABLE domain_warmup_status DROP COLUMN sender_email`
3. 运行 `alembic upgrade head` 验证迁移成功

**测试**: 无（迁移文件通过运行验证）

---

### U2: 后端 — 域名查询返回 sender_email [R5]

**目标**: Admin 和 Tenant 的域名查询 SQL 增加 sender_email 字段

**文件**:
- `backend/app/services/admin_config_service.py` — list_tenant_domains、get_tenant_domain 的 SELECT 加 sender_email；_serialize_domain 加 sender_email
- `backend/app/services/tenant_ops_service.py` — list_domains 的 SELECT 和序列化加 sender_email

**步骤**:
1. `admin_config_service.py`: list_tenant_domains (line 1362) 和 get_tenant_domain (line 1517) 的 SELECT 加 `sender_email`
2. `_serialize_domain` (line 1748) 加 `"sender_email": row["sender_email"]`
3. `tenant_ops_service.py`: list_domains (line 826) 的 SELECT 加 `sender_email`，序列化字典加 `"sender_email": row["sender_email"]`

**测试**: 通过 U3/U4 的测试覆盖

---

### U3: 后端测试 — create_tenant_domain 支持 sender_email [R2]

**目标**: TDD 先写测试，验证创建域名时 sender_email 写入

**测试文件**: `backend/tests/test_domain_crud_service.py` (新建)

**测试场景**:
- `test_create_domain_with_sender_email`: mock conn.execute 验证 INSERT 参数含 sender_email
- `test_create_domain_without_sender_email`: 不传 sender_email 时参数为 None

**实现文件**: `backend/app/services/admin_config_service.py`

**实现步骤**:
1. 写测试（RED）
2. create_tenant_domain (line 1414-1434) INSERT 语句加 `sender_email` 列和 `:sender_email` 参数
3. 参数字典加 `"sender_email": payload.get("sender_email")`
4. 运行测试（GREEN）

---

### U4: 后端测试 — update_tenant_domain 服务方法 [R3]

**目标**: TDD 先写测试，新增编辑域名服务方法

**测试文件**: `backend/tests/test_domain_crud_service.py`

**测试场景**:
- `test_update_sender_email`: 更新 sender_email 成功
- `test_update_warmup_triggers_daily_limit_recalc`: 修改 warmup_level 后 daily_limit 重算 + warmup_history 记录
- `test_update_ignores_domain_field`: payload 含 domain 字段时被忽略
- `test_update_invalid_warmup_returns_422`: 无效 warmup_rule_id/level 返回 422
- `test_update_nonexistent_domain_returns_404`: 域名不存在返回 404

**实现文件**: `backend/app/services/admin_config_service.py`

**实现步骤**:
1. 写全部测试（RED）
2. 新增 `update_tenant_domain(conn, *, tenant_id, domain_id, payload, platform_user_id)` 方法：
   - 从 payload 中 pop 掉 `domain` 字段（忽略）
   - 如有 warmup_rule_id/warmup_level：查 warmup_rule_levels 取 daily_limit（同 create 逻辑），更新三字段 + 记录 warmup_history
   - 如有 sender_email：UPDATE sender_email
   - 用单条 UPDATE SET ... WHERE 拼接动态字段
   - audit.write
   - 返回 get_tenant_domain 结果
3. 运行测试（GREEN）

---

### U5: 后端测试 — delete_tenant_domain 服务方法 [R4]

**目标**: TDD 先写测试，新增删除域名服务方法

**测试文件**: `backend/tests/test_domain_crud_service.py`

**测试场景**:
- `test_delete_domain_success`: 无 FK 引用时删除成功
- `test_delete_domain_with_daily_usage_returns_409`: domain_daily_usage 有记录时 409
- `test_delete_domain_with_sending_plans_returns_409`: sending_plans 有记录时 409
- `test_delete_nonexistent_domain_returns_404`: 域名不存在 404

**实现文件**: `backend/app/services/admin_config_service.py`

**实现步骤**:
1. 写全部测试（RED）
2. 新增 `delete_tenant_domain(conn, *, tenant_id, domain_id, platform_user_id)` 方法：
   - get_tenant_domain 确认存在（不存在抛 404）
   - 查 `SELECT COUNT(*) FROM domain_daily_usage WHERE domain_id = :domain_id`
   - 查 `SELECT COUNT(*) FROM sending_plans WHERE domain_id = :domain_id`
   - 任一 > 0 → raise AppError(code="CONFLICT", status_code=409, message="该域名存在关联数据，无法删除")
   - `DELETE FROM domain_warmup_status WHERE id = :domain_id AND tenant_id = :tenant_id`
   - audit.write
3. 运行测试（GREEN）

---

### U6: 后端路由 — PATCH/DELETE 端点 [R3, R4]

**目标**: TDD 先写路由测试，新增 PATCH 和 DELETE 路由

**测试文件**: `backend/tests/test_domain_crud_routes.py` (新建)

**测试场景**:
- `test_patch_domain_success`: 200 + 调用 service.update_tenant_domain
- `test_patch_domain_not_found`: 404
- `test_delete_domain_success`: 204
- `test_delete_domain_conflict`: 409

**实现文件**: `backend/app/api/admin/config.py`

**实现步骤**:
1. 写路由测试（RED）— 参考 test_sending_plan_routes.py 模式
2. config.py 新增两个路由：
   ```
   @router.patch("/tenants/{tenant_id}/domains/{domain_id}")
   @router.delete("/tenants/{tenant_id}/domains/{domain_id}")
   ```
3. PATCH 调用 `service.update_tenant_domain`，返回 `success_response`
4. DELETE 调用 `service.delete_tenant_domain`，返回 `Response(status_code=204)`
5. 运行测试（GREEN）

---

### U7: 后端 — /me 端点返回 tenant_name [R6]

**目标**: TDD 先写测试，/me 返回 tenant_name

**测试文件**: `backend/tests/test_tenant_me.py` (新建)

**测试场景**:
- `test_me_returns_tenant_name`: /me 响应包含 tenant_name 字段

**实现文件**:
- `backend/app/api/tenant/auth.py` — /me 端点 SELECT 加 `name`，传入 TenantMeResponse
- `backend/app/schemas/auth.py` — TenantMeResponse 加 `tenant_name: str | None = None`

**实现步骤**:
1. 写测试（RED）
2. `TenantMeResponse` 加 `tenant_name: str | None = None`
3. /me 端点 SELECT 加 `name`，取出 `tenant_row.mappings().first()` 取 `name` 字段
4. `TenantMeResponse(... tenant_name=row["name"])` 
5. 运行测试（GREEN）

---

### U8: 前端类型 — sender_email + tenant_name

**目标**: 前端类型定义新增字段

**文件**:
- `frontend/packages/shared-types/src/admin.ts` — TenantDomain 加 `sender_email: string | null`
- `frontend/packages/shared-types/src/tenant.ts` — TenantDomainInfo 加 `sender_email: string | null`
- `frontend/packages/shared-types/src/auth.ts` — CurrentUser 加 `tenant_name?: string`

**步骤**: 直接添加字段，无测试

---

### U9: 前端 API — Admin 域名 CRUD 方法

**目标**: Admin API 方法支持 sender_email + 新增 updateDomain / deleteDomain

**文件**: `frontend/packages/shared-api/src/admin/tenants.ts`

**步骤**:
1. `createDomain` 方法参数类型扩展 `sender_email?: string`
2. 新增 `updateDomain(tenantId, domainId, data)` — `client.patch<TenantDomain>(...)`
3. 新增 `deleteDomain(tenantId, domainId)` — `client.delete(...)`

---

### U10: Admin 前端 — 域名添加表单增加发件邮箱 [R2, R9]

**目标**: 添加域名表单新增 sender_email 输入框

**文件**: `frontend/apps/admin/src/app/(dashboard)/tenants/client-page.tsx`

**步骤**:
1. 表单 state 新增 `senderEmail` 字段
2. 在 sm:grid-cols-2 布局中新增 Input（label 发件邮箱，placeholder="sales@example.com"，可选无 * 标记）
3. createDomain 调用时传入 `sender_email: senderEmail || undefined`

---

### U11: Admin 前端 — 域名列表表格增强 [R9]

**目标**: 表格新增发件邮箱列 + 行操作改为 DropdownMenu

**文件**: `frontend/apps/admin/src/app/(dashboard)/tenants/client-page.tsx`

**步骤**:
1. 表格 th/td 新增"发件邮箱"列（域名后，验证状态前），空值显示 `—`
2. 表格 min-w 从 760px 调整为 880px
3. 行操作列：替换现有"验证域名"按钮为 DropdownMenu（MoreHorizontal 图标触发）
4. 菜单项：验证域名、编辑（触发编辑弹窗）、删除（destructive，触发删除确认）

---

### U12: Admin 前端 — 编辑域名弹窗 [R3, R9]

**目标**: 编辑域名的 Dialog 弹窗

**文件**: `frontend/apps/admin/src/app/(dashboard)/tenants/client-page.tsx`

**步骤**:
1. 新增编辑状态：`editingDomain` + `editForm`（sender_email, warmup_rule_id, warmup_level）
2. Dialog 组件：DialogTitle "编辑域名"，DialogDescription "编辑 {domain} 的配置"
3. 表单字段垂直单列：发件邮箱 Input → 预热规则 Select → 预热档位 Select
4. 保存按钮 loading 状态，调用 `updateDomain` API
5. 成功后 invalidate 域名列表 query，关闭弹窗
6. 失败用 toast.error

---

### U13: Admin 前端 — 删除域名确认弹窗 [R4, R9]

**目标**: 删除域名的 AlertDialog 弹窗，处理 409 错误

**文件**: `frontend/apps/admin/src/app/(dashboard)/tenants/client-page.tsx`

**步骤**:
1. AlertDialog 组件：标题 "删除域名"，描述 "确定要删除域名 {domain} 吗？此操作不可恢复。"
2. 确认按钮 destructive variant + loading 状态
3. 调用 `deleteDomain` API
4. 成功后 invalidate 域名列表 query，关闭弹窗
5. 409 错误：弹窗保持打开，显示红色 destructive 错误文本 "该域名存在关联数据，无法删除"
6. 其他错误：toast.error

---

### U14: Tenant 前端 — 新建计划默认值 [R7, R8]

**目标**: new/page.tsx 预加载数据构造 initialData + 域名切换联动

**文件**:
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/page.tsx` — 预加载 /me + 域名列表，构造 initialData
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-basic-info.tsx` — 域名 onValueChange 联动 sender_email

**步骤**:
1. `new/page.tsx` 镜像 edit/page.tsx 模式：
   - useQuery 加载 /me（获取 tenant_name）
   - useQuery 加载 verified 域名列表
   - loading / error 状态展示
   - 构造 initialData：sender_name=tenant_name，domain_id=verified 域名按 created_at 升序第一个的 id，sender_email=选中域名的 sender_email（无则空字符串）
   - 传入 `<SendPlanWizard mode="create" initialData={initialData} />`
2. `step-basic-info.tsx` 域名 onValueChange：
   - 从已加载 verifiedDomains 中找到选中域名
   - `update('sender_email', selectedDomain?.sender_email || '')`

---

## Dependencies & Sequencing

```
U1（迁移）→ U2（查询加字段）→ U3（创建测试+实现）
                              → U4（编辑测试+实现）→ U6（路由测试+实现）
                              → U5（删除测试+实现）→ U6
                        U7（/me 测试+实现）
                        U8（前端类型）→ U9（前端 API）→ U10/U11/U12/U13（Admin 前端）
                                                   → U14（Tenant 前端）
```

后端 U1-U7 先行（自底向上，可独立提交），前端 U8-U14 后行。U8 可与 U1 并行开始。

---

## Risks

| 风险 | 缓解 |
|------|------|
| 现有域名 sender_email 全为 NULL | 前端遇到 null 时显示 — 或留空，用户手动填写 |
| 域名删除不可恢复 | 删除前 FK 检查 + 前端确认弹窗双重保护 |
| edit/page.tsx 预加载模式需要适配 create 场景 | 镜像已有模式，差异仅在 initialData 构造 |
