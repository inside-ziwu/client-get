# waimaotong_clean_companies (60列) vs 原项目 company_analysis (44列) 字段对比

> 调研时间：2026-05-18
> 线上数据库：clientget / alembic_version: 20260518_0043
> 原项目：https://github.com/aoqi-ai/sysdev-ft-marketing

## 一、原项目 company_analysis 的 44 列在 CG 中的对应情况

| # | 原项目 company_analysis | 类型 | CG clean_companies | 类型 | 状态 |
|---|---|---|---|---|---|
| 1 | `id` | SERIAL | `id` | bigint | ✅ 一致 |
| 2 | `company_id` | TEXT | `company_id` | text | ✅ 一致 |
| 3 | `company_name` | TEXT | `company_name` | text | ✅ 一致 |
| 4 | `english_name` | TEXT | `english_name` | text | ✅ 一致 |
| 5 | `country` | TEXT | `country` | text | ✅ 一致 |
| 6 | `grade` | TEXT | `grade` | text | ✅ 一致 |
| 7 | `score` | INTEGER | `score` | integer | ✅ 一致 |
| 8 | `sub_industry` | TEXT | `sub_industry` | text | ✅ 一致 |
| 9 | `match_reasons` | JSONB | `match_reasons` | jsonb | ✅ 一致 |
| 10 | `potential_needs` | JSONB | `potential_needs` | jsonb | ✅ 一致 |
| 11 | `recommended_products` | JSONB | `recommended_products` | jsonb | ✅ 一致 |
| 12 | `sales_approach` | TEXT | `sales_approach` | text | ✅ 一致 |
| 13 | `risk_factors` | JSONB | `risk_factors` | jsonb | ✅ 一致 |
| 14 | `website` | TEXT | `website` | text | ✅ 一致 |
| 15 | `region` | TEXT | — | — | ❌ CG 缺失 |
| 16 | `founded_year` | TEXT | `founded_year_text` | text | ⚠️ CG 改名 |
| 17 | `company_size` | TEXT | — | — | ❌ CG 缺失 |
| 18 | `revenue_estimate` | TEXT | — | — | ❌ CG 缺失 |
| 19 | `industry` | TEXT | — | — | ❌ CG 缺失（注：CG 有同名 `industry` 但含义不同，属原生列） |
| 20 | `main_business` | JSONB | `main_business` | jsonb | ✅ 一致 |
| 21 | `products_services` | JSONB | — | — | ❌ CG 缺失 |
| 22 | `target_customers` | TEXT | — | — | ❌ CG 缺失 |
| 23 | `market_coverage` | TEXT | — | — | ❌ CG 缺失 |
| 24 | `company_type` | TEXT | `company_type_analysis` | text | ⚠️ CG 改名 |
| 25 | `linkedin` | TEXT | — | — | ❌ CG 缺失 |
| 26 | `youtube` | TEXT | — | — | ❌ CG 缺失 |
| 27 | `other_social` | TEXT | — | — | ❌ CG 缺失 |
| 28 | `recent_activities` | JSONB | — | — | ❌ CG 缺失 |
| 29 | `key_contacts` | JSONB | — | — | ❌ CG 缺失 |
| 30 | `data_sources` | JSONB | `data_sources` | jsonb | ✅ 一致 |
| 31 | `search_raw` | TEXT | `search_raw` | text | ✅ 一致 |
| 32 | `ai_raw` | TEXT | `ai_raw` | text | ✅ 一致 |
| 33 | `sys_company_id` | UUID | `sys_company_id` | uuid | ✅ 一致 |
| 34 | `plan_id` | INTEGER | `plan_id` | integer | ✅ 一致 |
| 35 | `email_priority` | TEXT | `email_priority` | text | ✅ 一致 |
| 36 | `product_tags` | JSONB | `product_tags` | jsonb | ✅ 一致 |
| 37 | `tag_confidence` | JSONB | `tag_confidence` | jsonb | ✅ 一致 |
| 38 | `data_source_tags` | JSONB | — | — | ❌ CG 缺失 |
| 39 | `has_trade_data` | BOOLEAN | `has_trade_data` | boolean | ✅ 一致 |
| 40 | `trade_summary` | JSONB | `trade_summary` | jsonb | ✅ 一致 |
| 41 | `score_details` | JSONB | `score_details` | jsonb | ✅ 一致 |
| 42 | `is_new_collection` | (推断) | — | — | ❌ CG 缺失 |
| 43 | `created_at` | TIMESTAMP | `created_at` | timestamptz | ⚠️ CG 带时区 |
| 44 | `updated_at` | TIMESTAMP | `updated_at` | timestamptz | ⚠️ CG 带时区 |

