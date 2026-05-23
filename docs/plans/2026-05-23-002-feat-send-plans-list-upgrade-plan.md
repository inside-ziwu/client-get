---
title: "feat: 发送计划列表页体验升级（筛选/分页/操作菜单/编辑/删除）"
type: feat
status: active
date: 2026-05-23
origin: openspec/changes/2026-05-23-send-plans-list-upgrade/
depth: standard
execution_posture: tdd
---

# feat: 发送计划列表页体验升级（筛选/分页/操作菜单/编辑/删除）

## Overview

将发送计划列表页从只读展示升级为完整管理界面：三维筛选（状态 + 名称搜索 + 日期范围）、page/page_size 分页、行末操作菜单（按状态动态展示编辑/删除）、草稿编辑（复用向导预填数据）、删除确认弹窗、时间格式优化、移除进度条列。后端新增 complete-update 端点 + 状态检查 + 筛选分页查询。

**执行姿态：TDD 测试驱动**。后端每个行为先写 pytest 测试再实现；前端关键行为写 vitest 测试。每个执行单元 2-5 分钟可完成一个 RED→GREEN 周期。

---

## Problem Frame

列表页当前只有「新建」和「查看」两个能力。计划数量增多后无法按状态或名称快速定位；草稿无法修改只能删除重建；已结束计划无法清理；时间只显示日期缺少精度；进度条列信息价值低。(see origin: `openspec/changes/2026-05-23-send-plans-list-upgrade/proposal.md`)

---

## Requirements Trace

- R1. 状态筛选下拉：全部/草稿/已排期/执行中/已暂停/已完成/已取消
- R2. 名称关键词搜索框（防抖）
- R3. 创建时间日期范围筛选
- R4. page/page_size 分页（与 companies 页面一致）
- R5. 行末操作菜单（「...」按钮），菜单项按状态动态展示
- R6. 草稿：查看详情、编辑、删除
- R7. 已完成/已取消：查看详情、删除
- R8. 已排期/执行中/已暂停：仅查看详情 (D5)
- R9. 点击行本身进入详情页
- R10. 编辑草稿跳转向导页预填数据（recipient_config 而非锁定列表）(D6)
- R11. 删除操作二次确认弹窗
- R12. 创建时间显示日期+时间（YYYY-MM-DD HH:mm）
- R13. 移除进度条列

---

## Key Decisions

| ID | 决策 | 理由 |
|----|------|------|
| D1 | 编辑草稿用 `complete-update` 原子端点 | 与 `complete-create` 对称，一次请求替换 plan+steps+recipients |
| D2 | 后端 PATCH/DELETE/complete-update 强制状态检查 | 防止 API 层面绕过前端 UI 限制，403 |
| D3 | page/page_size 分页 | 与 companies 页面一致，非 cursor |
| D5 | scheduled 与 running/paused 同级 | 即将执行的计划不应被编辑或删除 |
| D6 | 编辑时预填 recipient_config | 草稿阶段未锁定收件人，向导操作来源配置 |
| D7 | 缓存键统一 + FOR UPDATE 锁 + COUNT(*) + 日期边界 | Codex 审查技术改进 |

---

## Scope Boundaries

不在本次范围：
- 批量操作（批量删除、批量取消）
- 列头点击排序
- 导出功能
- 角色权限 UI 过滤（后端已强制校验）

### Deferred to Follow-Up Work
- 前端组件测试完整覆盖（本次仅覆盖关键行为路径）

---

## Existing Patterns

### 后端测试模式（参考 test_auth_refresh.py）
- `create_app()` + `dependency_overrides[get_connection]` mock 数据库
- `httpx.AsyncClient` + `ASGITransport` 做集成测试
- `AsyncMock` / `MagicMock` 模拟查询结果
- 测试文件位于 `backend/tests/`

### 后端筛选+分页（参考 companies）
- `backend/app/services/tenant_query_service.py` → `companies_page`：`where_clauses` 列表 + `params` 字典动态拼接，COUNT(*) + LIMIT/OFFSET
- `backend/app/api/tenant/ops.py` → page/page_size Query 参数

