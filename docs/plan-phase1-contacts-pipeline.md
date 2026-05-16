# Phase 1 联系人静默丢弃修复（最小补丁）

> **本计划是 v3，取代 v1/v2**。经过 plan-eng-review + Codex outside voice 两轮审查后，发现原 plan v2 的范围实际等同于"Phase 1 全清洗管道重构"，超出了"部署前补丁"应有的 blast radius。本 v3 把范围严格收敛到"消除联系人静默丢弃这个唯一 bug"，所有结构性改进推迟到 Phase 1.5（见 `spec-phase1.5-collection-pipeline-refactor.md`）。

## 1. Problem Statement

**唯一要修的 bug**：外贸通采集代码取到了联系人，但产出的记录路由到 `target_table: "shared_contacts"`（已被 Phase 1 移除的旧表），最终被 `_route_and_enqueue` 的 `else: pass` 静默丢弃。

**Phase 1 部署后，外贸通的联系人数据会直接丢失。** 这是真正的 P0 阻塞。

腾道和励销云联系人当前嵌套在 `raw_payload.contacts` / `raw_payload.lx_contacts` JSON 里——虽然不规范，但**数据没丢**，不是部署阻塞。

## 2. Scope（最小补丁）

**只做一件事**：让外贸通联系人有地方落，不再静默丢失。

具体改动：

1. 新增 `waimaotong_raw_contacts` 表（采集层归档）
2. 外贸通采集端改路由：`shared_contacts` → `waimaotong_raw_contacts`
3. `_route_and_enqueue` 加 `waimaotong_raw_contacts` 分支
4. `else: pass` 改成 `logger.warning`

**明确不做**（推迟到 Phase 1.5）：

- 腾道 / 励销云联系人独立建表（嵌套现状不丢数据，不是部署阻塞）
- `clean_contacts` 干净联系人表
- 联系人合并/去重逻辑
- 多租户关联缺口修复（cleanup_queue 重复采集 DO NOTHING 问题）
- 事务设计修复（CleanupService 整批 begin 导致异常后 abort 写不进 failed）
- `cleanup_queue.raw_row_id` 类型改造
- `clean_companies` 双唯一索引冲突
- email 规范化（`lower(trim())`）
- 励销云 `save_competitors_partial` 绕过 `_route_and_enqueue` 路径修复
- `AdminCollectionService.get_dashboard` 统计失真
- 真实 DB 集成测试框架

详见 `spec-phase1.5-collection-pipeline-refactor.md`。

## 3. Why minimal scope

Codex outside voice 审查发现 11 个问题，其中至少 8 个是 **Phase 1 公司清洗管道本来就有的债务**，并不是联系人补丁引入的：

- 多租户关联缺口（重复采集 DO NOTHING）
- CleanupService 事务设计错误
- `cleanup_queue.raw_row_id bigint` 主键不能容纳腾道 tid
- `clean_companies` UNIQUE(name_normalized, country_iso3) + UNIQUE(domain) 双索引冲突
- 励销云 early persistence 绕过路由层
- AdminCollectionService dashboard 统计错位
- 测试用 MagicMock 抓不到真实 SQL 问题
- 等等

把这些打包到"联系人补丁"里一起改，PR 会从一张表变成全管道重构，blast radius 失控。

**正确做法**：
- Phase 1 部署前：只修真正阻塞的 bug（联系人静默丢弃）
- Phase 1.5：把所有清洗管道债务集中重构，单独立项

## 4. Implementation

### Step 1: Migration 0012

新增一张表：

```sql
CREATE TABLE waimaotong_raw_contacts (
  id                bigserial PRIMARY KEY,
  source_contact_id text,                  -- 外贸通侧 ID（可空——外贸通字段不保证）
  source_company_id text NOT NULL,         -- 关联 waimaotong_raw_companies.source_id
  name              text,
  title             text,
  email             text NOT NULL,
  phone             text,
  task_id           uuid,
  raw_payload       jsonb,
  created_at        timestamptz DEFAULT now(),
  last_seen_at      timestamptz DEFAULT now()
);
CREATE INDEX idx_wmt_raw_contacts_company ON waimaotong_raw_contacts(source_company_id);
CREATE INDEX idx_wmt_raw_contacts_email_lower ON waimaotong_raw_contacts(lower(email));
```

