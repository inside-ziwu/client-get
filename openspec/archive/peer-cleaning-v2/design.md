## Context

codex worktree 里已有清洗系统的完整实现（`peer_company_cleaning_service.py` + `peer_company_backfill_service.py` + migration），但存在三个设计缺陷需要修正后才能合并到主分支。

后端代码位于：`backend/.worktrees/codex/admin-peer-company-cleaning/`
前端页面已存在：`frontend/apps/admin/.../peers-cleaned/page.tsx`（调用的 API 404）

## Goals / Non-Goals

**Goals:**
- 修正清洗规则：非空字段用最新数据覆盖（替代 COALESCE 保留首值）
- 修复 source_id 跨 identity 分裂问题
- 新增 peer_company_contacts 联系人清洗表
- 合并 worktree 代码到主分支、执行 migration、backfill
- API 对齐：移除 health、新增联系人端点
- 前端正确接入

**Non-Goals:**
- 不改原始表结构
- 不做 Tendata 联动

## Decisions

### D1：字段合并策略 — 最新覆盖

将 `_upsert_peer_company` 的 ON CONFLICT SET 从：
```sql
SET name = COALESCE(peer_companies.name, NULLIF(EXCLUDED.name, ''))
```
改为：
```sql
SET name = COALESCE(NULLIF(EXCLUDED.name, ''), peer_companies.name)
```

即：新值非空则覆盖，新值为空则保留。所有 display 字段统一此策略。

`_update_existing_peer_display` 同理。

### D2：source_id 双向复用已有 peer

在 `clean_raw_company()` 中，**不论 derive_identity 返回什么类型**，只要当前 raw 有 source_id，就先查 peer_company_sources 是否已有同 source_id 的 peer：

```python
# clean_raw_company() 内，在 derive_identity 之后、upsert 之前
source_id = str(row.get("source_id") or "").strip()
if source_id:
    existing_peer = await conn.execute(
        "SELECT peer_company_id FROM peer_company_sources WHERE source_id = :sid LIMIT 1",
        {"sid": source_id}
    )
    if existing_peer:
        # 复用已有 peer，走 update 路径（不管当前 identity 是 website_host 还是 source_id）
```

**为什么不仅限 source_id identity**（Eng Review D10）：
- 正向：raw 无 domain（identity=source_id）→ 同 source_id 已有 peer → 复用 ✓
- 反向：raw 有 domain（identity=website_host）→ 同 source_id 已有 peer（由无 domain 的 raw 创建）→ 也复用 ✓
- 原设计只覆盖正向，反向场景仍会分裂

### D3：peer_company_contacts 表

```sql
CREATE TABLE peer_company_contacts (
  id bigserial PRIMARY KEY,
  peer_company_id uuid NOT NULL REFERENCES peer_companies(id) ON DELETE CASCADE,
  email text,
  name text,
  position text,
  phone text,
  mobile text,
  source_contact_id text,
  raw_company_id bigint REFERENCES lixiaoyun_raw_companies(id),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

-- 去重唯一约束：优先 email（规范化），其次 source_contact_id，兜底 name+phone
CREATE UNIQUE INDEX idx_pcc_email ON peer_company_contacts(peer_company_id, lower(trim(email)))
  WHERE email IS NOT NULL AND trim(email) <> '';
CREATE UNIQUE INDEX idx_pcc_source_contact ON peer_company_contacts(peer_company_id, source_contact_id)
  WHERE source_contact_id IS NOT NULL AND source_contact_id <> ''
    AND (email IS NULL OR trim(email) = '');
CREATE UNIQUE INDEX idx_pcc_name_phone ON peer_company_contacts(peer_company_id, name, COALESCE(phone, ''))
  WHERE (email IS NULL OR trim(email) = '')
    AND (source_contact_id IS NULL OR source_contact_id = '');
```

**清洗实现**（Eng Review D3）：两步 upsert，非纯 INSERT ON CONFLICT：
1. 先按 (peer_company_id, source_contact_id) 查已有行——如果存在且新数据有 email，UPDATE 补上 email
2. 否则 INSERT ON CONFLICT DO UPDATE，字段用 D1 相同策略

**规范化**（Eng Review D11）：email 在插入前做 `lower(trim())`，phone 用 `COALESCE(phone, '')` 参与唯一约束。

### D3.1：DRY — _build_display_set_clause（Eng Review D7）

提取 `_build_display_set_clause()` 方法，统一生成 11 个字段的合并 SQL 片段。`_upsert_peer_company` 和 `_update_existing_peer_display` 都使用该 helper，确保合并策略一致。

### D3.2：backfill 批量事务（Eng Review D5）

backfill 改为每 500 条 raw 一个事务，记录 last_processed_id 支持断点续传。需要 runner 脚本负责循环调用和 commit。`upsert_contacts` 改为 True。

### D4：API 端点

| 操作 | 端点 |
|---|---|
| 移除 | `GET /collection/peer-companies/health` |
| 保留 | `GET /collection/peer-companies` |
| 保留 | `GET /collection/peer-companies/{id}` |
| 新增 | `GET /collection/peer-companies/{id}/contacts` |

联系人端点查 `peer_company_contacts WHERE peer_company_id = :id`，直接返回。

### D5：合并与部署顺序

1. 将 worktree 代码复制到主分支 backend/
2. 在主分支上做本次修改（D1-D4）
3. 执行 migration（建 peer_companies + peer_company_keywords + peer_company_sources + peer_company_contacts）
4. 运行 backfill（dry_run 先看数据，再正式跑）
5. 部署后端
6. 部署前端

## Risks / Trade-offs

- 条件唯一索引（D3）比单一唯一约束复杂，但这是三级去重键的必要代价
- 两步 upsert 比纯 INSERT ON CONFLICT 多一次查询，但解决了"升级"场景的重复问题
- 最新覆盖策略（D1）意味着后采集的数据优先，如果后面的数据质量更差会覆盖好数据——但与用户确认过这是期望行为
- "最新"由 raw id ASC 顺序决定（= 入库时间），对于励销云数据源这个假设成立
- backfill 批量事务（500/批）牺牲全局原子性换取短锁占和断点续传