### 前端分页（参考 companies）
- `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`：`page`/`pageSize`/`jumpPage` 状态，query key 含分页筛选参数

### 前端测试基础设施
- `frontend/apps/tenant/vitest.config.ts` 已配置 jsdom 环境
- 测试目录：`frontend/apps/tenant/test/`（需创建）

### 删除确认弹窗（参考 templates）
- `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`：`deleteTarget` 状态 + `AlertDialog` + `deleteMutation`

---

## Sequencing

```
Phase A: 后端筛选分页 (U1-U5)
    ↓
Phase B: 后端状态检查 + complete-update (U6-U11)
    ↓
Phase C: 前端基础设施 (U12-U15)
    ↓
Phase D: 前端列表页 (U16-U22)
    ↓
Phase E: 编辑模式 (U23-U25)
```

Phase A 和 Phase B 后端部分可并行。Phase C 先于 D/E。Phase D 依赖 A+C。Phase E 依赖 B+C。

---

## Implementation Units

### Phase A: 后端筛选与分页

### U1. 测试+实现：list_sending_plans status 筛选

**Goal:** 列表接口支持按状态精确筛选

**Requirements:** R1

**Dependencies:** 无

**Files:**
- `backend/tests/test_sending_plans_list.py`（新建）
- `backend/app/services/tenant_messaging_service.py`（修改 `list_sending_plans`）

**Approach:**
- RED：新建测试文件，mock `conn.execute` 返回多条不同 status 的计划，调用 `list_sending_plans(conn, tenant_id, status="draft")`，断言只返回 draft 记录
- GREEN：在 `list_sending_plans` 方法签名增加 `status: str | None = None`，当 status 有值时拼接 `AND sp.status = :status`

**Patterns to follow:** `backend/tests/test_auth_refresh.py` 的 mock 模式；`tenant_query_service.py` 的 `where_clauses` 动态拼接模式

**Test scenarios:**
- 传入 status=draft，mock 数据含 draft+running，断言只返回 draft
- 不传 status，返回全部记录
- 传入不存在的 status 值，返回空列表

**Verification:** `pytest backend/tests/test_sending_plans_list.py -v` 全部通过

---

### U2. 测试+实现：list_sending_plans keyword 模糊搜索

**Goal:** 列表接口支持按名称关键词模糊搜索

**Requirements:** R2

**Dependencies:** U1

**Files:**
- `backend/tests/test_sending_plans_list.py`（追加）
- `backend/app/services/tenant_messaging_service.py`（修改）

**Approach:**
- RED：追加测试用例，mock 数据含 name="巴西市场推广" 和 name="欧洲拓展"，传入 keyword="巴西"，断言只返回第一条
- GREEN：方法签名增加 `keyword: str | None = None`，当有值时拼接 `AND sp.name ILIKE :keyword`，参数 `f"%{keyword}%"`

**Test scenarios:**
- keyword="巴西" 模糊匹配名称包含"巴西"的记录
- keyword 为空字符串或 None，不影响结果
- keyword 大小写不敏感（ILIKE）

**Verification:** 测试通过

---

### U3. 测试+实现：list_sending_plans 日期范围筛选

**Goal:** 列表接口支持按创建时间范围筛选

**Requirements:** R3

**Dependencies:** U1

**Files:**
- `backend/tests/test_sending_plans_list.py`（追加）
- `backend/app/services/tenant_messaging_service.py`（修改）

**Approach:**
- RED：mock 数据含不同 created_at 的记录，传入 date_from="2026-05-01" + date_to="2026-05-15"，断言只返回范围内记录
- GREEN：增加 `date_from`/`date_to` 参数，date_from → `AND sp.created_at >= :date_from`，date_to → `AND sp.created_at < :date_to_exclusive`（date_to 字符串 +1 天，包含当天）

**Test scenarios:**
- date_from + date_to 范围筛选，返回范围内记录
- 仅传 date_from 无 date_to，返回该日期之后全部
- date_to="2026-05-15" 应包含 5 月 15 日当天的记录（< 5 月 16 日）

