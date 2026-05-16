# 真实 Schema 快照 · 2026-05-05

> **来源**：Sealos 生产 PostgreSQL 16.4.0（数据库名 `clientget`，schema `public`）
> **采集方式**：Chat2DB 控制台执行 3 条 information_schema / pg_indexes 元数据查询，复制结果
> **不含**：业务行数据 / 索引 DDL 之外的触发器 / 视图定义 / 默认值 / 字段注释
> **采集人**：用户
> **存档目的**：与 [`schema.sql`](schema.sql)（设计稿）+ [`docs/business-flow-DRAFT.md`](../../../docs/business-flow-DRAFT.md) §9 ER 图做三方对照

## 表总览（按字母序，54 行）

仅业务相关，已剔除 PG 系统扩展视图（`pg_stat_kcache*` / `pg_stat_statements*`）。

| # | 表名 | 类型 |
| --- | --- | --- |
| 1 | `ai_models` | 业务表 |
| 2 | `ai_scene_defaults` | 业务表 |
| 3 | `ai_usage_logs` | 业务表 |
| 4 | `alembic_version` | Alembic 版本表 |
| 5 | `articles_p_2026_04` | 分区子表（父=`intelligence_articles`） |
| 6 | `audit_logs` | 业务表（分区父） |
| 7 | `audit_logs_p_2026_04` | 分区子表 |
| 8 | `collection_keywords` | 业务表 |
| 9 | `collection_task_keywords` | 业务表 |
| 10 | `collection_tasks` | 业务表 |
| 11 | `company_blacklist` | 业务表 |
| 12 | `company_scores` | 业务表 |
| 13 | `company_sources` | 业务表（**关键**：来源映射，多源指向同 shared_companies） |
| 14 | `competitor_companies` | 业务表 |
| 15 | `contact_rules` | 业务表 |
| 16 | `data_source_credentials` | 业务表 |
| 17 | `data_sources` | 业务表 |
| 18 | `domain_daily_usage` | 业务表 |
| 19 | `domain_warmup_history` | 业务表 |
| 20 | `domain_warmup_status` | 业务表 |
| 21 | `email_events` | 业务表 |
| 22 | `email_send_locks` | 业务表 |
| 23 | `email_templates` | 业务表（租户级） |
| 24 | `emails` | 业务表（分区父） |
| 25 | `emails_p_2026_04` | 分区子表 |
| 26 | `group_members` | 业务表 |
| 27 | `groups` | 业务表 |
| 28 | `intelligence_article_publications` | 业务表 |
| 29 | `intelligence_articles` | 业务表（分区父） |
| 30 | `intelligence_sources` | 业务表 |
| 31 | `intelligence_subscriptions` | 业务表 |
| 32 | `notifications` | 业务表 |
| 33 | `platform_email_templates` | 业务表 |
| 34 | `platform_scoring_template_versions` | 业务表 |
| 35 | `platform_scoring_templates` | 业务表 |
| 36 | `platform_users` | 业务表 |
| 37 | `scoring_jobs` | 业务表（迁移 0003 加） |
| 38 | `scoring_template_versions` | 业务表（租户级） |
| 39 | `scoring_templates` | 业务表（租户级） |
| 40 | `sending_plan_recipients` | 业务表 |
| 41 | `sending_plans` | 业务表 |
| 42 | `sequence_enrollments` | 业务表 |
| 43 | `sequence_steps` | 业务表 |
| 44 | `service_idempotency_keys` | 业务表 |
| 45 | `shared_companies` | 业务表（**核心**：跨源去重的统一公司库） |
| 46 | `shared_contacts` | 业务表（**核心**：跨源去重的统一联系人库） |
| 47 | `tenant_ai_provider_configs` | 业务表 |
| 48 | `tenant_companies` | 业务表 |
| 49 | `tenant_contacts` | 业务表 |
| 50 | `tenants` | 业务表 |
| 51 | `user_roles` | 业务表 |
| 52 | `users` | 业务表 |
| 53 | `warmup_rule_levels` | 业务表 |
| 54 | `warmup_rules` | 业务表 |

## 重大缺失（与业务流 §9.3 ER 图对比）

