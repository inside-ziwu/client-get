## Context

当前数据流：

```
waimaotong_clean_companies ──1:N──▶ waimaotong_clean_contacts（WMT 源表，含邮箱）
        │
        ▼
tenant_companies ──1:N──▶ tenant_contacts（租户私有联系人，发送计划依赖此表）
```

`tenant_contacts` 是发送链路的核心：群组成员（`group_members.tenant_contact_id`）→ 收件人候选 → 发送计划收件人。但该表仅在 `create_company` 手动创建时写入，WMT 批量数据无自动物化路径。

迁移 `20260519_0045` 清空了 `tenant_contacts`，`20260519_0046` 只修复了 `tenant_companies`。结果：公司列表显示 `contacts_count > 0`（WMT 源数据），但实际无可用联系人。

## Goals / Non-Goals

**Goals:**

- 公司加入群组时，自动从 WMT 物化 `tenant_contacts`（lazy materialization）
- 修复 `_recipients_from_group` SQL，确保 fallback 路径也能取到联系人数据
- 一次性数据修复迁移：为已有公司补建缺失的 `tenant_contacts`
- 修正 `data_status` 与实际联系人状态一致
- **发送计划自动群发给公司所有已物化联系人**（1 公司 → N 封邮件，每个有 email 的联系人各一封）

**Non-Goals:**

- 不做全量预物化（eager materialization），避免 `tenant_contacts` 表膨胀
- 不改变 WMT 数据导入流程
- 不处理 `contact_status` 的状态机变更
- 前端改动限于 `list_group_members` 显示联系人数量，不涉及发送计划 UI

## Decisions

### D1：物化策略 — Lazy（按需）而非 Eager（全量预加载）

**选择**: 在 `add_group_members` 和 `_recipients_from_group` 入口处按需物化。

**理由**: WMT 源表可能有数十万家公司，全量预物化会产生大量 `tenant_contacts` 记录，且大部分不会被用到。按需物化只在实际业务需要时创建，资源消耗最小。

**备选**: Eager — 迁移时全量物化。缺点：数据量大、后续新增公司仍需补建、`tenant_contacts` 表急剧膨胀。

### D2：物化入口 — 新增 `_ensure_contacts_from_wmt` 方法

**位置**: 独立异步函数，新建 `backend/app/services/tenant_contact_utils.py`（Eng Review D2：两个 service 都需要调用，提取为零耦合的独立函数）。

**逻辑**:
```
输入: conn, tenant_id, tenant_company_id
1. 查 tenant_contacts 是否已有此公司的记录 → 有则跳过
2. 通过 tenant_companies.clean_company_id → waimaotong_clean_companies.sys_company_id
3. 查 waimaotong_clean_contacts WHERE sys_company_id = ? AND email IS NOT NULL
   ORDER BY (position IS NOT NULL) DESC, id ASC（无上限，全量物化）
4. 批量 INSERT INTO tenant_contacts ... ON CONFLICT DO NOTHING
5. UPDATE tenant_companies SET data_status = 'ready'
   WHERE data_status = 'missing_contacts'
   AND EXISTS (SELECT 1 FROM tenant_contacts WHERE tenant_id = :tenant_id AND clean_company_id = :clean_company_id)
6. 返回创建的数量
```

**调用点**:
- `add_group_members`（tenant_ops_service.py）：在 `_select_default_contact_id` 之前调用
- `_recipients_from_group`（tenant_messaging_service.py）：group 发送查询前，对 group 内各公司触发物化（Eng Review v3 D2：发送时自愈，不依赖 add_group_members 已执行）
- `_recipients_from_manual`（tenant_messaging_service.py）：company_ids 分支查询前调用
- `_recipients_from_filter`（tenant_messaging_service.py）：filter 发送查询前调用（Eng Review v3 D7：纳入 scope）
- 复用现有事务，无额外连接开销

**关键**:
- 步骤 5 必须执行，否则 `_build_recipient_candidates`（tenant_messaging_service.py:1657）会因 `data_status != 'ready'` 将收件人排除为 `excluded_reason = "incomplete"`（Eng Review v1 D1 发现）。
- 步骤 5 用 EXISTS 存在性检查而非 insert count > 0，确保并发安全（Eng Review v2 D6：两个请求同时物化时 ON CONFLICT 可能导致 insert count = 0，但联系人已存在）。
- 步骤 3 排序只用 `(position IS NOT NULL) DESC, id ASC`，因为 WHERE 已过滤 `email IS NOT NULL`（Eng Review v2 D1：去掉冗余的 email 排序项）。