**Verification:** 测试通过

---

### U4. 测试+实现：list_sending_plans 分页 + COUNT(*)

**Goal:** 列表接口支持 page/page_size 分页并返回 total 总数

**Requirements:** R4

**Dependencies:** U1

**Files:**
- `backend/tests/test_sending_plans_list.py`（追加）
- `backend/app/services/tenant_messaging_service.py`（修改）

**Approach:**
- RED：mock 5 条记录，传入 page=2 page_size=2，断言返回第 3-4 条，total=5
- GREEN：方法签名增加 `page: int = 1`, `page_size: int = 20`。查询拆分为两步：1) `SELECT COUNT(*) ...` 获取 total 2) 原查询加 `ORDER BY sp.created_at DESC LIMIT :limit OFFSET :offset`。返回值从 `list[dict]` 改为 `tuple[list[dict], int]`

**Test scenarios:**
- page=1 page_size=2，返回前 2 条 + total=5
- page=2 page_size=2，返回第 3-4 条 + total=5
- page 超出范围，返回空列表 + total=5
- 有筛选条件时 total 反映筛选后的总数

**Verification:** 测试通过

---

### U5. 测试+实现：路由层筛选分页参数透传

**Goal:** messaging.py 路由接收 Query 参数并传给 service

**Requirements:** R1, R2, R3, R4

**Dependencies:** U4

**Files:**
- `backend/tests/test_sending_plans_list.py`（追加集成测试）
- `backend/app/api/tenant/messaging.py`（修改 `list_sending_plans`）

**Approach:**
- RED：用 httpx AsyncClient 发送 `GET /api/v1/sending-plans?status=draft&page=1&page_size=20`，mock service 返回值，断言 HTTP 200 + 响应体含 data + total
- GREEN：路由函数增加 Query 参数 `status`, `keyword`, `date_from`, `date_to`, `page`, `page_size`，调用 service 并解构 `(items, total)`，返回 `paginated_response(items, total=total)`

**Test scenarios:**
- GET /sending-plans?status=draft 返回 200 + 正确结构
- GET /sending-plans 不传参数，使用默认值
- 返回体包含 data 数组 + total 字段

**Verification:** 测试通过

---

### Phase B: 后端状态检查与 complete-update

### U6. 测试+实现：update_sending_plan 状态检查

**Goal:** PATCH 只允许 draft 计划，非 draft 返回 403

**Requirements:** D2

**Dependencies:** 无

**Files:**
- `backend/tests/test_sending_plans_status.py`（新建）
- `backend/app/services/tenant_messaging_service.py`（修改 `update_sending_plan`）

**Approach:**
- RED：mock 计划 status=running，调用 update_sending_plan，断言抛出 403 AppError
- GREEN：方法开头 `SELECT status FROM sending_plans WHERE id = :id AND tenant_id = :tenant_id FOR UPDATE`，status 非 draft 则 `raise AppError(status_code=403, ...)`

**Patterns to follow:** `start_plan` 方法中 `FOR UPDATE` 锁的使用模式

**Test scenarios:**
- status=draft 更新成功
- status=running 更新返回 403
- status=scheduled 更新返回 403
- 计划不存在返回 404

**Verification:** 测试通过

---

### U7. 测试+实现：delete_sending_plan 状态检查

**Goal:** DELETE 只允许 draft/completed/cancelled，其他返回 403

**Requirements:** D2

**Dependencies:** 无

**Files:**
- `backend/tests/test_sending_plans_status.py`（追加）
- `backend/app/services/tenant_messaging_service.py`（修改 `delete_sending_plan`）

**Approach:**
- RED：mock status=running，调用 delete_sending_plan，断言 403
- GREEN：方法开头 FOR UPDATE 查询 status，不在 (draft, completed, cancelled) 则 403

**Test scenarios:**
- status=draft 删除成功
- status=completed 删除成功
- status=cancelled 删除成功
- status=running 删除返回 403
- status=scheduled 删除返回 403
- status=paused 删除返回 403

**Verification:** 测试通过

---

