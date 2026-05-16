# v3-data-foundation 现状调研（起草 design.md 前置）

> 调研日期：2026-05-06
> 调研者：Explore subagent（read-only）
> 用途：v3-data-foundation/design.md 架构决策依据

## A. Alembic 迁移现状（0007-0013）

### 完整迁移链

```
0001 → 0002 → 0003 (scoring_jobs) → 0004 → 0005 → 0006
→ 0007 (collection_task_type) → 0008 (competitor_enrichment)
→ 0009 (phase1_collection_schema) → 0010 (default_partitions)
→ 0011 (drop_ai_pricing) → 0012 (waimaotong_raw_contacts) → 0013 (drop_ai_fallback)
```

### 0009 phase1_collection_schema 详情

**新建 5 张表**：
- `waimaotong_raw_companies` (bigserial PK，13 字段)
- `tendata_raw_companies` (text PK: tid，19 字段)
- `lixiaoyun_raw_companies` (bigserial PK，11 字段)
- **`clean_companies` (bigserial PK)** — name_normalized + name_display + country_iso3 + domain + industry + products + contacts_count + sources(array) + last_updated；UNIQUE(name_normalized, country_iso3)
- **`cleanup_queue` (bigserial PK)** — raw_table + raw_row_id + status(enum) + attempts + last_error；UNIQUE(raw_table, raw_row_id)

**新建函数**：`normalize_company_name()`（IMMUTABLE，去后缀 LLC/LTD/MFG 等 + 空格合并）

**改造 collection_keywords**：
- 删除：source_types / countries / countries_hash
- 新增 40 字段：subscription_status / stage1+stage2 计数 / daily_limit / error_msg / started_at
- 约束：UNIQUE (tenant_id, keyword_normalized) ← 替代旧 (tenant_id, keyword_normalized, countries_hash)

### B-2 已知漂移

| 项 | 说明 |
|---|---|
| F1 | `backend/app/models/` 是空目录（无 ORM 模型层） |
| F2 | `scoring_jobs`（迁移 0003）/ `waimaotong_raw_contacts`（迁移 0012）未回写 schema.sql |

---

## B. Cleanup 服务现状

### B.1 ✅ cleanup_service.py 已存在（286 行）

路径：`backend/app/services/cleanup_service.py`

**核心设计**：
1. **轮询消费 cleanup_queue**（_POLL_INTERVAL=1.5s, BATCH_SIZE=100）
2. **FOR UPDATE SKIP LOCKED**（多 worker 防争用）
3. **重试 3 次**（_MAX_ATTEMPTS=3, last_error 截断 500 字符）
4. **5 分钟重置失败行**（_reset_retryable_failures：failed → pending if attempts<3）
5. **清洗流程**：
   - waimaotong/tendata → `_clean_and_link()` UPSERT clean_companies → UPSERT tenant_companies
   - **lixiaoyun 跳过清洗**（直接标 done，"不入 clean"）
6. **去重**：normalize_company_name() + UPSERT ON CONFLICT (name_normalized, country_iso3)

### B.2 缺陷

- 🟡 lixiaoyun 业务流不明（代码注释含糊）
- 🟡 无死信队列（failed 仅日志）
- 🟡 无幂等保护（重复入队会重复处理）

---

## C. 4 Worker 现状

| Worker | 文件 | Lease | 心跳 | 幂等键 | Retry | 异常处理 |
|---|---|:-:|:-:|:-:|---|---|
| **collection** | collection.py（133 行）| ✅ | ✅ | ✅ request_id | 上层 | AppError + Exception |
| **collection_scheduler** | collection_scheduler.py（24 行）| ⚠️ 仅 recover | ❌ | ❌ | ❌ | ❌ 极简 |
| **scoring** | scoring.py（66 行）| ✅ | ❌ | ❌ | 细粒度 retryable | NOT_FOUND→不重试 / 其他→重试 |
| **sending** | sending.py（73 行）| ❌（一次完成）| ❌ | ✅ idempotency_key=email_id | 统一失败 | EngageLabSendError + Exception |

**结论**：collection / scoring 已有 lease 模式可作 base class 雏形；scheduler / sending 未对齐。

---

## D. Schema 现状（生产 vs 0009 设计）

### D.1 raw_* 表

