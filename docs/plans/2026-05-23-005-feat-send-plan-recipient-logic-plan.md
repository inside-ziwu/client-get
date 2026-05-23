---
title: "feat: 发送计划收件人逻辑优化（分类排序 + 每公司8人上限 + 按公司预览）"
type: feat
status: active
date: 2026-05-23
origin: docs/brainstorms/2026-05-23-send-plan-recipient-logic-requirements.md
depth: standard
execution_posture: tdd
---

# feat: 发送计划收件人逻辑优化（分类排序 + 每公司8人上限 + 按公司预览）

## Summary

修改 `_recipients_from_group()` SQL，LEFT JOIN 联系人分类视图，在 SQL 层排除无效联系人并按 `(company, email)` 去重后，用 `ROW_NUMBER() OVER (PARTITION BY company)` 限制每公司最多 8 人。新增 `preview-recipients` API 端点复用同一逻辑，返回按公司分组的结果。前端群组选择器从"人"改为"家公司"，预览改为按公司汇总可展开的表格。

**执行姿态：TDD 测试驱动**。后端每个行为先写 pytest 测试再实现；每个执行单元 2-5 分钟可完成一个 RED→GREEN 周期。

---

## Problem Frame

群组选择器显示"14 人"但实际是 14 家公司；收件人选取未接入 admin 联系人分类等级体系（A/B/X + is_sendable），无排序无限数；预览路径（listMembers）和实际发送路径（_recipients_from_group）逻辑不一致。(see origin: `docs/brainstorms/2026-05-23-send-plan-recipient-logic-requirements.md`)

---

## Requirements

- R1. 群组选择器中显示"X 家公司"而非"X 人"
- R2. 收件人预览底部合计显示"合计 X 家公司，Y 位收件人"
- R3. 每家公司收件人按 admin 联系人分类等级 sort_order 从高到低排序，仅取 is_sendable=true 的等级，取前 8 个有邮箱联系人
- R4. 未匹配到分类等级的联系人排最后但仍可入选
- R5. 每家公司收件人不超过 8 人
- R6. 预览按公司汇总，每公司一行标注收件人数量
- R7. 公司行可展开查看明细（姓名、邮箱、分类等级）

**Origin acceptance examples:** AE1 (covers R3, R4), AE2 (covers R3, R5), AE3 (covers R1)

---

## Scope Boundaries

- 不修改手动选择和筛选器两种收件人来源
- 不修改 admin 联系人分类规则本身
- 不修改邮件实际发送流程
- 不重构 `_build_recipient_candidates()` 的排除过滤结构（blacklist/unsubscribed/bounced 等保持原样）

### Deferred to Follow-Up Work

- 前端组件测试：本次不为前端改动写 vitest 测试
- `tenant_contacts.is_sendable` 字段处理：若生产数据检查发现该字段有 false 记录，需单独评估是否兼顾

---

## Context & Research

### Relevant Code and Patterns

- `backend/app/services/tenant_messaging_service.py`：`_recipients_from_group()` (line 2003)，`_build_recipient_candidates()` (line 1818)，`preview_plan_recipients()` (line 871)，`_load_blacklist()` (line 2140)
- `backend/app/api/tenant/messaging.py`：路由文件，`/sending-plans/{plan_id}/recipients/preview` 已有先例 (line 321)
- `backend/tests/test_sending_plan_routes.py`：路由层 mock 测试模式——`create_app()` + `dependency_overrides` + `httpx.AsyncClient`
- `backend/tests/test_sending_plan_complete_update.py`：service 层 mock 测试模式——直接实例化 service + `patch.object` mock 内部方法
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-recipients.tsx`：当前预览用 `tenantApi.groups.listMembers`
- `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-confirmation.tsx`：从 React Query 缓存读 groups 数据显示 member_count
- `frontend/packages/shared-api/src/tenant/sending-plans.ts`：sendingPlansApi，已有 `previewRecipients(planId)` 方法
- `frontend/packages/shared-api/src/tenant/groups.ts`：Group 类型定义，member_count 字段
- `backend/03_database/schema.sql` line 1439：`v_tenant_contact_classified` 视图（JOIN LATERAL + LIMIT 1，仅匹配到关键词的联系人有行）
- `backend/03_database/schema.sql` line 1408：`position_classification_levels` 表（sort_order, is_sendable）

---

## Key Technical Decisions

| ID | 决策 | 理由 |
|----|------|------|
| D1 | 修改 `_recipients_from_group()` 而非新建方法 | 唯一入口，修改即同时影响预览和实际发送 (see origin: design.md D1) |
| D2 | 排除过滤在 SQL 层 ROW_NUMBER 之前完成 | 确保每公司 8 人名额全部有效，不会先取 8 再排除 (工程审查 override) |
| D3 | 按 `(tenant_company_id, email)` 去重后再 ROW_NUMBER | 防止同一邮箱多条记录占用名额 (Codex 审查补充) |
| D4 | `is_sendable` 取自 `position_classification_levels` 而非 `tenant_contacts` | 后者无 UI 配置入口且全部默认 true (see origin: design.md D4) |
| D5 | 新增 `GET /sending-plans/preview-recipients?group_id=` 端点 | 创建前无 plan_id，不能用已有 `/{plan_id}/recipients/preview` |

---

## Open Questions

### Resolved During Planning

- `member_count` 是否需要修改计算逻辑：不需要，`_refresh_group_member_count()` 已经是 COUNT group_members 行 = 公司数，仅改前端显示文本

### Deferred to Implementation

- 生产环境是否存在 `tenant_contacts.is_sendable = false` 记录：U1 前置检查确认，结果决定是否需要在 SQL 中兼顾该字段

---

## High-Level Technical Design

> *This illustrates the intended approach and is directional guidance for review, not implementation specification. The implementing agent should treat it as context, not code to reproduce.*

```
_recipients_from_group() SQL 改造思路:

WITH candidates AS (
  -- 现有 JOIN 链: group_members → tenant_companies → tenant_contacts → clean_companies → clean_contacts
  -- 新增 LEFT JOIN: v_tenant_contact_classified → position_classification_levels
  -- WHERE 排除: 无邮箱、unsubscribed、bounced、data_status != ready、黑名单
  -- 按 (tenant_company_id, email) 去重: 保留等级最高记录 (DISTINCT ON 或子查询)
),
ranked AS (
  SELECT *, ROW_NUMBER() OVER (
    PARTITION BY tenant_company_id
    ORDER BY pcl_is_sendable DESC NULLS LAST,
             pcl_sort_order DESC NULLS LAST,
             contact_id ASC
  ) AS rn
  FROM candidates
  WHERE pcl_is_sendable IS DISTINCT FROM false  -- 排除 X 级
)
SELECT * FROM ranked WHERE rn <= 8
```

---

## Sequencing

```
Phase A: 后端核心逻辑 (U1-U5)
    ↓
Phase B: 后端预览 API (U6-U8)
    ↓
Phase C: 前端改造 (U9-U13)
```

Phase A 各单元严格顺序（SQL 改造需逐步叠加测试）。Phase B 依赖 Phase A。Phase C 依赖 Phase B。

---

## Implementation Units

### Phase A: 后端核心逻辑

### U1. 前置检查：生产数据 is_sendable 确认

**Goal:** 确认生产环境中是否存在 `tenant_contacts.is_sendable = false` 的记录，决定新 SQL 是否需要兼顾该字段

**Requirements:** D4 前置条件

**Dependencies:** 无

**Files:**
- 无代码变更

**Approach:**
- 在 dev 数据库执行 `SELECT COUNT(*) FROM tenant_contacts WHERE is_sendable = false`
- 如果结果为 0：按计划进行，完全改用 `position_classification_levels.is_sendable`
- 如果结果 > 0：在 U3 的 SQL 中增加 `AND tc.is_sendable IS NOT false` 条件

**Test scenarios:**
- Test expectation: none — 纯数据查询，无代码变更

**Verification:** 查询结果记录在 change 目录下，后续 SQL 编写基于此结果

---

### U2. 测试：_recipients_from_group 等级排序（RED）

**Goal:** 为分类等级排序逻辑编写失败测试

**Requirements:** R3, R4

**Dependencies:** U1

**Files:**
- Create: `backend/tests/test_recipient_selection.py`

**Approach:**
- RED：新建测试文件，直接实例化 `TenantMessagingService`
- Mock `conn.execute` 返回预设行（模拟 SQL 结果），或 `patch.object` mock `_recipients_from_group` 的内部查询
- 参照 `test_sending_plan_complete_update.py` 的 service 层 mock 模式
- 测试用例覆盖 AE1 场景：12 个联系人混合等级

**Execution note:** 仅写测试，不修改实现。此测试目前会失败（当前 SQL 无排序无限数）。

**Patterns to follow:** `backend/tests/test_sending_plan_complete_update.py` — service 实例化 + AsyncMock conn + patch.object

**Test scenarios:**
- Happy path: 混合等级（3A + 4B + 2X + 3未分类），期望返回 3A → 4B → 1未分类 = 8人，X级被排除（Covers AE1）
- Happy path: 不足8人全部入选，5个B级联系人全部返回（Covers AE2）
- Edge case: 全部未分类，10人取前8
- Edge case: 全部 is_sendable=false，返回0人

**Verification:** 测试文件存在且可运行（全部 FAIL 是预期的）

---

### U3. 实现：_recipients_from_group SQL 改造（GREEN）

**Goal:** 修改 SQL 加入分类 LEFT JOIN + 排除过滤 + 邮箱去重 + ROW_NUMBER 限8人

**Requirements:** R3, R4, R5

**Dependencies:** U2

**Files:**
- Modify: `backend/app/services/tenant_messaging_service.py`（`_recipients_from_group` 方法）

**Approach:**
- 在现有 SQL 基础上新增两个 LEFT JOIN（`v_tenant_contact_classified` 和 `position_classification_levels`）
- 用 CTE 分层：第一层做排除过滤（is_sendable=false、无邮箱已在 WHERE 处理，blacklist 用子查询排除），按 `(tenant_company_id, email)` 去重
- 第二层加 `ROW_NUMBER() OVER (PARTITION BY tenant_company_id ORDER BY pcl.is_sendable DESC NULLS LAST, pcl.sort_order DESC NULLS LAST, shc.id ASC)`
- 外层 `WHERE rn <= 8`
- 返回行新增 `level_display_name` 字段（`pcl.display_name`）
- `is_sendable` 字段改为 `COALESCE(pcl.is_sendable, true)`

**Patterns to follow:** 现有 `_recipients_from_group` 的 JOIN 链结构

**Test scenarios:**
- 无新测试——U2 测试变绿

**Verification:** `pytest backend/tests/test_recipient_selection.py -v` 全部通过

---

### U4. 测试+实现：邮箱去重逻辑

**Goal:** 同一公司下同一邮箱多条记录只保留等级最高的一条

**Requirements:** R5, D3

**Dependencies:** U3

**Files:**
- Modify: `backend/tests/test_recipient_selection.py`（追加测试）
- Modify: `backend/app/services/tenant_messaging_service.py`（如 U3 未完全覆盖）

**Approach:**
- RED：追加测试——某公司有3个联系人，其中2个邮箱相同（一个A级一个B级），期望去重后只保留A级那条
- GREEN：确认 U3 的 `DISTINCT ON (tenant_company_id, email)` 或等价去重逻辑生效

**Test scenarios:**
- Happy path: 同一公司2条记录同一邮箱（A级 + B级），去重后保留A级
- Edge case: 同一公司3条记录同一邮箱（A级 + B级 + 未分类），去重后保留A级
- Edge case: 不同公司同一邮箱不去重（各自保留）

**Verification:** 全部测试通过

---

### U5. 测试+实现：_build_recipient_candidates 排除过滤适配

**Goal:** 确保 `_build_recipient_candidates` 的 Python 层排除过滤与新 SQL 返回字段兼容

**Requirements:** R3

**Dependencies:** U3

**Files:**
- Modify: `backend/tests/test_recipient_selection.py`（追加）
- Modify: `backend/app/services/tenant_messaging_service.py`（`_build_recipient_candidates` 如需微调）

**Approach:**
- RED：测试整个 `_build_recipient_candidates` 调用链——mock `_recipients_from_group` 返回新格式行（含 `level_display_name`、新 `is_sendable` 来源），断言 candidates 结构正确
- GREEN：确保 `_build_recipient_candidates` 对新字段的 dict key 取值无 KeyError
- `is_sendable` 字段已在 SQL 中改为取自 `position_classification_levels`，Python 层 `row.get("is_sendable", True)` 逻辑应仍然兼容

**Test scenarios:**
- Happy path: 新格式行传入 _build_recipient_candidates，输出 candidates 包含 company_name、contact_email、excluded_reason 等字段
- Edge case: blacklisted 公司的行被标记为 excluded_reason="blacklisted"
- Integration: 从 _recipients_from_group mock → _build_recipient_candidates → 输出候选人列表，验证完整调用链

**Verification:** 全部测试通过

---

### Phase B: 后端预览 API

### U6. 测试+实现：preview_recipients_for_group 方法

**Goal:** 新增 service 方法，调用 `_build_recipient_candidates` 并按公司分组返回

**Requirements:** R6, R2

**Dependencies:** U5

**Files:**
- Modify: `backend/tests/test_recipient_selection.py`（追加）
- Modify: `backend/app/services/tenant_messaging_service.py`（新增方法）

**Approach:**
- RED：测试调用 `preview_recipients_for_group(conn, tenant_id, group_id)`，mock `_build_recipient_candidates` 返回多条候选人（含不同公司），断言返回 `{ companies: [...], summary: { company_count, recipient_count } }` 结构
- GREEN：新增方法，内部调用 `_build_recipient_candidates(conn, tenant_id=tenant_id, recipient_source="group", recipient_config={"group_id": group_id})`
- 按 `tenant_company_id` 分组，统计每公司 recipient_count（excluded_reason 为 None 的才计入）
- 返回 summary 聚合

**Test scenarios:**
- Happy path: 3家公司共10条候选人，按公司分组后 summary 正确
- Edge case: 某公司全部被排除（excluded_reason 非 None），该公司 recipient_count=0 但仍在 companies 列表中
- Edge case: 空群组（0条候选人），返回 companies=[], summary={company_count:0, recipient_count:0}

**Verification:** 全部测试通过

---

### U7. 测试+实现：preview_recipients_for_group 群组校验

**Goal:** 群组不存在或不属于当前租户时返回 422

**Requirements:** spec 场景"群组不存在"

**Dependencies:** U6

**Files:**
- Modify: `backend/tests/test_recipient_selection.py`（追加）
- Modify: `backend/app/services/tenant_messaging_service.py`（在新方法开头调用 `_validate_group_ownership`）

**Approach:**
- RED：测试传入无效 group_id，断言抛出 AppError(status_code=422)
- GREEN：在 `preview_recipients_for_group` 开头调用已有的 `_validate_group_ownership(conn, tenant_id, group_id)`

**Test scenarios:**
- Error path: 无效 group_id → 422
- Error path: 有效 group_id 但不属于当前 tenant → 422

**Verification:** 全部测试通过

---

### U8. 测试+实现：preview-recipients 路由

**Goal:** 新增 `GET /sending-plans/preview-recipients?group_id=` 路由

**Requirements:** D5

**Dependencies:** U6

**Files:**
- Modify: `backend/tests/test_recipient_selection.py`（追加路由测试）
- Modify: `backend/app/api/tenant/messaging.py`（新增路由）

**Approach:**
- RED：参照 `test_sending_plan_routes.py` 的模式，mock service 方法，测试 GET 请求带 `group_id` 参数返回 200 和正确结构
- GREEN：在 messaging.py 添加路由，接收 `group_id: str = Query(...)` 参数，调用 `service.preview_recipients_for_group`

**Patterns to follow:** `backend/tests/test_sending_plan_routes.py` — `create_app()` + `dependency_overrides` + `httpx.AsyncClient`；`backend/app/api/tenant/messaging.py` line 321 现有 preview 路由

**Test scenarios:**
- Happy path: GET /sending-plans/preview-recipients?group_id=valid-id → 200 + 正确 JSON 结构
- Error path: 缺少 group_id 参数 → 422
- Error path: 无效 group_id → 422（由 service 层抛出）

**Verification:** `pytest backend/tests/test_recipient_selection.py -v` 全部通过

---

### Phase C: 前端改造

### U9. 新增 preview-recipients API 类型和调用方法

**Goal:** 在 shared-api 添加新 API 端点的类型定义和调用方法

**Requirements:** R6, R7

**Dependencies:** U8

**Files:**
- Modify: `frontend/packages/shared-api/src/tenant/sending-plans.ts`（新增类型和方法）

**Approach:**
- 新增 `PreviewRecipientCompany` 和 `PreviewRecipientsSummary` 类型
- 在 `sendingPlansApi` 中新增 `previewGroupRecipients(groupId: string)` 方法，调用 `GET /sending-plans/preview-recipients?group_id=`

**Test scenarios:**
- Test expectation: none — 纯类型定义和 API 调用封装，无业务逻辑

**Verification:** TypeScript 编译无错误

---

### U10. 群组选择器文本改为"家公司"

**Goal:** 群组选择器下拉项从"X 人"改为"X 家公司"

**Requirements:** R1

**Dependencies:** 无（前端独立改动）

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-recipients.tsx`（line 70）