### U8. 测试+实现：complete-update 路由 + 状态检查

**Goal:** 新增 complete-update 端点，仅 draft 可调用

**Requirements:** D1, D2

**Dependencies:** U6

**Files:**
- `backend/tests/test_sending_plans_complete_update.py`（新建）
- `backend/app/api/tenant/messaging.py`（新增路由）
- `backend/app/services/tenant_messaging_service.py`（新增 `complete_update_sending_plan` 骨架）

**Approach:**
- RED：POST /sending-plans/{id}/complete-update，mock status=scheduled，断言 403
- GREEN：messaging.py 新增 `@router.post("/sending-plans/{plan_id}/complete-update")`，service 新增 `complete_update_sending_plan` 方法，开头 FOR UPDATE 检查 status=draft

**Test scenarios:**
- status=draft 继续执行（暂时跳过完整逻辑，仅检查状态通过）
- status=scheduled 返回 403
- status=running 返回 403
- 权限：无角色用户返回 403

**Verification:** 测试通过

---

### U9. 测试+实现：complete-update 基本信息更新

**Goal:** complete-update 原子更新计划基本信息

**Requirements:** R10, D1

**Dependencies:** U8

**Files:**
- `backend/tests/test_sending_plans_complete_update.py`（追加）
- `backend/app/services/tenant_messaging_service.py`（补充 `complete_update_sending_plan`）

**Approach:**
- RED：传入修改后的 plan 信息（name, description, sender_name 等），断言 UPDATE 执行并返回更新后数据
- GREEN：复用 `_normalize_complete_plan_payload` 验证 payload，执行 `UPDATE sending_plans SET name=:name, description=:description, ... WHERE id=:id AND tenant_id=:tenant_id`

**Test scenarios:**
- 更新 name + description 成功
- 更新 sender_name + sender_email + domain_id 成功
- 更新 recipient_source + recipient_config 成功
- payload 验证失败返回 422

**Verification:** 测试通过

---

### U10. 测试+实现：complete-update 步骤替换

**Goal:** complete-update 删除旧步骤并插入新步骤

**Requirements:** D1

**Dependencies:** U9

**Files:**
- `backend/tests/test_sending_plans_complete_update.py`（追加）
- `backend/app/services/tenant_messaging_service.py`（补充）

**Approach:**
- RED：mock 计划原有 2 步骤，传入 3 个新步骤，断言 DELETE 旧步骤 + INSERT 3 个新步骤
- GREEN：在 complete_update_sending_plan 中添加 `DELETE FROM sequence_steps WHERE plan_id = :plan_id AND tenant_id = :tenant_id`，然后逐个调用 `create_plan_step`

**Test scenarios:**
- 原 2 步骤 → 新 3 步骤，旧步骤全部删除 + 新步骤全部创建
- 步骤编号自动规范化（从 1 开始连续）
- 第一步 condition_type 强制为 always + delay_days=0

**Verification:** 测试通过

---

### U11. 测试+实现：complete-update 收件人处理

**Goal:** complete-update 处理收件人重新锁定

**Requirements:** D1, D6

**Dependencies:** U10

**Files:**
- `backend/tests/test_sending_plans_complete_update.py`（追加）
- `backend/app/services/tenant_messaging_service.py`（补充）

**Approach:**
- RED：传入 lock_recipients=true + 有效 recipient_config，断言旧收件人清除 + 重新锁定
- GREEN：`DELETE FROM plan_recipients WHERE plan_id = :plan_id`，然后调用 `lock_plan_recipients`。最后 `return await self.get_sending_plan(...)`

**Test scenarios:**
- lock_recipients=true 清除旧收件人 + 锁定新收件人
- lock_recipients=false 不处理收件人
- 完整 complete-update 流程：更新基本信息 + 替换步骤 + 重新锁定收件人

**Verification:** 测试通过

---

### Phase C: 前端基础设施

### U12. PlanFilters 类型扩展

**Goal:** 扩展 PlanFilters 类型支持日期和分页参数

**Requirements:** R1, R2, R3, R4

**Dependencies:** 无

