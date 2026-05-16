# 数据库 Schema 整理

> **目的**：把分散在 blueprint 与 backend 的数据库相关材料集中到一处，加上索引与表清单，方便后续查阅与决策。
> **整理时间**：2026-05-04（schema 设计稿）+ 2026-05-05（访问协议成文化）
> **原则**：所有文件均为 `cp` 拷贝（非剪切），原位置保持不动；所有文件 MD5 已校验一致。

## 🔴 访问生产数据库前必读

如需从 Sealos 生产 PostgreSQL 拉真实 schema 或查数据，**必须遵守**：

→ [**`access-protocol.md`**](access-protocol.md) — 数据库访问协议（含命令模板、脱敏规则、Gate 10 边界）

**当前选定方案（用户 2026-05-05 决策）**：方案 1（schema-only 拷贝）+ 方案 2（偶发数据查询：用户跑、粘贴脱敏结果）。

**真实 schema 快照**（待用户首次跑）：`schema-current-YYYY-MM-DD.sql`，与本目录 [`schema.sql`](schema.sql)（blueprint 设计稿）对照可得 §D ER vs schema 偏差表。

## 1. 文件来源映射

| 本目录文件 | 来源（原位置不动） | 大小 | 标签 |
| --- | --- | --- | --- |
| [`schema.sql`](schema.sql) | `blueprint/03_database/schema.sql` | 42KB / 945 行 | 设计真源 |
| [`RLS_POLICY_MATRIX.md`](RLS_POLICY_MATRIX.md) | `blueprint/03_database/RLS_POLICY_MATRIX.md` | 5.5KB | 行级安全策略矩阵 |
| [`MIGRATION_ORDER_AND_NOTES.md`](MIGRATION_ORDER_AND_NOTES.md) | `blueprint/03_database/MIGRATION_ORDER_AND_NOTES.md` | 2.5KB | 迁移顺序笔记 |
| [`09_DATABASE_DESIGN_REPAIRED.md`](09_DATABASE_DESIGN_REPAIRED.md) | `blueprint/01_final_repaired_docs/09_DATABASE_DESIGN_REPAIRED.md` | 4.9KB | 数据库设计修订（设计权威） |
| [`14_DATA_MIGRATION_REPAIRED.md`](14_DATA_MIGRATION_REPAIRED.md) | `blueprint/01_final_repaired_docs/14_DATA_MIGRATION_REPAIRED.md` | 3.5KB | 数据迁移修订 |
| [`SECURITY_RLS_AUTH_ARCHITECTURE.md`](SECURITY_RLS_AUTH_ARCHITECTURE.md) | `blueprint/02_architecture/SECURITY_RLS_AUTH_ARCHITECTURE.md` | 3.2KB | 安全/RLS/鉴权架构 |
| [`entities.yaml`](entities.yaml) | `blueprint/machine_readable/entities.yaml` | 1.2KB | 机读实体定义 |
| [`alembic-migrations/*.py`](alembic-migrations/) | `backend/alembic/versions/2026*.py` | 13 份 | 实际迁移脚本 |

> ⚠️ **未拷贝**：`blueprint/00_original_sources/09_DATABASE_DESIGN.md`（107KB 原始版）与 `docs/archive/system-docs/09_DATABASE_DESIGN.md`（归档版）——按 [`02-docs-index.md`](../../02-docs-index.md) 标签为 `[HISTORY]`，不再作为依据。

## 2. 真源关系（重要）

```
设计稿（人写的）           运行时被加载（代码读的）             实际执行
─────────────────────────────────────────────────────────────────
03_database/schema.sql ──cp──► backend/03_database/schema.sql
（蓝图中的设计副本）            （MD5 相同；alembic 0001 直接 read_text 加载）
                                              │
                                              ▼
                              alembic 0001 canonical_schema.py
                                              │
                                              ▼  按时间顺序
                              0002 → 0003 → ... → 0013
                              （增量演进当前真实库）
```

**结论**：
- `backend/03_database/schema.sql` 才是**代码运行时实际加载**的文件（来自 `0001_canonical_schema.py` 的 `Path(__file__).resolve().parents[2] / "03_database" / "schema.sql"`），不是无用拷贝。
- `blueprint/03_database/schema.sql` 是同一份的**设计副本**（手工保持同步）；本目录拷贝来自此处。
- 当前真实数据库结构 ≠ 仅 schema.sql；应理解为 **schema.sql + 0002~0013 顺序应用之后的状态**。

> 🟡 [`04-open-questions.md`](../../04-open-questions.md) #B1 已登记：两份 schema.sql 同 MD5——是否需要保留两份？现已澄清：**两份都需要**（一份是设计真源、一份被代码加载），但需要建立"修改时同步"的纪律。

## 3. 表清单（来自 `schema.sql` 945 行 + 0003、0012 增量；按业务域分组）

> 共 **44 张表 + 1 个 ENUM type**（schema.sql 中 43 张 + 迁移新增 2 张）。仅列表名，不展开列。完整定义看 [`schema.sql`](schema.sql) 与各迁移脚本。

