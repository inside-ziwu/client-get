# Slice 1.B — 数据模型 V3 重建（T-DF-31 + D-008=B + cleanup_service）

状态：**✅ 本地验证通过，已签字**

创建日期：2026-05-07

---

## 目标

基于 migration 0009（Phase 1 Collection Schema）留下的 bigserial 骨架，将数据模型全面升级至 V3：

| 变更项 | 规格来源 | 说明 |
|--------|----------|------|
| `tenant_companies.id` bigserial → uuid | T-DF-31 | 修复与 `sending_plan_recipients.tenant_company_id uuid` 的类型错配 |
| `shared_companies` → `clean_companies` | D-008=B | V3 共享公司池，uuid PK + 11 个 D-038/D-039 字段 |
| `clean_contacts` 新建 | D-008=B | 清洗联系人表，与 `clean_companies` 关联 |
| `competitor_companies` / `competitor_contacts` 重建 | 0009 CASCADE | 0009 级联删除后依 V3 schema 重建 |
| cleanup_service worker | C1-G1~G5 | 无状态服务，消费 cleanup_queue → UPSERT clean_companies → fan-out tenant_companies |

---

## 阻塞问题（已解决）

1. **0009 DROP shared_companies CASCADE** → competitor_companies/company_sources 一并删除 → 需在 0014 重建
2. **shared_contacts 未被 0009 删除** → contacts 迁移延迟至 Slice 2；shared_contacts.company_id FK 已随 shared_companies 删除而自动移除
3. **clean_companies.last_updated vs updated_at** → V3 schema 使用 `last_updated`；tenant_ops_service.py 已修正

---

## 交付物清单

### 数据库迁移
- [x] `backend/alembic/versions/20260507_0014_t_df_31_data_model_v3.py`
  - DROP tenant_companies / clean_companies / competitor_companies / competitor_contacts CASCADE
  - CREATE clean_companies (uuid PK，D-038 +9 字段，D-039 +2 字段)
  - CREATE tenant_companies (uuid PK，clean_company_id FK，matched_keywords jsonb，完整业务字段)
  - CREATE clean_contacts (uuid PK → clean_companies)
  - CREATE competitor_companies / competitor_contacts (V3 schema，RLS)
  - 恢复 sending_plan_recipients / scoring_jobs / company_scores / tenant_contacts FK（DO $$ EXCEPTION 模式）

### 服务层修改
- [x] `backend/app/services/tenant_ops_service.py` — shared_companies → clean_companies，company_id → clean_company_id
- [x] `backend/app/services/tenant_query_service.py` — 同上
- [x] `backend/app/services/tenant_messaging_service.py` — 同上（6+ 处）；shared_contacts 引用保留至 Slice 2
- [x] `backend/app/services/scoring_service.py` — _load_company_context JOIN clean_companies

### 新增 worker
- [x] `backend/app/services/cleanup_service.py` — 无状态 CleanupService（_claim_batch SKIP LOCKED → _process_one → _upsert_clean_company → _upsert_tenant_companies）
- [x] `backend/app/workers/cleanup.py` — CleanupWorker（run_once / run_loop）
- [x] `backend/scripts/run_cleanup_worker.py` — CLI 入口（--once / --sleep-seconds）

### 文档同步
- [x] `backend/03_database/schema.sql` — 全量更新：
  - normalize_company_name() 函数（0009 新增）
  - collection_keywords 反映 0009 schema（去 countries/countries_hash/source_types，加进度字段）
  - clean_companies（V3），shared_contacts（FK 移除注释），clean_contacts（新建）
  - waimaotong_raw_companies / tendata_raw_companies / lixiaoyun_raw_companies / cleanup_queue（0009 新增）
  - tenant_companies（V3），competitor_companies / competitor_contacts（V3 重建）
  - 去重 RLS（已 inline 入表定义）

---

## D-008=B 设计决策

### clean_companies 字段策略
- **向后兼容**：保留 `name`, `name_en`, `country`, `domain`, `industry`, `industry_tags`, `product_keywords`, `data_completeness`, `employee_count` — 服务层代码零改动
- **D-038 新增**（+9）：`incorporation_date`, `reg_capital`, `employee_scale`, `employee_num`, `trade_amount_3y_usd`, `trade_count`, `contacts_count`, `product_tags`, `factory_type`
- **D-039 新增**（+2）：`has_china_pcb_supplier`（factory_type 覆盖 PCB 场景）
- **去重键**：`UNIQUE(name_normalized, country_iso3)` + `normalize_company_name()` 函数

### tenant_companies 字段策略
- 删除：`company_id uuid → shared_companies`（旧），`keyword_id`, `collection_task_id`（改由 cleanup_queue.task_id 承载）
- 新增：`clean_company_id uuid → clean_companies ON DELETE CASCADE`，`matched_keywords jsonb`（D-012）
- 保留：`business_status`, `data_status`, `grade`, `total_score`, `is_precise_customer`, `source_marker`, `notes`, `tags`, `deleted_at`

### cleanup_service 路由规则（D-008 规则）
| raw_table | 处理方式 |
|-----------|----------|
| `lixiaoyun_raw_companies` | 直接 mark done（励销云不入 clean） |
| `waimaotong_raw_companies` | → _clean_and_link → UPSERT clean_companies → fan-out tenant_companies |
| `tendata_raw_companies` | 同上（Phase 2 单独处理 Tendata text PK 不兼容问题） |

---

## 延迟至 Slice 2 的事项

1. **shared_contacts 迁移** → clean_contacts（contacts 路径，Slice 2）
2. **tenant_contacts.contact_id → clean_contacts**（当前仍指向 shared_contacts）
3. **tenant_messaging_service.py** 中的 shared_contacts JOIN（Slice 2 同步修改）
4. **Tendata raw_row_id 类型不兼容**（text PK vs bigint）→ Phase 2 清洗逻辑

---

## 本地验证步骤

```bash
cd backend

# 1. 运行迁移
uv run alembic upgrade head

# 2. 验证表结构
# 检查 tenant_companies.id 是 uuid
# 检查 clean_companies 存在且 UNIQUE(name_normalized, country_iso3)
# 检查 FK: sending_plan_recipients → tenant_companies

# 3. Cleanup worker smoke test
uv run python scripts/run_cleanup_worker.py --once
# 期望输出：{"service_instance": "cleanup-worker-1", "recovered": 0, "processed": 0}

# 4. 基础单元测试
uv run pytest tests/ -x -q
```

---

## 签字

- [x] 本地迁移验证通过（lay 2026-05-07）
- [x] cleanup worker --once smoke test 通过 — processed=25，再次为0（lay 2026-05-07）
- [x] Sealos 生产迁移（lay 2026-05-07）

**发现的 bug（已修复）：** `_upsert_tenant_companies` SQL 中 `:clean_id::uuid` 的 `::` PostgreSQL 强制转型语法使 asyncpg 参数替换失效，改为 `CAST(:clean_id AS uuid)` 修复。