**Files:**
- `frontend/packages/shared-types/src/api.ts`（修改）

**Approach:**
- PlanFilters 增加 `date_from?: string`、`date_to?: string`、`page?: number`、`page_size?: number`

**Test expectation:** none — 纯类型定义，TypeScript 编译通过即可

**Verification:** `tsc --noEmit` 编译无错误

---

### U13. API 客户端：completeUpdate 方法

**Goal:** 新增 completeUpdate API 调用方法

**Requirements:** D1

**Dependencies:** U12

**Files:**
- `frontend/packages/shared-api/src/tenant/sending-plans.ts`（修改）

**Approach:**
- 新增 `completeUpdate(planId: string, data: {...})` 方法
- URL: `/api/v1/sending-plans/${planId}/complete-update`
- 签名与 `completeCreate` 相同，额外接受 `planId`

**Test expectation:** none — 纯 API 封装，TypeScript 编译通过即可

**Verification:** 编译无错误

---

### U14. 列表页 query key 统一

**Goal:** 修复列表页与向导的缓存键不一致问题

**Requirements:** D7

**Dependencies:** 无

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx`（修改 queryKey）
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/page.tsx`（确认 invalidation key）

**Approach:**
- 列表页 queryKey 从 `['tenant', 'send-plans']` 改为 `['tenant', 'sendingPlans']`
- 确认向导页 invalidation `['tenant', 'sendingPlans']` 一致
- 全局搜索 `send-plans` 和 `sendingPlans` 确认无遗漏

**Test expectation:** none — 配置修复，手动验证创建后列表刷新

**Verification:** 创建计划后列表页自动更新

---

### U15. 前端测试 setup

**Goal:** 创建前端测试基础设施

**Dependencies:** 无

**Files:**
- `frontend/apps/tenant/test/setup.ts`（新建）

**Approach:**
- 创建 test/setup.ts，配置 jsdom 环境和必要的 mock（如 next/navigation 的 useRouter）
- 确认 `npx vitest run` 能执行（passWithNoTests 已配置）

**Test expectation:** none — 基础设施搭建

**Verification:** `cd frontend/apps/tenant && npx vitest run` 无报错

---

### Phase D: 前端列表页

### U16. 列表页：Table 组件替换 + 新列定义

**Goal:** 用 Table 组件替换 DataTable，定义新列（含时间格式、移除进度条）

**Requirements:** R9, R12, R13

**Dependencies:** U14, U15

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx`（重写）

**Approach:**
- 替换 DataTable 为直接使用 Table/TableRow/TableCell（参考 companies 页面），支持行级 onClick
- 列定义：计划名称、状态（StatusTag）、收件人数、创建时间（`YYYY-MM-DD HH:mm`）、操作
- 行点击 `router.push(/send-plans/${id})`
- 移除 Progress 组件和进度条列
- 创建时间格式化：`row.created_at?.slice(0, 16).replace('T', ' ')`

**Test scenarios:**
- 创建时间显示为 "2026-05-22 14:30" 格式
- 无进度条列
- 点击行导航到详情页

**Verification:** 页面渲染正常，时间格式正确，无进度条

---

### U17. 列表页：状态筛选下拉

**Goal:** 列表顶部增加状态筛选 Select 组件

**Requirements:** R1

**Dependencies:** U16, U5（后端筛选支持）

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx`（修改）

**Approach:**
- 新增 `filters` 状态对象 `{ status, keyword, date_from, date_to }`
- 新增 Select 组件，选项：全部（空值）/ 草稿 / 已排期 / 执行中 / 已暂停 / 已完成 / 已取消
- 选中后更新 `filters.status` 并重置 `page=1`
- queryKey 包含 filters：`['tenant', 'sendingPlans', page, pageSize, filters]`

**Test scenarios:**
- 初始状态下拉显示"全部"
- 选择"草稿"后 queryKey 变化触发重新查询
- 切换筛选后 page 重置为 1

**Verification:** 选择状态后列表仅显示对应状态的计划

---

### U18. 列表页：名称搜索框 + 防抖

**Goal:** 列表顶部增加名称搜索输入框，300ms 防抖