### 业务流声称的 6 张 raw 表 — **实际 0 张存在**

| 业务流 §9.3 实体 | 实际 schema | 状态 |
| --- | --- | --- |
| `WaimaotongRawCompany` | ❌ 不存在 | **缺失** |
| `WaimaotongRawContact` | ❌ 不存在 | **缺失**（迁移 0012 应该创建，但表不在） |
| `TendataRawCompany` | ❌ 不存在 | **缺失** |
| `TendataRawContact` | ❌ 不存在 | **缺失** |
| `LixiaoyunRawCompany` | ❌ 不存在 | **缺失** |
| `LixiaoyunRawContact` | ❌ 不存在 | **缺失** |

### 业务流声称的 clean 干净库

| 业务流 §9.4 实体 | 实际 schema | 状态 |
| --- | --- | --- |
| `CleanCompany` | `shared_companies`（不同名但功能等价？） | **命名分歧** |
| `CleanContact` | `shared_contacts`（不同名但功能等价？） | **命名分歧** |

### 业务流没有，但实际存在

- `company_sources` —— 来源映射表（一行 = 一个 (shared_company_id, source_type, source_id) 三元组）

> **结论**：实际 backend 的设计是 **`shared_companies` + `company_sources` (来源映射)** 模型，而不是业务流提的 **6 张 raw 表 + 2 张 clean 表** 模型。这是根本性的架构分歧。

## 完整字段定义

### 详细输出见以下三段（原始 SQL 结果）

> 太长，仅作存档；摘要分析见 [`_control/v3/02-er-schema-divergence.md`](../../v3/02-er-schema-divergence.md)

#### SQL ① 表 + 字段（共 58 行，含 4 个 PG 系统视图）

见用户 2026-05-05 提供的原始消息——已用于生成 [`02-er-schema-divergence.md`](../../v3/02-er-schema-divergence.md) 的字段对照表。完整内容因量大不再原样转录，原始数据由 Chat2DB 查询直接产生，可随时重跑：

```sql
SELECT table_name,
       string_agg(column_name || ' ' || data_type ||
                  COALESCE('(' || character_maximum_length || ')', '') ||
                  CASE WHEN is_nullable='NO' THEN ' NOT NULL' ELSE '' END,
                  ', ' ORDER BY ordinal_position) AS columns
FROM information_schema.columns WHERE table_schema = 'public'
GROUP BY table_name ORDER BY table_name;
```

关键观察：

- `alembic_version` 仅 1 字段（version_num），证明 Alembic 在管理迁移
- `articles_p_2026_04` 与 `intelligence_articles` 字段完全相同 → 分区子表/父表
- `audit_logs_p_2026_04` 与 `audit_logs` 同上
- `emails_p_2026_04` 与 `emails` 同上
- 大量 jsonb 字段（业务弹性高）：`config / metadata / raw_data / dimensions / settings / tags / industry_tags / variables` 等
- 大量带 `_at` 后缀的 timestamptz 字段（统一审计）

#### SQL ② 主键 / 外键 / 唯一约束

> 数据由 `information_schema.table_constraints` 查询；含**重复行**（PG `string_agg` 在多列约束下会展开），分析时只取唯一三元组 (table, type, column_or_fk)。

#### SQL ③ 索引

> 数据由 `pg_indexes` 查询；每行 1 个 `CREATE INDEX` DDL。
> 关键索引模式：所有大表都有 `idx_<table>_tenant` 风格的多租户隔离索引；`scoring_jobs` 和 `collection_tasks` 用 `WHERE status = 'pending'` 偏序索引（lease 模式必备）。

## 待跑（用户方便时）

```sql
-- 当前 alembic head（确认是否 0013）
SELECT version_num FROM alembic_version;

-- 字段默认值（INSERT 行为）
SELECT table_name, column_name, column_default
FROM information_schema.columns
WHERE table_schema = 'public' AND column_default IS NOT NULL
ORDER BY table_name;

-- ENUM 类型定义
SELECT typname, string_agg(enumlabel, ', ' ORDER BY enumsortorder) AS values
FROM pg_type t JOIN pg_enum e ON t.oid = e.enumtypid
GROUP BY typname;
```