**Approach:**
- 将 `{g.member_count} 人` 改为 `{g.member_count} 家公司`
- `member_count` 已经是公司计数（`_refresh_group_member_count` COUNT group_members 行），无需后端改动

**Test scenarios:**
- Test expectation: none — 纯文本替换

**Verification:** 启动 dev server，打开群组选择器确认显示"X 家公司"（Covers AE3）

---

### U11. 预览改为调用 preview-recipients API + 按公司汇总

**Goal:** 预览表格改为调用新 API，按公司汇总展示，支持展开明细

**Requirements:** R2, R6, R7

**Dependencies:** U9

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-recipients.tsx`

**Approach:**
- 替换 `membersQuery` 的 queryFn 为 `tenantApi.sendingPlans.previewGroupRecipients(selectedGroupId)`
- 更新 queryKey 为 `['tenant', 'sendingPlans', 'previewRecipients', selectedGroupId]`
- 表格改为按公司汇总：每行显示公司名 + 收件人数量
- 添加展开/折叠状态（useState），点击公司行展开显示明细（姓名、邮箱、分类等级）
- 底部合计改为"合计 X 家公司，Y 位收件人"（取自 summary 字段）

**Test scenarios:**
- Test expectation: none — 前端 UI 改造，手动验证

**Verification:** dev server 中选择群组后，预览显示按公司汇总，可展开明细，底部合计格式正确

---

### U12. 确认步骤收件人数显示更新

**Goal:** 确认步骤"预估收件人数"从 `member_count 人` 改为从预览 API 的 summary 数据获取

**Requirements:** R2

**Dependencies:** U11

**Files:**
- Modify: `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/step-confirmation.tsx`（line 91）

**Approach:**
- 从 React Query 缓存读取 preview-recipients 的 summary 数据（queryKey 与 U11 一致）
- 将"预估收件人数"显示改为 `${summary.company_count} 家公司，${summary.recipient_count} 位收件人`
- 如果缓存无数据（未到过步骤3），回退显示 `${selectedGroup.member_count} 家公司`

**Test scenarios:**
- Test expectation: none — 前端显示逻辑改动，手动验证

**Verification:** 创建发送计划到步骤4，确认显示"X 家公司，Y 位收件人"

---

### U13. 端到端验证

**Goal:** 全流程手动验证

**Requirements:** R1-R7, AE1-AE3

**Dependencies:** U12

**Files:**
- 无代码变更

**Approach:**
- 启动 dev server，创建发送计划完整走一遍步骤 1→2→3→4
- 验证：群组选择器显示"X 家公司"、预览按公司汇总、展开明细正确、合计格式正确、确认步骤显示正确
- 边界场景：选择包含未分类联系人公司的群组、包含超过8人公司的群组

**Test scenarios:**
- Test expectation: none — 手动端到端验证

**Verification:** 全流程无异常，AE1/AE2/AE3 场景验证通过

---

## System-Wide Impact

- **Interaction graph:** `_recipients_from_group()` 被 `_build_recipient_candidates()` 调用，后者有 3 个调用方——`preview_plan_recipients`（已有计划预览）、`complete_plan`（创建计划）、另一个创建流程。SQL 改造影响所有 3 条路径，这是期望行为（统一逻辑）
- **Error propagation:** 新增路由层面的 422 错误（群组不存在）；SQL 层面错误通过现有 SQLAlchemy 异常处理链上报
- **API surface parity:** 新增 `GET /sending-plans/preview-recipients?group_id=` 与现有 `GET /sending-plans/{plan_id}/recipients/preview` 并存。前者用于创建前，后者用于已有计划
- **Unchanged invariants:** 手动选择和筛选器两种收件人来源的 `_recipients_from_manual` / `_recipients_from_filter` 不受影响；`_build_recipient_candidates` 的排除过滤逻辑（blacklist/unsubscribed/bounced 等）保持原样

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| `v_tenant_contact_classified` LATERAL JOIN 视图对大量联系人查询慢 | 当前业务规模可接受；视图仅匹配有 position 的联系人，LIMIT 1 控制匹配次数 |
| 生产环境存在 `tenant_contacts.is_sendable = false` 记录 | U1 前置检查确认，结果决定 SQL 是否需要兼顾 |
| 修改 `_recipients_from_group` 影响已有计划的 preview 和 complete 流程 | 这是期望行为（统一逻辑）；后端测试覆盖核心路径 |

---

## Sources & References

- **Origin document:** [docs/brainstorms/2026-05-23-send-plan-recipient-logic-requirements.md](docs/brainstorms/2026-05-23-send-plan-recipient-logic-requirements.md)
- **Design document:** [openspec/changes/send-plan-recipient-logic/design.md](openspec/changes/send-plan-recipient-logic/design.md)
- **Spec document:** [openspec/changes/send-plan-recipient-logic/specs/recipient-selection-by-level/spec.md](openspec/changes/send-plan-recipient-logic/specs/recipient-selection-by-level/spec.md)
- **Tasks document:** [openspec/changes/send-plan-recipient-logic/tasks.md](openspec/changes/send-plan-recipient-logic/tasks.md)
- Related test patterns: `backend/tests/test_sending_plan_routes.py`, `backend/tests/test_sending_plan_complete_update.py`