### D3：`_recipients_from_group` SQL 修复

**问题**: lateral fallback `tc_default` 只回退了 `tenant_contact_id`，但 `contact_name` / `contact_email` 仍来自 `tc` → `shc` JOIN 链。

**修复方案**: 将 `tc_default` 扩展为同时返回 `clean_contact_id`，再用 COALESCE 统一取值：

```sql
LEFT JOIN LATERAL (
  SELECT tc_d.id, tc_d.clean_contact_id, tc_d.contact_status
  FROM tenant_contacts tc_d
  WHERE tc_d.tenant_id = :tenant_id
    AND tc_d.clean_company_id = tco.clean_company_id
  ORDER BY tc_d.created_at ASC
  LIMIT 1
) tc_default ON gm.tenant_contact_id IS NULL

-- 统一取值
COALESCE(tc.id, tc_default.id) AS tenant_contact_id
COALESCE(shc.name, shc_default.name) AS contact_name
COALESCE(shc.email, shc_default.email) AS contact_email
COALESCE(tc.contact_status, tc_default.contact_status) AS contact_status
```

新增一个 `shc_default` JOIN：
```sql
LEFT JOIN waimaotong_clean_contacts shc_default
  ON shc_default.id = tc_default.clean_contact_id
```

### D4：数据修复迁移

新增 Alembic revision，执行：

1. **补建 `tenant_contacts`**: 对每个 tenant，找出 `tenant_companies` 关联的 `waimaotong_clean_contacts`（有 email），如果 `tenant_contacts` 中不存在则插入。
2. **修正 `data_status`**: 对 `tenant_contacts` 仍为空的公司设 `data_status = 'missing_contacts'`；有记录的保持 `'ready'`。

**注意**: 不回填 `group_members.tenant_contact_id`（Eng Review v2 D7：LATERAL fallback 已能正确解析 NULL，回填会制造不可逆的语义变更——无法区分"用户主动指定"和"系统自动回填"）。

### D5：`list_group_members` SQL 同步修复

`list_group_members`（`tenant_ops_service.py:636`）与 `_recipients_from_group` 有相同问题——当 `gm.tenant_contact_id = NULL` 时取不到联系人数据。需同步添加 fallback JOIN。

### D6：物化排序策略 — 按 position 优先（全量物化，无上限）

**变更**: 原 D6 有 `LIMIT 10`。范围扩展后改为全量物化（发送计划群发给公司所有联系人），排序仍保留用于 `list_group_members` 默认联系人展示。

**排序策略**:
```sql
WHERE email IS NOT NULL
ORDER BY
  (position IS NOT NULL)::int DESC,     -- 有职位的优先
  id ASC                                 -- 兜底：稳定排序
-- 无 LIMIT，全量物化
```

**理由**: WHERE 已过滤 `email IS NOT NULL`，排序中的 email 判断是冗余的（Eng Review v2 D1）。position 字段有值的联系人通常比无职位的更有价值。排序影响 `tenant_contacts.created_at` 顺序，`list_group_members` 的 fallback 取 `ORDER BY created_at ASC LIMIT 1`，因此排在前面的联系人会成为默认展示联系人。

### D7：`_recipients_from_manual` company_ids 分支 fallback 修复

**问题**: `_recipients_from_manual`（tenant_messaging_service.py:1878）按 `company_ids` 发送时，直接 `JOIN tenant_contacts`。当 `tenant_contacts` 为空时查不到记录，与 `_recipients_from_group` 有相同的 fallback 缺失。

**修复方案**: 简化为 LEFT JOIN + COALESCE（Eng Review v2 D4：company_ids 分支不需要 LATERAL，因为已有 ORDER BY + LIMIT 1 选首个联系人）：

```sql
-- 原: JOIN tenant_contacts tco ON tco.clean_company_id = tc.clean_company_id AND tco.tenant_id = tc.tenant_id
-- 改:
LEFT JOIN tenant_contacts tco
  ON tco.clean_company_id = tc.clean_company_id
 AND tco.tenant_id = tc.tenant_id
LEFT JOIN waimaotong_clean_contacts shc ON shc.id = tco.clean_contact_id

-- 取值用 COALESCE 处理 NULL
COALESCE(tco.id, NULL) AS tenant_contact_id
COALESCE(shc.name, NULL) AS contact_name
COALESCE(shc.email, NULL) AS contact_email
COALESCE(tco.contact_status, NULL) AS contact_status
```

