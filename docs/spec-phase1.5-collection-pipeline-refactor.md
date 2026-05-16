# Phase 1.5 采集清洗管道重构 Spec

> **本文档记录从"Phase 1 联系人补丁"中剥离出来、决定推迟到 Phase 1.5 单独立项的所有改动**。这些改动多数是 Phase 1 公司清洗管道本来就存在的债务，被联系人改动暴露出来。集中到 Phase 1.5 重构而非散落在多个 PR 里，可以一次性处理 blast radius。

## 1. 背景与定位

Phase 1 的 v1 plan 设想三渠道（外贸通/腾道/励销云）走对称的"采集→清洗→干净"三层管道。但实际代码是：

| 渠道 | raw 表 | cleanup_queue | clean 层 |
|------|--------|--------------|---------|
| 外贸通 | ✓ | ✓ | ✓ → clean_companies |
| 腾道 | ✓ | ❌ 不入队（`tid text` ≠ `raw_row_id bigint`） | ❌ 注释"Cleanup for tendata is Phase 2" |
| 励销云 | ✓ | ✓ 入队但 worker 跳过（`pass`） | ❌ "仅归档"业务设计 |

加上 plan-eng-review + Codex 审查发现的多项管道债务，Phase 1.5 需要集中重构。

## 2. 推迟事项清单（按优先级）

### P0 — 数据正确性（必须修，否则有数据漏洞）

#### 2.1 多租户关联缺口

**问题**：`cleanup_queue` 对 `(raw_table, raw_row_id)` 唯一，重复采集同一家公司时 `DO NOTHING`；同时 `_upsert_*_raw` 不更新 `task_id`。第二个租户采到同一 raw 公司时，不会再触发 `_upsert_tenant_companies`，导致联系人也不关联到该租户。

**影响**：跨租户数据共享场景下，第二个及之后租户拿不到关联

**证据**：`collection_service.py:41` `_upsert_waimaotong_raw` 的 ON CONFLICT 分支不更新 task_id；`alembic/versions/20260430_0009_phase1_collection_schema.py:122` cleanup_queue 唯一约束

**修复方向**：
- 选项 A：cleanup_queue 唯一约束改成 `(raw_table, raw_row_id, task_id)`，每个 task 都触发清洗
- 选项 B：在 raw 入库时维护一个 `(raw_id, task_id)` 关联表，清洗 worker 出队时查所有相关 task
- 选项 C：raw upsert 时 append task_id 到一个数组字段，清洗时 fan-out

#### 2.2 CleanupService 事务设计错误

**问题**：当前 `CleanupService.run` 在一个 `engine.begin()` 里处理整批队列，`_process_one` 捕获异常后还在同一个事务里 `UPDATE cleanup_queue SET status='failed'`。但 Postgres 一旦 SQL 错误事务已 abort，后续 UPDATE 也会失败。**实际效果是整批一起失败、整批一起重试**，不是计划里的"单条失败、单条重试"。

**证据**：`cleanup_service.py:84` `_process_one` + 外层 `engine.begin()`

**修复方向**：每行独立事务（`async with engine.begin() as conn` 在循环内）或 savepoint

#### 2.3 cleanup_queue.raw_row_id 类型迁移

**问题**：腾道主键是 `tid text`，与 `cleanup_queue.raw_row_id bigint` 不兼容，导致腾道根本不入队。改 text 又会破坏多处现有 SQL：

- `admin_collection_service.py:563` 健康检查 `q.raw_row_id = w.id` 会变成 `text = bigint`
- `cleanup_service.py:160` `_load_raw_row` 用 `:id` 参数查 raw 表，类型不匹配
- 腾道分支需要查 `tid` 列（不是 `id`）

**修复**：raw_row_id 改 text 必须同步改至少 3 处现有 SQL

#### 2.4 clean_companies 双唯一索引冲突

**问题**：表上同时有 `UNIQUE(name_normalized, country_iso3)` 和 `UNIQUE(domain) WHERE domain IS NOT NULL`。当前 `_upsert_clean_company` 只 ON CONFLICT 处理 name+country 冲突，**同一 domain、不同名称会直接 INSERT 失败**，不是合并。