**设计决策（与 Codex 审查对齐）**：

- **不加 `UNIQUE(source_contact_id)`**：Codex 警告外贸通 contact id 可能为空，强加唯一约束会丢数据
- **不加 `(source_company_id, email)` 唯一约束**：同公司多次采到同 email 先全收，去重逻辑放到 Phase 1.5 的 `clean_contacts` 层
- **email 加 `lower(...)` 索引**：Phase 1.5 做合并时按 lower(email) 查询，先把索引准备好
- **email 是 NOT NULL**：和外贸通采集端的"无 email 过滤"对齐

### Step 2: 采集端 (`waimaotong.py`)

`_build_contacts` 方法改一行：

```python
# 改前
"target_table": "shared_contacts",
# 改后
"target_table": "waimaotong_raw_contacts",
```

字段保持现有（`source_contact_id`, `name`, `title`, `email`, `phone`, `raw_payload`）。现有的无 email 过滤（line 331-332）保留。

### Step 3: 路由层 (`collection_service.py`)

`_route_and_enqueue` 添加分支：

```python
elif target_table == "waimaotong_raw_contacts":
    await self._upsert_waimaotong_raw_contact(conn, task_id, row)
    inserted += 1
else:
    logger.warning("unknown target_table: %s", target_table)
```

新增 `_upsert_waimaotong_raw_contact` 方法（简单 INSERT，不带 ON CONFLICT——同公司同 email 多次采到会产生多行，去重在 Phase 1.5 的 clean 层做）。

### Step 4: 测试

`tests/test_waimaotong.py`：补两条断言

```python
# 验证联系人写入 waimaotong_raw_contacts，不再被丢弃
contacts_count = (await conn.execute(
    text("SELECT count(*) FROM waimaotong_raw_contacts WHERE task_id = :task_id"),
    {"task_id": task_id},
)).scalar_one()
assert contacts_count >= 1

# 验证字段映射正确
contact_row = (await conn.execute(
    text("SELECT name, email, source_company_id FROM waimaotong_raw_contacts WHERE task_id = :task_id LIMIT 1"),
    {"task_id": task_id},
)).mappings().one()
assert contact_row["email"] is not None
assert contact_row["source_company_id"] is not None
```

E2E 测试不动。`test_phase1_e2e.py` 主验证公司清洗链路，联系人不进 clean，无新增场景。

## 5. Technical Constraints

- **不破现有 60 个 Phase 1 测试**：本 plan 改动面只有 1 张新表 + 4 处代码改动，回归风险极低
- **腾道/励销云零改动**：保持嵌套在 raw_payload 的现状，不是 Phase 1 部署阻塞
- **联系人不进 clean 层**：Phase 1 部署后外贸通联系人在 raw 层归档，等 Phase 1.5 实现 `clean_contacts` 后才进干净层

## 6. Success Criteria

- [ ] `alembic current` head = `20260501_0012`
- [ ] `waimaotong_raw_contacts` 表存在
- [ ] 外贸通采集 e2e 后该表有联系人记录
- [ ] `_route_and_enqueue` 不再有 `else: pass` 静默分支
- [ ] 60 个原有 Phase 1 测试全部通过
- [ ] 10 个 Phase 2 skip 测试不变
- [ ] `grep -r "shared_contacts" app/integrations/` 无匹配（外贸通采集端已改）

## 7. CC 估时

~1 小时
- Migration 0012：10 分钟
- waimaotong.py 改 target_table：5 分钟
- collection_service.py 加分支 + 新增 upsert 方法：20 分钟
- 测试断言：15 分钟
- 跑全量测试验证：10 分钟

## 已审决策记录

本 plan 经过 plan-eng-review 一轮 + Codex outside voice 一轮审查：

- **决策**：缩小范围到最小补丁，所有结构性改动推迟到 Phase 1.5
- **理由**：原 v2 plan 的扩张范围实际是"Phase 1 全清洗管道重构"，与"部署前补丁"的 blast radius 不匹配
- **未采纳的扩张项**全部归入 Phase 1.5 spec，不在本 plan 落地