**同时**: 在查询前调用 `ensure_contacts_from_wmt` 确保联系人已物化（从 `tenant_contact_utils.py` import）。

**注意**: `contact_ids` 分支不受影响——该分支直接按 `tenant_contact_id` 查询，前提是 `tenant_contacts` 已存在。

### D8：`_recipients_from_group` 多联系人发送（取代 D3 的 1-per-company 模型）

**变更**: D3 修复的是 LATERAL fallback 取 1 个默认联系人的 bug。范围扩展后，发送链路改为返回公司的**所有**已物化联系人。

**新 SQL**:
```sql
FROM group_members gm
JOIN tenant_companies tco ON tco.id = gm.tenant_company_id
JOIN tenant_contacts tc ON tc.tenant_id = gm.tenant_id
  AND tc.clean_company_id = tco.clean_company_id
JOIN waimaotong_clean_contacts shc ON shc.id = tc.clean_contact_id
WHERE gm.tenant_id = :tenant_id
  AND gm.group_id = :group_id
  AND tco.visibility_status = 'visible'
  AND shc.email IS NOT NULL
```

**关键变化**:
- `gm.tenant_contact_id` 在发送链路中不再使用 — 发给所有联系人，不需要"默认联系人"概念
- 不再需要 LATERAL fallback — 直接 JOIN 所有 `tenant_contacts`
- `shc.email IS NOT NULL` 过滤确保只发给有邮箱的联系人
- 每个 `(company, contact)` 对成为一个独立收件人
- `_build_recipient_candidates` 新增 `is_sendable` 检查（Eng Review v3 D7/Codex：`tenant_contacts.is_sendable` 字段存在但未在发送链路过滤）

**D3 保留用途**: D3 的 LATERAL fallback 方案仍用于 `list_group_members`（D5/D10），但不用于发送。

### D9：`_recipients_from_manual` company_ids 多联系人发送（取代 D7 的 LIMIT 1）

**变更**: D7 将 company_ids 分支从 JOIN 改为 LEFT JOIN + COALESCE + LIMIT 1。范围扩展后，去掉 LIMIT 1，返回所有联系人。

**新 SQL**:
```sql
FROM tenant_companies tc
JOIN waimaotong_clean_companies cc ON cc.id = tc.clean_company_id
JOIN tenant_contacts tco ON tco.clean_company_id = tc.clean_company_id
  AND tco.tenant_id = tc.tenant_id
JOIN waimaotong_clean_contacts shc ON shc.id = tco.clean_contact_id
WHERE tc.tenant_id = :tenant_id
  AND tc.id = ANY(:company_ids)
  AND tc.visibility_status = 'visible'
  AND shc.email IS NOT NULL
```

**关键变化**:
- 使用 JOIN 而非 LEFT JOIN — 无联系人的公司返回 0 行（符合预期：没有联系人就没有收件人）
- 去掉 `ORDER BY ... LIMIT 1` — 返回所有联系人
- 查询前仍调用 `ensure_contacts_from_wmt` 确保联系人已物化

**注意**: `contact_ids` 分支不受影响 — 该分支按具体联系人 ID 查询，语义不变。

### D10：`list_group_members` 显示联系人数量

**行为**: 群组成员列表保持 1 公司 1 行，新增 `contacts_count` 字段。

**SQL 改动**: 在现有查询基础上，新增标量子查询：
```sql
(SELECT COUNT(*)
 FROM tenant_contacts tc_count
 JOIN waimaotong_clean_contacts shc_count ON shc_count.id = tc_count.clean_contact_id
 WHERE tc_count.tenant_id = gm.tenant_id
   AND tc_count.clean_company_id = tco.clean_company_id
   AND shc_count.email IS NOT NULL
) AS contacts_count
```

**D5 LATERAL fallback 保留**: 默认联系人展示仍使用 D3/D5 的 LATERAL fallback 逻辑（取 `created_at ASC LIMIT 1`），`contacts_count` 是额外字段。

**前端**: `list_group_members` 响应新增 `contacts_count` 字段，前端在公司行上展示"N 个联系人"。

### D11：`lock_plan_recipients` 批量 INSERT（Eng Review v3 D5）