**Requirements:** R2

**Dependencies:** U16

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx`（修改）

**Approach:**
- 新增 Input 组件，placeholder="搜索计划名称"
- 本地 `searchText` 状态 + `useEffect` 做 300ms 防抖，防抖后更新 `filters.keyword`
- keyword 变化重置 page=1

**Test scenarios:**
- 输入文字后 300ms 触发查询
- 快速连续输入只触发最后一次查询
- 清空搜索框恢复全部结果

**Verification:** 输入关键词后列表筛选结果正确

---

### U19. 列表页：日期范围筛选

**Goal:** 列表顶部增加创建时间日期范围筛选

**Requirements:** R3

**Dependencies:** U16

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx`（修改）

**Approach:**
- 两个 `<Input type="date" />` 控件（开始日期 / 结束日期）
- 变更后更新 `filters.date_from` / `filters.date_to`，重置 page=1
- 放在筛选栏中，与状态下拉和搜索框同行

**Test scenarios:**
- 设置开始日期 + 结束日期后查询参数正确
- 仅设置开始日期也能筛选
- 清除日期恢复全部

**Verification:** 日期筛选后列表结果正确

---

### U20. 列表页：分页组件

**Goal:** 列表底部增加分页控件

**Requirements:** R4

**Dependencies:** U16, U5（后端分页支持）

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx`（修改）

**Approach:**
- 新增 `page`、`pageSize`、`jumpPage` 状态（参考 companies 页面）
- queryFn 传入 `{ ...filters, page, page_size: pageSize }`
- 分页 UI：上一页/下一页按钮 + 每页条数选择（20/50/100）+ 跳转页码输入 + 「共 X 条」
- 上一页 disabled：page === 1；下一页 disabled：page >= totalPages

**Test scenarios:**
- 初始显示第 1 页，总数正确
- 点击下一页翻页，数据更新
- 切换每页条数后重置到第 1 页
- 输入页码跳转到指定页
- 筛选条件变更时 page 重置为 1

**Verification:** 翻页数据正确，筛选保持

---

### U21. 列表页：操作菜单列

**Goal:** 每行末尾增加操作菜单，按状态动态展示

**Requirements:** R5, R6, R7, R8

**Dependencies:** U16

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx`（修改）

**Approach:**
- 操作列使用 DropdownMenu（Radix）：trigger 为 `<Button variant="ghost" size="icon"><MoreHorizontal /></Button>`
- 菜单项按状态动态渲染：
  - 所有状态：「查看详情」→ `router.push`
  - draft：「编辑」→ `/send-plans/${id}/edit`
  - draft / completed / cancelled：「删除」→ `setDeleteTarget(row)`
  - scheduled / running / paused：无编辑和删除
- 操作菜单区域 `e.stopPropagation()` 阻止行点击导航

**Test scenarios:**
- draft 行菜单显示 3 项（详情/编辑/删除）
- running 行菜单仅显示 1 项（详情）
- scheduled 行菜单仅显示 1 项（详情）
- completed 行菜单显示 2 项（详情/删除）
- 点击菜单按钮不触发行导航

**Verification:** 各状态菜单项正确，行导航不被误触发

---

### U22. 列表页：删除确认弹窗

**Goal:** 删除操作增加二次确认

**Requirements:** R11

