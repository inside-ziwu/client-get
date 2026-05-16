# §D · ER 图 vs 真实 Schema 偏差对照表

> **目的**：把 [`docs/business-flow-DRAFT.md`](../../docs/business-flow-DRAFT.md) §9 ER 图（业务方对齐成果）与 Sealos 生产数据库实际 schema 做三方对照（含 [`schema.sql`](../inputs/database/schema.sql) 设计稿），列出全部偏差并由用户逐项决策。
> **生成时间**：2026-05-05
> **数据来源**：
> - 真实 schema：[`_control/inputs/database/schema-current-2026-05-05.md`](../inputs/database/schema-current-2026-05-05.md)（用户 Chat2DB 跑出 + Sealos 生产 PG 16.4.0）
> - 业务流 ER：`docs/business-flow-DRAFT.md` §9（29 个实体，9 子节）
> - 设计稿 schema：`_control/inputs/database/schema.sql`（blueprint 03_database/，与 backend `app/03_database/` MD5 相同）

---

## 0. 决策标记说明

每行末尾的"建议"列由 AI 给出，**不生效**。每行需用户 ✅ 接受 / ✏️ 修改 / ❌ 拒绝。

按 [`AGENTS.md` §6 单一真源](../../AGENTS.md#6-单一真源原则最高优先级)，最终结论以本文件用户签字版（v0.2+）为准——届时业务流 §9 ER 图与 schema.sql 都按此对齐。

签字行：

```
__________________________ (用户)   日期：__________
```

---

## 1. 🔴 根本架构分歧：raw 6 表 vs shared+sources 模型

> **这是最重大的偏差**，影响业务流 §2.2 / §2.3 / §5 / §9.3 / §9.4 全部表述，以及 V3 范围的多个核心决策。

### 1.1 业务流 §9.3 模型（业务方期望）

```
关键词
  ├─→ waimaotong_raw_companies → waimaotong_raw_contacts
  ├─→ tendata_raw_companies   → tendata_raw_contacts
  └─→ lixiaoyun_raw_companies → lixiaoyun_raw_contacts
                  ↓ 清洗去重合并
       clean_companies → clean_contacts （平台共享）
                  ↓ fan-out
       tenant_companies → tenant_contacts （租户视图）
```

**6 张 raw 表 + 2 张 clean 表 + 租户视图**——按数据源分表，清洗时合并到统一表。

### 1.2 实际 Schema 模型（backend 已实现）

```
关键词 (collection_keywords)
  ↓ collection_tasks（含 source_types JSON 数组，标识此任务用哪些源）
  ↓ 直接写入：
shared_companies + company_sources（一行 = 一个 (shared_company_id, source_type, source_id) 三元组）
shared_contacts （一行 = 一个联系人）
  ↓ fan-out
tenant_companies + tenant_contacts （租户视图）
```

**统一 1 张 shared_companies + company_sources 多对一映射**——按公司去重，多个源指向同一行 shared 公司。

### 1.3 两种模型对照

| 维度 | 业务流 §9.3（6 raw + 2 clean） | 实际 Schema（shared + sources） |
| --- | --- | --- |
| 公司表数 | 6（raw）+ 1（clean） = 7 | 1（shared）+ 1（sources 映射） = 2 |
| 联系人表数 | 6（raw 嵌套或独立）+ 1（clean） = 7 | 1（shared_contacts） |
| 数据流 | raw → 清洗 worker → clean → 分发 | 采集 → 直接写 shared + sources |
| 跨源去重 | 清洗 worker 合并 | 写入时 UPSERT shared_companies(name_normalized, country) |
| 业务流 §5"差距清单" | "tendata_raw_contacts ❌ 没建" | 实际 **完全不存在 raw 表** |
| 励销云不进清洗（§2.5） | 业务规则：lixiaoyun_raw_companies 不入 cleanup_queue | **lixiaoyun_raw 表本身就不存在**——励销云数据流向不明 |

### 1.4 影响的业务流条款

| 条款 | 业务流原文（来源行） | 实际 Schema 现状 | 偏差 |
| --- | --- | --- | --- |
| §2.1 双路径并行（L52-69） | "外贸通 → waimaotong_raw_*" | 不存在 waimaotong_raw_* | **路径表述错** |
| §2.2 6 张原始库（L71-94） | "原始库按【渠道 × 类型】建表，共 6 张实表" | 0 张 raw 表 | **架构错** |
| §2.3 清洗与干净库（L95-99） | "外贸通原始 + 腾道原始 → clean_companies + clean_contacts" | 直接写 shared_*；无 clean_* 表 | **命名 + 流程错** |
| §2.5 励销云不进清洗（L107-110） | "中国同行清单仅作反推 stage 2 输入" | lixiaoyun raw 表不存在；励销云数据如何处理未知 | **流程未实现** |
| §5 差距清单（L412-426） | 标 "clean_companies ✅ 已建 / clean_contacts ❌ 没建" | 实际是 shared_companies ✅ + shared_contacts ✅ | **诊断错位** |
| §9.3 ER（L2393-2466） | 6 张 raw 表完整字段定义 | 0 张存在 | **整节失效** |
| §9.4 ER（L2469-2497） | CleanCompany / CleanContact | 实际 shared_companies / shared_contacts | **命名错** |
| Phase 1.5 D2 / D3 缺口 | "tendata/lixiaoyun raw_contacts 未独立成表 / clean_contacts 未建" | 全是基于错误前提的"缺口" | **缺口本身不成立** |

### 1.5 决策结果（用户 2026-05-05）

| 选项 | 含义 | 决策 |
| --- | --- | --- |
| (A) 以实际 Schema 为准（shared + sources） | 接受现状，业务流 §2.2~§9.4 修订 | ❌ 未选 |
| **(B) 以业务流 ER 为准（6 raw + 2 clean）** | **重构 backend：拆 shared → 6 raw + 2 clean；新建 cleanup_service worker** | ✅ **用户已选** |
| (C) 双轨保留 | 双倍存储 + 维护 | ❌ 未选 |

**用户决策理由**：清洗逻辑解耦是数据管道最佳实践（采集→清洗→沉淀）；后期清洗逻辑变更时不需要重写采集端，只需调整 cleanup worker。**架构演进性优先于短期工作量**。

**派生影响**：
- D-001 修订：允许 V3 实施时重构 raw/clean 层
- Phase 1.5 D2/D3/D4 缺口**重新打开**为 V3 必修
- D-015 励销云数据落点重新评估（详见 [`04-open-questions.md`](../04-open-questions.md) §L D-008-B.3）
- 新建 cleanup_service worker（~500 行 Python + 测试）
- V3 工作量 9-15 → 14-25 天

---

## 2. 关键概念缺失

### 2.1 KeywordMaster（业务流 §9.2）

**业务流 ER**：`KeywordMaster` + `TenantKeyword` 两张表（M:N 关联），归一查 master 命中即走 UC-11"已收录复用"分支。

**实际 schema**：`collection_keywords` **一张表**含 `tenant_id`——意味着每个租户独立的关键词，**没有跨租户复用机制**。

| 业务流 ER | 实际 Schema |
| --- | --- |
| `KeywordMaster.normalized_text` 全平台唯一 | 不存在 |
| `KeywordMaster.status = 'collected'` → 已收录 → UC-11 复用 | 不存在；每租户重复采集 |
| `TenantKeyword(tenant_id, keyword_master_id)` | 不存在；直接 `collection_keywords(tenant_id, ..., countries_hash)` |

**影响 UC**：
- UC-06 步骤 5/6a 已收录路径 → **当前不可能**
- UC-11 已收录关键词自动复用 → **当前不可能**
- 业务流 §1.3 关键词归一规则与跨租户复用 → **设计未实现**

**建议**：按 D-001"V3 起点 = 当前 backend"，**接受 UC-11 暂不可用**。要么 V3 实施时新增 `keyword_master` 表 + 迁移 `collection_keywords`，要么把 UC-11 推迟到 V3.1。

### 2.2 私有状态字段（业务流 §3.5 Q12）

业务流 §3.5（L216-225）列出租户私有状态层 7 个字段。实际 schema：

| 业务流字段 | 实际表 / 字段 | 状态 |
| --- | --- | --- |
| ① 是否精选 | `tenant_companies.tags`（jsonb） | ⚠️ 没有独立 `is_curated` 字段，可能用 tag 实现，**或未实现** |
| ② 是否拉黑 | `company_blacklist` 独立表 | ✅ 已实现（独立表而非字段） |
| ③ 租户级评分调整 | `company_scores` 独立表（含 grade/total_score/dimension_scores） | ⚠️ 实现了"评分"但没有 `tenant_score_override` 概念——是覆盖系统默认还是单独评分？ |
| ④ 私有备注 | `tenant_companies.notes` | ✅ |
| ⑤ 私有标签 | `tenant_companies.tags` | ✅ |
| ⑥ 联系人级状态 | `tenant_contacts.status / is_default` | ✅ |
| ⑦ 邮件状态（5 态聚合） | `emails.status` 联系人级 + 公司行聚合需查询时计算 | ⚠️ 状态在每行 email 里，UI 列表的"公司行 5 态聚合"逻辑由前端/API 实时算 |

### 2.3 业务流提的 tenant_smtp_credentials

**业务流 ER §9.6 标 `tenant_smtp_credentials`** —— 实际 **不存在**（按 D-002 架构 C 也不应建，是 D-002 决策已覆盖）

✅ 与 D-002 一致，不冲突。

---

## 3. 命名分歧（同一概念不同名）

| 业务流 ER 命名 | 实际 Schema 命名 | 备注 |
| --- | --- | --- |
| `CleanCompany` | `shared_companies` | §1 已展开 |
| `CleanContact` | `shared_contacts` | §1 已展开 |
| `WaimaotongRawCompany` 等 6 张 | （不存在） | §1 已展开 |
| `KeywordMaster` + `TenantKeyword` | `collection_keywords` | §2.1 已展开 |
| `SendingPlanTarget` | `sending_plan_recipients` | 同概念，命名不同 |
| `TenantEmailTemplate` | `email_templates`（带 `tenant_id`，含 `platform_template_id` 引用） | 同概念 |
| `EmailSendLog` | `email_events`（事件流） + `emails`（实例） | 业务流单一日志 → 实际拆为事件流 + 实例 |

**建议**：以实际 Schema 命名为准。业务流 ER 图后续修订时改名对齐。

---

## 4. 业务流没有但实际存在的（额外能力）

| 实际表 | 用途推测 | 业务流是否需要 |
| --- | --- | --- |
| `company_sources` | (shared_company_id, source_type, source_id) 三元组，多源映射到同公司 | ✅ shared+sources 模型必需，业务流 ER 应补 |
| `audit_logs`（按月分区） | 全量审计日志 | 业务流 §10.2 提过 |
| `service_idempotency_keys` | 服务幂等键 | 业务流隐含（worker 幂等），但 ER 未画 |
| `scoring_jobs` | 评分任务队列（lease 模式） | 业务流 ER 未画，UC-12 / UC-14 隐含 |
| `email_send_locks` | 邮件发送锁（防重复） | 业务流 §4.7 防重复发送的实现 |
| `domain_warmup_history` | 预热历史轨迹 | 业务流 §4.4 未提，但 admin 维护 warmup 用得到 |
| `domain_daily_usage` | 每日发件配额（按域名） | 业务流 §2.7"1000/天/数据源"的邮件版 |
| `tenant_ai_provider_configs` | 租户 AI 配置（OpenRouter key 等） | 业务流 UC-04 |
| `competitor_companies` | 反推路径中的中国同行（lixiaoyun 输入） | 业务流 §2.1 路径 B stage 1，但**没有按 lixiaoyun_raw 单独建表**——直接落到 competitor_companies |

**关键发现**：`competitor_companies` 可能就是**励销云数据的真实落地表**！业务流 ER §9.3 描述的"`lixiaoyun_raw_companies`"实际上是 `competitor_companies` 的别名/旧名。

**建议**：按 D-001 接受当前实现，业务流 §2.1 路径 B 的"励销云 → lixiaoyun_raw_companies"应改为"励销云 → competitor_companies"。

---

## 5. 字段层级偏差（按表分组）

> 仅列业务流 ER §9 描述与实际不一致的关键字段。

### 5.1 `tenants`

| 业务流 ER §9.1 | 实际 Schema | 备注 |
| --- | --- | --- |
| `name`（公司名称，全局唯一） | `name varchar(100)` | ✅ |
| `industry / status / created_at` | `industry / status / created_at` | ✅ |
| — | `slug varchar(50)`（业务流 UC-02 / Q1 隐含） | ✅ 实际有 slug，业务流 ER 漏画 |
| — | `settings jsonb` | ✅ 弹性配置 |
| — | `needs_onboarding bool` | ✅ 引导 UI 状态 |
| — | `contact_name / contact_phone / contact_email` | ✅ |

### 5.2 `users`

| 业务流 ER §9.1 | 实际 Schema | 备注 |
| --- | --- | --- |
| `email / password_hash / role / status` | `email / password_hash / status / must_change_pwd / failed_login_count / locked_until / last_login_at` | ⚠️ 业务流的 `role` 在实际中放到独立表 `user_roles`（多对多） |
| — | 无 `role` 字段 | role 在 `user_roles` 表 |
| `invited_at / activated_at` | 实际无（仅 `created_at / updated_at`） | ⚠️ 邀请流程时间戳缺失 |

### 5.3 `tenant_companies`

| 业务流 ER §9.5（推测） | 实际 Schema | 备注 |
| --- | --- | --- |
| `is_curated`（精选） | ❌ 无独立字段；可能用 tags 实现 | **决策点**：要不要单独字段？ |
| `is_blacklisted`（拉黑） | 实际是 `company_blacklist` 独立表 | ✅ 设计选择，可接受 |
| `tenant_score_override` | 实际是 `company_scores` 独立表（不是字段） | ✅ 实现更复杂但更灵活 |
| `note` | `notes`（多了 's'） | 命名细节 |
| `tags[]` | `tags jsonb` | ✅ |
| `primary_contact_id` | ❌ 实际通过 `tenant_contacts.is_default` 标记 | ⚠️ 业务流是"指针"模型，实际是"标志"模型 |
| `matched_keywords[]` | ❌ 仅 `keyword_id`（单一关键词） | **重要差异**：业务流允许 1 公司命中多关键词，实际只关联 1 个 |

### 5.4 `tenant_contacts`

| 业务流 ER §9.5 | 实际 Schema | 备注 |
| --- | --- | --- |
| 联系人状态 5 态 | `status varchar(20)` | ✅ 字段在；具体取值待 §B 决策 |
| `is_default`（业务流 §3.6 主联系人） | `is_default bool` | ✅（替代业务流的 `tenant_companies.primary_contact_id`） |
| `primary_contact` 唯一性 | 索引 `idx_tenant_contacts_one_default` `WHERE is_default AND deleted_at IS NULL` | ✅ 部分唯一索引，确保每公司每租户最多 1 主联系人 |
| `grade` 字段 | `grade char(1)` | ✅ 联系人级评分等级 |

### 5.5 `sending_plans`

| 业务流 §4.2 / Q16 | 实际 Schema | 备注 |
| --- | --- | --- |
| target_strategy（主联系人/全部/自定义） | `recipient_source varchar(20) + recipient_config jsonb` | ✅ 等价 |
| trigger_mode（手动/定时） | `scheduled_at`（NULL = 手动） + `started_at`（启动时间） | ⚠️ 没有显式 `trigger_mode` 字段，靠 scheduled_at 是否有值推断 |
| status 计划级（draft/active/paused/cancelled/completed） | `status varchar(20)` | ✅ 取值待确认 |
| sender_name / sender_email / domain_id | 业务流 ER 没画，**实际有**（D-002 架构 C 关键字段） | ✅ 实际 schema 已经为 D-002 准备好 |

### 5.6 `sending_plan_recipients`（业务流叫 SendingPlanTarget）

| 业务流 ER §9.8 | 实际 Schema | 备注 |
| --- | --- | --- |
| `current_step` | ❌ 不在这表，在 `sequence_enrollments.current_step` | ✅ 拆得更细 |
| `status`（5 态联系人级） | ❌ 不在这表，在 `sequence_enrollments.status`（4 态） + `emails.status`（每封邮件） | **重要差异**：实际把"联系人在计划中状态"和"每封邮件状态"分开 |
| `replied_at` | ❌ 不在这表，在 `emails.replied_at` 每封邮件 | 同上 |
| — | 实际有 `appended_after_start / excluded_at / excluded_reason / locked_at` | 实际更细致 |

### 5.7 `emails` / `email_events`（业务流叫 EmailSendLog）

| 业务流 ER §9.8 | 实际 Schema | 备注 |
| --- | --- | --- |
| `EmailSendLog`（单一表） | `emails`（实例 + 状态）+ `email_events`（事件流） | 拆为两层 |
| `smtp_response` | 实际是 `engagelab_message_id`（D-002 架构 C 一致） | ✅ 走 EngageLab 而非 SMTP |
| `raw_smtp_error` | ❌ 实际无显式字段（可能在 email_events.metadata） | ⚠️ 业务流 §4.6 "1.0 不区分失败但日志保留"——需确认错误信息存哪 |
| 状态机（5 态：未开始/投递中/投递完成/已回复/已取消） | `emails.status varchar(20)` 取值待跑 SQL 确认 | ⚠️ 需查 `SELECT DISTINCT status FROM emails` 看实际取值 |
| 回信字段（业务流没要求） | `reply_message_id / reply_from_email / reply_subject / reply_body_text / reply_received_at` | **意外发现**：实际 schema **预留了 EngageLab Inbound 回信字段**！但 D-007 决策放弃 Inbound—— **这些字段是否使用？** |

### 5.8 `data_sources` / `data_source_credentials`

| 业务流 §1.4 凭证管理 | 实际 Schema | 备注 |
| --- | --- | --- |
| 数据源凭证 | `data_source_credentials` | ✅ |
| 多账号轮换（Phase 2） | 实际有 `rotation_order / current_day_used / current_day_reset_at / consecutive_error_count` | ⚠️ **意外发现**：实际 schema **已经支持多账号轮换**，业务流标"Phase 2 才做"—— Phase 1 已经做了 |

### 5.9 邮件域名预热

| 业务流 §4.4 | 实际 Schema | 备注 |
| --- | --- | --- |
| 平台级 admin 配 warmup_rules | `warmup_rules + warmup_rule_levels` | ✅ |
| 域名预热档位 | `domain_warmup_status`（含 `spf_record / dkim_record / dmarc_record / verification_status`） | ✅ **D-002 架构 C 关键字段实际已存在！** |
| 每日发送配额 | `domain_daily_usage` | ✅ |
| 历史轨迹 | `domain_warmup_history` | ✅ 业务流 ER 未画 |

**重要**：D-002 架构 C 的"租户域名 + EngageLab 验证 + DKIM/SPF 记录"——**实际 schema 的 `domain_warmup_status` 已经有这些字段**，只是当前业务流未关联到 D-002。**`domain_warmup_status` 可能就是 `tenant_email_domains`！** 不需要新建表。

---

## 6. 已跑扩展 SQL 结果（2026-05-05 用户）

### 6.1 ① alembic head = `20260423_0006`（**严重落后**）

代码仓库 [`backend/alembic/versions/`](../../backend/alembic/versions/) 有 13 个迁移，head 应该是 `20260501_0013`。**生产 PG 落后 7 个迁移、12 天**。

| 迁移 | 日期 | 说明 | 跑了？ | 影响（与§D 偏差对照证据）|
| --- | --- | --- | --- | --- |
| 0001 | 2026-04-21 | canonical_schema | ✅ | 整个 schema 基础 |
| 0002 | 2026-04-21 | seed_and_partitions | ✅ | 月度分区已建（articles_p_2026_04 等） |
| 0003 | 2026-04-22 | scoring_jobs | ✅ | scoring_jobs 表存在 |
| 0004 | 2026-04-22 | tenant_ai_provider | ✅ | tenant_ai_provider_configs 存在 |
| 0005 | 2026-04-23 | drop_source_type_check | ✅ | data_sources CHECK 已删 |
| 0006 | 2026-04-23 | email_template_design | ✅ | platform_email_templates.body_design 存在 |
| 0007 | 2026-04-29 | collection_task_type | ❌ | `collection_tasks` 缺 `task_type` / `context` 字段 |
| 0008 | 2026-04-29 | competitor_enrichment | ❌ | `competitor_companies` 缺 source_id/esdate/legalperson/reg_capital/paid_capital/reg_address/contact_address 等富集字段 |
| 0009 | 2026-04-30 | phase1_collection_schema | ❌ | Phase 1 采集 schema 未应用——**业务流 R-2 阻塞** |
| 0010 | 2026-05-01 | add_default_partitions | ❌ | 缺 DEFAULT 分区，跨月 INSERT 时可能 CheckViolationError |
| 0011 | 2026-05-01 | drop_ai_model_pricing_columns | ❌（但实际字段已不存在） | no-op（设计稿先行更新） |
| 0012 | 2026-05-01 | waimaotong_raw_contacts | ❌ | **`waimaotong_raw_contacts` 表不存在**——之前 §1 困惑解开 |
| 0013 | 2026-05-01 | drop_ai_fallback | ❌ | `ai_scene_defaults.fallback_model_ids` 字段仍在；`ai_models.model_type` 实际已不在（设计稿先行） |

### 6.2 ② `emails.status` 分布 = **空**

生产数据库**从未真实发过任何邮件**。

| 含义 | 印证 |
| --- | --- |
| sending worker 完全没启动 | R-1：4 worker 全部未部署（D-006） |
| 邮件 5 态实际取值无法从生产数据观察 | 5 态实际取值需从代码层确认（推测：sequence_enrollments.status 取值 + emails.status 取值） |
| 邮件投递流程在 R-1 中**完全没跑通** | 业务流 R-3 是 V3 必补；不是"已 ready" |

### 6.3 ③ tenants 当前 5 行

| slug | status | 推测 |
| --- | --- | --- |
| `t-019dbb27` | archived | 早期测试租户（snowflake/uuid 风格 slug） |
| `t-019dbb14` | archived | 早期测试租户 |
| `globex-pcb` | archived | 业务流未提，可能是销售演示用 |
| `t-019dc236` | **active** | 当前活跃测试租户 |
| `t-019dc238` | **active** | 当前活跃测试租户 |

| 含义 | 印证 |
| --- | --- |
| 租户基础（UC-02 创建租户）✅ ready | R-1 已部署的 backend / admin 跑得通租户管理 |
| 2 个 active 租户可作 V3 E2E 测试基础 | [`inputs/test-data/`](../inputs/test-data/) 模板里待你填的"测试租户 A/B" → 可直接复用 `t-019dc236` + `t-019dc238` |
| 3 个 archived → 不影响新功能开发 | 数据回收处理已有先例 |

---

## 7. 决策汇总（按优先级）

| # | 决策项 | 影响范围 | 建议 | 用户拍板 |
| --- | --- | --- | --- | --- |
| **D-008** | 架构模型 = shared + sources（不是 6 raw + clean） | 业务流 §2.2/2.3/§5/§9.3/§9.4 全部修订 | (A) 接受实际架构 | ⬜ |
| **D-009** | UC-11 已收录关键词跨租户复用 → 推迟到 V3.1+ | 范围裁剪 | 接受推迟 | ⬜ |
| **D-010** | 业务流 ER 命名按实际 Schema 对齐 | 业务流文档修订 | 全部以实际为准（CleanCompany→shared_companies 等） | ⬜ |
| **D-011** | `tenant_companies.is_curated` 字段是否需要 | 私有状态字段 ① 实现方式 | 加独立 bool 字段（替代 tags 中放标志） | ⬜ |
| **D-012** | `tenant_companies.matched_keywords[]` 是否需要 | 业务流 §3.4 多关键词命中场景 | 实际只有 keyword_id，需补 jsonb 字段或独立关联表 | ⬜ |
| **D-013** | `domain_warmup_status` 充当 D-002 `tenant_email_domains` | 不再新建 tenant_email_domains 表 | 接受复用 | ⬜ |
| **D-014** | `emails` 表预留的 `reply_*` 字段是否启用 | 与 D-007"放弃 Inbound"冲突 | 字段保留（schema 已建），但 V3 不写入 | ⬜ |
| **D-015** | 励销云数据落点 = `competitor_companies`（不是 lixiaoyun_raw_*） | 业务流 §2.1 路径 B 改写 | 接受 | ⬜ |
| **D-016** | 数据源多账号轮换实际已实现（不是 Phase 2） | 业务流"1.0 不做" 项需删除 | 接受 → 业务流 UC-16 异常 A3 修订 | ⬜ |
| **D-017** 🔴 | **alembic head=0006 落后 7 个迁移**——V3 部署前 Slice 0 必须先 `alembic upgrade head`，含潜在 schema 风险 | R-2 / R-3 阻塞前置；7 个迁移含表创建（0012 加 waimaotong_raw_contacts）+ 列添加（0007/0008）+ 列删除（0011/0013，已为 no-op）+ 分区（0010） | 强烈建议：(a) staging 库先跑迁移验证；(b) 跑前 pg_dump 全量备份；(c) 跑后跑 §6.1 表检查再确认 head=0013 | ⬜ |
| **D-018** 🔴 | emails 表空（生产从未发邮件）→ sending worker / R-3 邮件投递在 R-1 中**完全 0%**；预热档位 / EngageLab 集成均未真实跑过 | R-3"邮件投递流程 ready"完全是 V3 新建工作（不是补缺口） | 接受：R-3 当作 from-scratch 实施 | ⬜ |
| **D-019** | V3 E2E 测试租户复用 `t-019dc236` + `t-019dc238` 现有 active 租户 | inputs/test-data/test-materials.md 待你填的"测试租户 A/B" → 直接复用 | 接受 | ⬜ |

---

## 8. 后续动作

- 用户**逐条**在 §7 决策表上 ✅/✏️/❌
- 决策完成后，AI 同步：
  - 修订 [`v3-target-spec.md` §9 Data Objects + §10 RLS 表清单](00-v3-target-spec.md)（按用户决策版本）
  - 修订 [`04-open-questions.md`](../04-open-questions.md) 关闭 D-008~D-016
  - 在 `_control/inputs/database/schema.sql` 旁加注："此为 v0 设计稿，权威以 schema-current-2026-05-05.md 为准；详细偏差见 02-er-schema-divergence.md"
  - **不修改** `docs/business-flow-DRAFT.md`（按 [`AGENTS.md` §3 硬性禁止](../../AGENTS.md#3-硬性禁止) 不动 docs/）