**证据**：`alembic/versions/20260430_0009_phase1_collection_schema.py:97-101`

**修复方向**：要么去掉 domain 唯一索引（用应用层去重），要么 upsert 加第二个 ON CONFLICT (domain) 分支

### P1 — 数据规范化（不修会产生脏数据但不立刻崩）

#### 2.5 email 去重未规范化

**问题**：`A@X.com` / `a@x.com` / 带空格的邮箱会被当成三个不同联系人

**修复**：用 `lower(trim(email))` 做唯一索引，或改 `citext` 类型

#### 2.6 raw_contacts 表的去重策略

**问题**：原计划 `UNIQUE(source_contact_id)` 是危险设计——外贸通 contact id 可能为空、跨渠道 id 不稳定

**修复**：改成 `(source_company_id, lower(email))` 唯一约束，source_contact_id 仅作辅助字段保留

#### 2.7 励销云 early persistence 路径绕过路由层

**问题**：`save_competitors_partial` 和 `save_competitor_enriched` 直接调 `_upsert_lixiaoyun_raw`，**不走 `_route_and_enqueue`**。这意味着即使将来励销云联系人有独立 raw 表，这条路径上的联系人也不会入表。

**证据**：`collection_service.py:575-608`

**修复**：early persistence 路径也走 `_route_and_enqueue`，或者在 `_upsert_lixiaoyun_raw` 内部直接处理联系人

### P1 — 三渠道清洗管道补齐

#### 2.8 腾道公司清洗

腾道公司当前不入 cleanup_queue（依赖 2.3 修复），不进 clean_companies。Phase 1.5 需要：

- 腾道 raw → clean_companies
- 腾道丰富字段（`trade_amount_3y_usd`、`trade_count`、`employee_num`、`industry_desc`、`pcb_suppliers`）映射到 clean_companies（需扩字段，或独立 `clean_overseas_buyers` 表）

#### 2.9 励销云公司清洗 + 业务边界分流

励销云抓的是中国本土公司（用于反查海外采购商的供应商），跟外贸通/腾道的"海外采购商"不是同一类业务对象。Phase 1.5 应建独立的 `clean_chinese_companies` 表，物理隔离两个业务池，避免下游营销逻辑误把营销邮件发给中国本土公司。

#### 2.10 三渠道联系人独立 raw 表 + clean 表

- `tendata_raw_contacts`：把当前嵌套在 `tendata_raw_companies.raw_payload.contacts` 的联系人拆出
- `lixiaoyun_raw_contacts`：把当前嵌套在 `lixiaoyun_raw_companies.raw_payload.lx_contacts` 的拆出
- `clean_contacts`：海外采购商联系人（关联 clean_companies）
- `clean_chinese_contacts`：中国供应商联系人（关联 clean_chinese_companies）

**注意 Codex 审查的反对意见**：`clean_chinese_contacts` 用 email 建模可疑——励销云联系人主要是电话/职位，强制 email NOT NULL 会丢失最有用的供应链分析数据。Phase 1.5 实施时需重新讨论：
- 选项 A：`clean_chinese_contacts` 不要求 email NOT NULL，allow phone-only
- 选项 B：`clean_chinese_contacts` 用 phone 作为主键
- 选项 C：不建 `clean_chinese_contacts` 表，励销云联系人只到 raw 层

#### 2.11 联系人合并规则

参考原 plan v2 的设计（已经过审查）：

- 唯一键：(clean_company_id, lower(trim(email)))
- 主记录字段（name/title/phone）保留最新采集时间的非空值
- 历史变体存 `name_history jsonb`，每条含 `observed_at` + `source` 字段
- 硬编码上限 10 条历史快照
- 时间戳判定用 raw_contact.last_seen_at

#### 2.12 联系人合并触发时机

**Codex 审查发现的盲点**：原计划"联系人不入 cleanup_queue，由公司 worker 触发"漏了几个场景：