### 小结

- ✅ 一致：23 列
- ⚠️ 改名/改类型：4 列（`founded_year_text`、`company_type_analysis`、`created_at`、`updated_at`）
- ❌ CG 缺失：13 列（`region`、`company_size`、`revenue_estimate`、`industry`(原项目含义)、`products_services`、`target_customers`、`market_coverage`、`linkedin`、`youtube`、`other_social`、`recent_activities`、`key_contacts`、`data_source_tags`、`is_new_collection`）

---

## 二、CG 独有列（原项目 company_analysis 没有的 33 列）

这些列来自 CG 0035 迁移时的原生设计，大部分和 raw_companies 的字段重复搬过来。

| # | CG 列名 | 类型 | 被代码引用情况 |
|---|---|---|---|
| 1 | `source_id` | text | admin_collection_service（管理端展示） |
| 2 | `name` | text | tenant_ops_service（INSERT/唯一约束）— **租户端核心** |
| 3 | `country_iso3` | char(3) | tenant_ops_service（INSERT/唯一约束/查询）— **租户端核心** |
| 4 | `domain` | text | tenant_ops_service（INSERT）— 活跃写入 |
| 5 | `industry` | text | tenant_ops_service（INSERT）— 活跃写入（注：与原项目同名列含义不同） |
| 6 | `address` | text | 待确认 |
| 7 | `phone` | text | tenant_ops_service（INSERT）— 活跃写入 |
| 8 | `employee_size` | text | tenant_ops_service（INSERT）— 活跃写入 |
| 9 | `founded_year` | integer | tenant_ops_service（INSERT）— 活跃写入 |
| 10 | `description` | text | tenant_ops_service（INSERT）— 活跃写入 |
| 11 | `products` | text[] | tenant_ops_service（INSERT）— 活跃写入 |
| 12 | `emails` | text[] | 待确认 |
| 13 | `trade_amount_3y_usd` | numeric | tenant_query_service + admin_collection_service — **租户端筛选** |
| 14 | `trade_count` | integer | tenant_query_service + admin_collection_service — **租户端筛选** |
| 15 | `contacts_count` | integer | tenant_query_service + admin_collection_service — **租户端筛选** |
| 16 | `has_trade_data` | boolean | tenant_query_service — **租户端筛选** |
| 17 | `keyword_master_ids` | uuid[] | admin_collection_service（管理端展示） |
| 18 | `source_tags` | text[] | admin_collection_service（管理端展示） |
| 19 | `customs_data` | jsonb | admin_collection_service（管理端展示） |
| 20 | `search_payload` | jsonb | admin_collection_service（管理端展示） |
| 21 | `detail_payload` | jsonb | admin_collection_service（管理端展示） |
| 22 | `trade_payload` | jsonb | admin_collection_service（管理端展示） |
| 23 | `raw_payload` | jsonb | admin_collection_service（管理端展示） |
| 24 | `detail_status` | text | admin_collection_service（管理端展示） |
| 25 | `detail_fetched_at` | timestamptz | admin_collection_service（管理端展示） |
| 26 | `trade_status` | text | admin_collection_service（管理端展示） |
| 27 | `trade_fetched_at` | timestamptz | admin_collection_service（管理端展示） |
| 28 | `contacts_status` | text | admin_collection_service（管理端展示） |
| 29 | `contacts_fetched_at` | timestamptz | admin_collection_service（管理端展示） |
| 30 | `enrichment_error` | jsonb | admin_collection_service（管理端展示） |
| 31 | `full_address` | text | 待确认 |
| 32 | `founded_year_text` | text | 兼容原项目 founded_year（text 版本） |
| 33 | `website` | text | 兼容原项目 |

### 小结

- **不能删**（租户端活跃使用）：`name`、`country_iso3`、`domain`、`industry`、`phone`、`employee_size`、`founded_year`、`description`、`products`、`trade_amount_3y_usd`、`trade_count`、`contacts_count`、`has_trade_data`（共 13 列）
- **仅管理端使用**（管道重写后可能可删）：`source_id`、`keyword_master_ids`、`source_tags`、`customs_data`、`search_payload`、`detail_payload`、`trade_payload`、`raw_payload`、`detail_status`、`detail_fetched_at`、`trade_status`、`trade_fetched_at`、`contacts_status`、`contacts_fetched_at`、`enrichment_error`（共 15 列）
- **待确认**：`address`、`emails`、`full_address`（共 3 列）
- **兼容列**：`founded_year_text`、`website`（共 2 列）