### 3.1 平台层 / 系统

| 表 | 来源 | 用途（推测） |
| --- | --- | --- |
| `platform_users` | schema.sql L23 | 平台运营管理员账号 |
| `audit_logs` | schema.sql L852 | 审计日志（按月分区） |
| `service_idempotency_keys` | schema.sql L869 | 服务幂等键 |
| `notifications` | schema.sql L837 | 系统通知 |

### 3.2 租户与用户

| 表 | 来源 | 用途（推测） |
| --- | --- | --- |
| `tenants` | schema.sql L37 | 租户（slug + 域名等） |
| `users` | schema.sql L53 | 租户内用户 |
| `user_roles` | schema.sql L71 | 用户角色映射 |
| `user_role` (ENUM) | schema.sql L70 | `'admin','operator','viewer'` |

### 3.3 数据源（采集源）

| 表 | 来源 | 备注 |
| --- | --- | --- |
| `data_sources` | schema.sql L81 | 采集数据源（waimao_tong / tengdao / lixiaoyun 等） |
| `data_source_credentials` | schema.sql L95 | 数据源凭证（0005 已 drop source_type CHECK） |

### 3.4 Admin 全局配置

| 表 | 来源 | 备注 |
| --- | --- | --- |
| `platform_scoring_templates` | schema.sql L118 | 平台评分模板 |
| `platform_scoring_template_versions` | schema.sql L134 | 评分模板版本 |
| `platform_email_templates` | schema.sql L146 | 平台邮件模板（0006 加 body_design 列） |
| `warmup_rules` | schema.sql L163 | 预热规则 |
| `warmup_rule_levels` | schema.sql L176 | 预热规则等级 |
| `ai_models` | schema.sql L189 | AI 模型（0011 移除 input_price/output_price，0013 移除 model_type） |
| `ai_scene_defaults` | schema.sql L205 | AI 场景默认（0013 移除 fallback_model_ids） |
| `tenant_ai_provider_configs` | schema.sql L217（0004 容错重建） | 租户级 AI Provider 配置 |
| `ai_usage_logs` | schema.sql L244 | AI 调用日志 |

### 3.5 采集 · 共享层（跨租户）

| 表 | 来源 | 备注 |
| --- | --- | --- |
| `shared_companies` | schema.sql L270 | 共享公司库 |
| `company_sources` | schema.sql L297 | 公司来源映射 |
| `shared_contacts` | schema.sql L310 | 共享联系人库 |
| `collection_keywords` | schema.sql L333 | 采集关键词 |
| `collection_tasks` | schema.sql L352 | 采集任务（0007 加 task_type、context 列） |
| `collection_task_keywords` | schema.sql L378 | 任务-关键词关联 |
| `waimaotong_raw_contacts` | **0012 新增** | 外贸通联系人原始归档（修复"静默丢弃"P0） |

### 3.6 租户业务

| 表 | 来源 | 备注 |
| --- | --- | --- |
| `tenant_companies` | schema.sql L390 | 租户公司视图 |
| `tenant_contacts` | schema.sql L504 | 租户联系人视图 |
| `scoring_templates` | schema.sql L413 | 租户评分模板 |
| `scoring_template_versions` | schema.sql L428 | 模板版本 |
| `company_scores` | schema.sql L441 | 公司评分结果 |
| `scoring_jobs` | **0003 新增** | 评分任务队列（lease 模式） |
| `contact_rules` | schema.sql L464 | 联系人规则 |
| `company_blacklist` | schema.sql L477 | 公司黑名单 |
| `competitor_companies` | schema.sql L490（0008 富集多个字段） | 竞对公司 |
| `groups` | schema.sql L521 | 分组 |
| `group_members` | schema.sql L535 | 分组成员 |

### 3.7 邮件预热

| 表 | 来源 |
| --- | --- |
| `domain_warmup_status` | schema.sql L548 |
| `domain_warmup_history` | schema.sql L572 |
| `domain_daily_usage` | schema.sql L590 |

### 3.8 邮件发送

| 表 | 来源 |
| --- | --- |
| `email_templates` | schema.sql L605 |
| `sending_plans` | schema.sql L624 |
| `sending_plan_recipients` | schema.sql L649 |
| `sequence_steps` | schema.sql L666 |
| `sequence_enrollments` | schema.sql L683 |
| `email_send_locks` | schema.sql L702 |
| `emails` | schema.sql L716 |
| `email_events` | schema.sql L755 |

### 3.9 情报中心

| 表 | 来源 |
| --- | --- |
| `intelligence_sources` | schema.sql L771 |
| `intelligence_articles` | schema.sql L788 |
| `intelligence_subscriptions` | schema.sql L807 |
| `intelligence_article_publications` | schema.sql L819 |

## 4. 迁移时间线（13 份）