- 公司已清洗后再补联系人（同任务公司清洗早于联系人采集完成）
- 励销云 partial/enriched 早期落 raw、最终 submit 失败 → 联系人永远不会进 clean

**修复方向**：联系人也入 cleanup_queue，独立 worker 处理；公司清洗时检查关联联系人但不强行同事务

### P2 — 周边一致性

#### 2.13 AdminCollectionService dashboard 统计修正

**问题**：`get_dashboard()` 当前从 `clean_companies.contacts_count` 汇总联系人数。Phase 1.5 加 `clean_contacts` 后，这个字段要么维护、要么改统计 SQL 用 COUNT(*)。

**证据**：`admin_collection_service.py:355`

#### 2.14 真实 DB 集成测试框架

**问题**：当前 `test_phase1_e2e.py` 大量用 MagicMock，抓不到真实 SQL 类型不匹配、唯一索引冲突、事务 abort 等问题（Codex 反复警告）

**修复**：Phase 1.5 必须配套引入真实 DB 集成测试，至少覆盖：
- raw_row_id 类型迁移后所有 SQL 路径
- 跨渠道公司合并的双唯一索引冲突
- 联系人合并的 email 大小写规范化
- 多租户重复采集场景

### P2 — Phase 1 字段清理（推迟而非补丁内做）

#### 2.15 删除已废弃字段

- `waimaotong_raw_companies.emails`：被独立 raw_contacts 表替代后可删
- `tendata_raw_companies.contacts_count`：联系人独立表后可删
- 立小云 `raw_payload.lx_contacts` 嵌套：联系人独立表后可清理冗余

## 3. 实施估算

| 模块 | 估时 |
|------|------|
| 多租户关联修复 (2.1) | 2-3h |
| 事务设计重构 (2.2) | 2h |
| raw_row_id 类型迁移 + SQL 联动改 (2.3) | 3h |
| 双唯一索引处理 (2.4) | 1h |
| email 规范化 + 去重策略 (2.5/2.6) | 2h |
| 励销云路径修复 (2.7) | 1h |
| 腾道清洗 + 字段映射 (2.8) | 3h |
| 励销云独立池 (2.9) | 3h |
| 三渠道联系人 raw + clean 表 (2.10) | 4h |
| 联系人合并规则实现 (2.11) | 3h |
| 联系人合并触发时机 (2.12) | 2h |
| Dashboard 统计修正 (2.13) | 1h |
| 真实 DB 集成测试框架 (2.14) | 4h |
| 字段清理 (2.15) | 0.5h |
| **总计** | **30-35h** |

这是单独立项的工作量，不是补丁。

## 4. 实施前置条件

Phase 1.5 启动前应该：

1. Phase 1 已部署上线，联系人静默丢弃修复（v3 plan）已生效
2. Phase 1 实际跑了一段时间，有真实数据可以验证清洗管道行为
3. 业务方确认 `clean_chinese_contacts` 是否真的需要（参考 Codex 对 email NOT NULL 的反对意见）
4. 决定 `clean_companies` 字段扩展策略 vs `clean_overseas_buyers` 独立表

## 5. 不在 Phase 1.5 范围内

- Phase 2 的 CRM 功能（tenant_contacts、运营状态字段、发送服务等）
- 跨业务边界的合并（外贸通 ↔ 励销云）
- 联系人 → 租户关联（属 Phase 2）

## 6. 来源记录

本 spec 内容来自：

- Phase 1 联系人补丁 plan v2 中决定推迟的扩展项
- plan-eng-review skill 一轮审查的 P0/P1/P2 findings
- Codex outside voice 一轮独立审查发现的 11 个问题

涉及文件：

- `app/services/collection_service.py`
- `app/services/cleanup_service.py`
- `app/services/admin_collection_service.py`
- `app/integrations/collection/{waimaotong,tendata,lixiaoyun}.py`
- `alembic/versions/20260430_0009_phase1_collection_schema.py`
- `tests/test_phase1_e2e.py` 及其他相关测试