**Dependencies:** U21

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx`（修改）

**Approach:**
- `deleteTarget` 状态存储待删除计划
- AlertDialog：标题「确认删除计划？」，描述「删除后无法恢复，确认要删除「{name}」吗？」
- 确认触发 `deleteMutation`（调用 `tenantApi.sendingPlans.delete(id)`）
- 成功后 invalidate `['tenant', 'sendingPlans']` + toast 提示
- 参考 `templates/page.tsx` 的 AlertDialog 使用模式

**Test scenarios:**
- 点击删除弹出确认对话框
- 点击取消关闭对话框，不触发删除
- 点击确认执行删除，成功后列表刷新
- 删除期间确认按钮禁用

**Verification:** 删除流程完整，列表刷新

---

### Phase E: 编辑模式

### U23. 向导组件提取 SendPlanWizard

**Goal:** 从 new/page.tsx 提取可复用向导组件

**Requirements:** R10

**Dependencies:** U13

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/page.tsx`（重构）
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/components/send-plan-wizard.tsx`（新建）

**Approach:**
- 将 new/page.tsx 中的向导核心逻辑（state、validation、步骤渲染、mutation）提取到 `SendPlanWizard` 组件
- Props：`initialData?: WizardFormData`、`mode: 'create' | 'edit'`、`planId?: string`
- create 模式：标题「新建发送计划」、按钮「创建计划」、调用 completeCreate
- edit 模式：标题「编辑发送计划」、按钮「保存修改」、调用 completeUpdate(planId, ...)
- new/page.tsx 简化为 `<SendPlanWizard mode="create" />`

**Test scenarios:**
- 新建页面功能不变（回归）
- SendPlanWizard 接受 initialData 时各步骤预填数据
- create 模式调用 completeCreate
- edit 模式调用 completeUpdate

**Verification:** `/send-plans/new` 页面功能完整保留

---

### U24. 编辑路由 + 数据加载

**Goal:** 新建编辑页面，加载计划数据

**Requirements:** R10, D6

**Dependencies:** U23

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/edit/page.tsx`（新建）

**Approach:**
- useQuery 加载 plan 详情（`tenantApi.sendingPlans.detail(planId)`）
- useQuery 加载 steps（`tenantApi.sendingPlans.listSteps(planId)`）
- 映射为 WizardFormData：
  - plan: name, description, sender_name, sender_email, domain_id, recipient_source, recipient_config
  - steps: 映射为 StepConfig[]（step_number, template_id, delay_days, condition_type, use_ai_personalization, ai_instructions）
  - lock_recipients: true
- 加载中显示 loading 骨架
- 数据就绪后渲染 `<SendPlanWizard mode="edit" planId={id} initialData={formData} />`

**Test scenarios:**
- 访问 /send-plans/{id}/edit 发起 plan + steps 查询
- 加载中显示 loading 状态
- 数据映射为 WizardFormData 格式正确
- recipient_config 预填（非锁定列表）

**Verification:** 编辑页面加载数据并预填向导

---

### U25. 编辑提交 + 导航

**Goal:** 编辑模式提交调用 complete-update 并导航

**Requirements:** R10, D1

**Dependencies:** U24, U8-U11（后端 complete-update）

**Files:**
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/components/send-plan-wizard.tsx`（修改 mutation 逻辑）

**Approach:**
- edit 模式 mutation 调用 `tenantApi.sendingPlans.completeUpdate(planId!, payload)`
- 成功后 invalidate `['tenant', 'sendingPlans']` + 导航到 `/send-plans/${planId}`
- 错误处理：非 draft 计划后端返回 403 时显示 toast 提示

**Test scenarios:**
- 编辑草稿后提交成功，导航到详情页
- 修改步骤后提交，旧步骤被替换
- 编辑成功后列表页缓存刷新
- 后端 403 时显示错误提示

**Verification:** 编辑 → 提交 → 详情页显示更新后数据 → 列表页也更新

---

## Risks

| 风险 | 影响 | 缓解 |
|------|------|------|
| DataTable 不支持行点击 | 需替换为 Table 组件 | U16 直接用 Table 组件渲染（companies 页面同模式） |
| 向导重构范围 | 提取 SendPlanWizard 可能涉及较多改动 | 最小化：仅提取 props 接口，内部实现整体搬迁 |
| complete-update 与 complete-create 重复 | 维护两份相似代码 | 复用 `_normalize_complete_plan_payload`，UPDATE 部分独立 |
| 后端 mock 测试不验证 SQL 正确性 | mock 测试可能遗漏 SQL 拼接错误 | 实施后端到端手动验证（AGENTS.md 要求） |
| 缓存键修复影响其他页面 | 修改 queryKey 后 invalidation 可能遗漏 | 全局搜索 `sendingPlans` 和 `send-plans` 确认所有引用 |