**问题**: 当前 `lock_plan_recipients`（tenant_messaging_service.py:743）逐行 INSERT，多联系人场景下 100 公司 × 50 联系人 = 5000 次 round-trip。

**修复方案**: 改为批量 INSERT，一次提交所有非 excluded 候选人：
```sql
INSERT INTO sending_plan_recipients (id, tenant_id, plan_id, tenant_company_id, tenant_contact_id, source_type, source_ref, locked_at, appended_after_start, excluded_at, excluded_reason)
SELECT ...
FROM unnest(:ids, :tenant_ids, :plan_ids, :company_ids, :contact_ids, :source_types, :source_refs)
ON CONFLICT (plan_id, tenant_contact_id) DO NOTHING
RETURNING id
```

**注意**: 用 RETURNING 行数统计真实新增数（修复现有 `inserted += 1` 计数 bug — 当前无论 ON CONFLICT 与否都会递增）。

### D12：`_recipients_from_filter` 多联系人发送（Eng Review v3 D7：从 TODO 纳入 scope）

**问题**: `_recipients_from_filter`（tenant_messaging_service.py:1906）使用 `JOIN tenant_contacts` 且通过 `setdefault` 只取每公司首个联系人。与 D8/D9 同类问题。

**修复方案**: 去掉 `setdefault` 去重逻辑，返回所有联系人；查询前对涉及公司调用 `ensure_contacts_from_wmt`：
```sql
FROM tenant_companies tc
JOIN waimaotong_clean_companies cc ON cc.id = tc.clean_company_id
JOIN tenant_contacts tco ON tco.clean_company_id = tc.clean_company_id
  AND tco.tenant_id = tc.tenant_id
JOIN waimaotong_clean_contacts shc ON shc.id = tco.clean_contact_id
WHERE tc.tenant_id = :tenant_id
  AND tc.visibility_status = 'visible'
  AND shc.email IS NOT NULL
  AND (CAST(:business_status AS text) IS NULL OR tc.business_status = :business_status)
  AND (CAST(:country AS text) IS NULL OR cc.country_iso3 = :country)
```

**注意**: 去掉 Python 层的 `selected.setdefault()` 去重，直接 `return list(rows)`。

### D13：`_build_recipient_candidates` 新增 `is_sendable` 过滤（Eng Review v3 D7/Codex）

**问题**: `tenant_contacts` 表有 `is_sendable` boolean 字段（迁移 20260508_0034），但 `_build_recipient_candidates` 未检查。不可发送的联系人会进入候选列表。

**修复方案**: 在 `_build_recipient_candidates` 的排除逻辑中新增检查：
```python
elif not row.get("is_sendable", True):
    excluded_reason = "not_sendable"
```

**同时**: D8/D9/D12 的 SQL 查询返回列需包含 `tco.is_sendable`。

### D14：`tenant_contact_id` None 字符串修复（Eng Review v3 D7）

**问题**: `_build_recipient_candidates` 中 `str(row["tenant_contact_id"])` 在 `tenant_contact_id` 为 NULL 时输出字符串 `"None"`。

**修复方案**: 改为条件表达式：
```python
"tenant_contact_id": str(row["tenant_contact_id"]) if row["tenant_contact_id"] else None,
```

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 物化时 WMT 表中联系人极多（某公司几百个）→ 全量物化 tenant_contacts 表增长 | lazy 物化只在实际使用时创建；迁移也只为已有 tenant_companies 补建 |
| 迁移执行时间长（公司 × 联系人笛卡尔积） | 迁移用 batch 分批处理，每批 1000 家公司 |
| `_ensure_contacts_from_wmt` 增加 `add_group_members` 延迟（联系人多时 INSERT 量大） | 仅在 `tenant_contacts` 为空时触发，已有记录则一次 COUNT 查询即返回；INSERT 用 ON CONFLICT DO NOTHING 批量执行 |
| 迁移后新导入的 WMT 公司仍可能没有 `tenant_contacts` | lazy 物化在加群组时兜底，不依赖迁移全覆盖 |
| 1 公司 N 封邮件可能导致发送量激增 | `_build_recipient_candidates` 仍逐个检查 blacklist / contact_status / data_status，非 ready 或已退订的自动排除 |
| 用户在群组成员列表看到 1 行但实际发了多封 | D10: 展示 `contacts_count` 让用户知晓实际发送量 |