| 顺序 | 文件 | 日期 | 一句话摘要 |
| --- | --- | --- | --- |
| 0001 | `20260421_0001_canonical_schema.py` | 2026-04-21 | **初始 schema**：直接 exec `backend/03_database/schema.sql` 全文 |
| 0002 | `20260421_0002_seed_and_partitions.py` | 2026-04-21 | 初始 seed 数据 + 月度分区创建 |
| 0003 | `20260422_0003_scoring_jobs.py` | 2026-04-22 | **新增** `scoring_jobs` 表（评分任务队列，lease 模式） |
| 0004 | `20260422_0004_tenant_ai_provider.py` | 2026-04-22 | 容错创建 `tenant_ai_provider_configs`（如果不存在） |
| 0005 | `20260423_0005_drop_source_type_check.py` | 2026-04-23 | 移除 `data_sources` / `data_source_credentials` 的 source_type CHECK |
| 0006 | `20260423_0006_email_template_design.py` | 2026-04-23 | `platform_email_templates` 加 `body_design` 列 |
| 0007 | `20260429_0007_collection_task_type.py` | 2026-04-29 | `collection_tasks` 加 `task_type` + `context` 列 |
| 0008 | `20260429_0008_competitor_enrichment.py` | 2026-04-29 | `competitor_companies` 加 source_id / name_en / reg_capital 等富集字段 |
| 0009 | `20260430_0009_phase1_collection_schema.py` | 2026-04-30 | Phase 1 采集 schema（具体未细读） |
| 0010 | `20260501_0010_add_default_partitions.py` | 2026-05-01 | 给 `audit_logs` / `emails` / `intelligence_articles` 加 DEFAULT 分区兜底 |
| 0011 | `20260501_0011_drop_ai_model_pricing_columns.py` | 2026-05-01 | `ai_models` 移除 `input_price` / `output_price` 列（计费模型变化） |
| 0012 | `20260501_0012_waimaotong_raw_contacts.py` | 2026-05-01 | **新增** `waimaotong_raw_contacts` 表（修复联系人静默丢弃 P0） |
| 0013 | `20260501_0013_drop_ai_fallback.py` | 2026-05-01 | 移除 `ai_models.model_type` 与 `ai_scene_defaults.fallback_model_ids`（场景解析简化） |

## 5. 与文档的对应关系

| 主题 | 设计文档 | 实际代码 |
| --- | --- | --- |
| 整体设计 | [`09_DATABASE_DESIGN_REPAIRED.md`](09_DATABASE_DESIGN_REPAIRED.md) | `schema.sql` |
| 行级安全 | [`RLS_POLICY_MATRIX.md`](RLS_POLICY_MATRIX.md) + [`SECURITY_RLS_AUTH_ARCHITECTURE.md`](SECURITY_RLS_AUTH_ARCHITECTURE.md) | RLS 策略写在 `schema.sql` 内 |
| 数据迁移 | [`14_DATA_MIGRATION_REPAIRED.md`](14_DATA_MIGRATION_REPAIRED.md) | `migrate_legacy.py`（`backend/scripts/`） |
| 迁移顺序 | [`MIGRATION_ORDER_AND_NOTES.md`](MIGRATION_ORDER_AND_NOTES.md) | `alembic-migrations/` |
| 机读实体 | [`entities.yaml`](entities.yaml) | （供 AI 代理读） |
| 业务域 schema 扩展 | `docs/spec-collection-module.md`（活跃）、`docs/spec-phase1.5-*.md`（活跃） | 0007、0008、0009、0012 等 |

## 6. 关键发现 / 待确认

- 🟡 **B1 → 已澄清**：两份 schema.sql MD5 相同，但**不是冗余**——一份被 alembic 0001 加载（`backend/03_database/schema.sql`），一份是设计真源副本（`blueprint/03_database/schema.sql`）。修改时需要同步两份。
- 🔴 **新发现 F1**：`backend/app/models/` **是空目录**（除 `__pycache__`）——后端没有 SQLAlchemy ORM 模型层？所有数据访问都是裸 SQL 还是其他方式？需读 `backend/app/repositories/` 与 `backend/app/db/` 才能确认（**本次未读**）。已登记到 [`04-open-questions.md`](../../04-open-questions.md)。
- 🟡 **F2**：`scoring_jobs` 与 `waimaotong_raw_contacts` 不在 schema.sql 里，由迁移单独建——schema.sql 是否会在某时刻被"同步刷新"，把这两张表也写进去？现在 schema.sql 与真实库结构有偏差。
- 🟡 **F3**：分区策略：schema.sql 与 0002、0010 都涉及分区。月度分区由"启动钩子"创建，0010 的 DEFAULT 分区是兜底。运行环境的"启动钩子"在何处？需读 `backend/app/main.py` 或 lifespan 配置（**本次未读**）。

## 7. 本目录的更新纪律

> 当 `blueprint/` 中任一原始文件变更时，本目录拷贝**不会自动同步**。需要在 [`_control/04-open-questions.md`](../../04-open-questions.md) 记录"待重新整理"，由人工触发再次拷贝。

> 🟢 当前所有拷贝的 MD5 已校验与原文件一致（2026-05-04）。