| 表 | 0009 设计 | schema.sql | 生产 |
|---|:-:|:-:|:-:|
| waimaotong_raw_companies | ✅ | ❌ | ❌（0009 未跑）|
| tendata_raw_companies | ✅ | ❌ | ❌ |
| lixiaoyun_raw_companies | ✅ | ❌ | ❌ |
| waimaotong_raw_contacts | ✅（0012）| ❌ | ❌ |

### D.2 ⚠️ clean_companies vs shared_companies 分歧

| 项 | 0009 设计 clean_companies | schema.sql shared_companies |
|---|---|---|
| 主键 | bigserial | UUID |
| 来源记录 | sources(array) 内联 | 独立 company_sources 表（多对一）|
| 字段量 | 简单（10 字段）| 丰富（30+ 字段）|
| 含字段示例 | name_normalized / country_iso3 / domain | name / name_en / region / city / website / industry_tags / employee_count / annual_revenue / data_completeness |
| cleanup_service 当前用 | 硬编码 clean_companies | 不用 |

**结论**：0009 downgrade() 会恢复到 shared_companies（说明历史演进经历）。

### D.3 cleanup_queue

- 0009 设计：✅
- schema.sql：❌
- 生产：❌

### D.4 推断生产迁移状态

**证据链**：3 张 raw 表 + cleanup_queue + waimaotong_raw_contacts 全缺 → **生产停在 0006 或更早**

---

## E. 起草 design.md 的 3 个架构方案

### 方案 A：恢复 0009 设计（clean_companies）

```
保留：clean_companies (bigserial) + cleanup_queue + 3 raw 表
弃用：shared_companies + company_sources
```

✅ cleanup_service 代码已对齐
✅ 简单（清洗规则少）
❌ shared_companies 30+ 字段全废（含 D-038 用到的 employee_count / annual_revenue / industry_tags）
❌ 需要重写 D-038 9 字段 + D-039 2 字段映射逻辑（在 clean_companies 上加 11 字段）
❌ 已上线的 shared_companies 数据（如有）需迁移
**工作量**：重新加 11 字段 + 重写 cleanup_service 字段逻辑 + downgrade

### 方案 B：基于 shared_companies 重设计（推荐）

```
保留：shared_companies (UUID) + company_sources（多源映射）
改造：cleanup_service 改用 shared_companies + company_sources
新建：cleanup_queue（沿用 0009 设计）+ 3 raw 表（沿用 0009）
shared_companies 加 D-038/D-039 缺的字段
```

✅ shared_companies 已含 D-038 大部分字段（country / industry_tags / employee_count / annual_revenue 等都对得上）
✅ 多源映射（company_sources）更规范，符合 §5.2 跨源合并
✅ 业务上线后 shared_companies 数据保留
❌ cleanup_service 需改约 50-100 行（改用 shared_companies + 新增 company_sources 写入）
❌ 需要起草迁移：从 0009 设计的 clean_companies 切换到 shared_companies 模型（或废弃 0009 重写新迁移）
**工作量**：改 cleanup_service + 写新迁移（替代 0009 部分）+ shared_companies 加少数字段

### 方案 C：混合（不推荐）

```
保留 shared_companies + 加 raw 表 + 无 cleanup_queue（流式 / 定时任务）
```

❌ 违反 D-008-B 决策（明确要 cleanup_service worker + queue）
❌ 失去重试 / 幂等 / 监控的队列优势

---

## F. 关键决策点（design.md 必答）

1. **架构方案 A / B / C**（最大决策）
2. **lixiaoyun 业务流**：cleanup_service 现行"跳过清洗直接标 done"是否符合 V3 业务（business-goals §5.2 "励销云不入干净库"）？
3. **scheduler 异常处理**：是否在 base class 中加？
4. **死信队列**：是否需要？
5. **幂等入队**：cleanup_queue UNIQUE(raw_table, raw_row_id) 已防队列重复，但上游入队的幂等谁负责？
6. **历史数据迁移**：现有 shared_companies / company_sources 数据（如有）如何处理？

---

## G. 关键文件路径

**迁移**（设计参考）：
- `_control/inputs/database/alembic-migrations/20260430_0009_phase1_collection_schema.py`
- `_control/inputs/database/alembic-migrations/20260501_0012_waimaotong_raw_contacts.py`

**实现**：
- `backend/app/services/cleanup_service.py`（286 行）
- `backend/app/workers/{collection,collection_scheduler,scoring,sending}.py`

**Schema**：
- `_control/inputs/database/schema.sql`（设计稿）
- `_control/inputs/database/schema-current-2026-05-05.md`（生产现状）
