# 14 数据迁移方案

> **版本**: v1.0
> **日期**: 2026-04-17
> **输入文档**: `01_DATA_MODEL.md`（源 Schema）, `09_DATABASE_DESIGN.md`（目标 Schema §12）
> **目标读者**: AI Agent（解析迁移步骤）+ 后端工程师（执行迁移）

---

## 目录

1. [迁移概述](#1-迁移概述)
2. [迁移策略](#2-迁移策略)
3. [主键迁移：SERIAL → UUID v7](#3-主键迁移serial--uuid-v7)
4. [表级迁移映射](#4-表级迁移映射)
5. [评分体系映射](#5-评分体系映射)
6. [email_plans 状态拆分](#6-email_plans-状态拆分)
7. [迁移脚本执行顺序](#7-迁移脚本执行顺序)
8. [双写过渡方案](#8-双写过渡方案)
9. [数据验证与一致性检查](#9-数据验证与一致性检查)
10. [回滚策略](#10-回滚策略)
11. [迁移工具与脚本规范](#11-迁移工具与脚本规范)

---

## 1. 迁移概述

### 1.1 迁移规模

| 维度 | 源 | 目标 | 变化 |
|------|-----|------|------|
| 表数量 | 12 表 + 1 视图 + 1 函数 | 38 表 + 3 RLS 视图 + RLS 函数 | +26 表 |
| 主键类型 | SERIAL (INT) | UUID v7 | 全量切换 |
| 多租户 | 无 | RLS + `tenant_id` | 全表改造 |
| 评分体系 | A/B/X 三级 | S/A/B/C/D 五级 | 需映射 |
| 邮件模型 | `email_plans` 9 状态单表 | `sending_plans` + `sequence_steps` + `sequence_enrollments` | 拆分 |
| 分区表 | 无 | 3 张（emails / audit_logs / intelligence_articles） | 新增 |

### 1.2 迁移约束

- **零停机**：采用双写过渡，不停服
- **可回滚**：每步有 `down()` 回滚，旧表保留 ≥7 天
- **数据不丢失**：迁移完成后行数校验 + 抽样比对
- **单一默认租户**：现有数据归入 `tenant_slug = 'default'`，后续按需拆分

---

## 2. 迁移策略

采用 **分阶段双写** 策略（见 `09_DATABASE_DESIGN.md` §12）：

```
Phase 1: Schema 创建        ──  CREATE TABLE（可回滚）
Phase 2: 双写启用            ──  应用层同时写新旧表
Phase 3: 历史数据批量迁移    ──  分批 1000 条，带 checkpoint
Phase 4: 数据验证            ──  行数 + 抽样校验
Phase 5: 读切换              ──  应用读取指向新表
Phase 6: 停写旧表            ──  旧表设为只读
Phase 7: 观察期 + 清理       ──  7 天后 DROP 旧表
```

### 2.1 ENUM 类型处理

> `ALTER TYPE ... ADD VALUE` 在 PostgreSQL 中不可在事务内执行，也无法回滚。

**策略**：所有 ENUM 类型在 Phase 1 **第一步**单独执行，不放在事务内。如需回滚，需 `DROP TYPE` + 重建。

---

## 3. 主键迁移：SERIAL → UUID v7

### 3.1 映射表

迁移期间创建临时映射表，维护旧 SERIAL ID → 新 UUID v7 的对应关系：

```sql
CREATE TABLE _migration.id_mapping (
    source_table    TEXT NOT NULL,
    old_id          BIGINT NOT NULL,
    new_id          UUID NOT NULL DEFAULT gen_uuid_v7(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (source_table, old_id)
);

CREATE INDEX idx_id_mapping_new ON _migration.id_mapping(source_table, new_id);
```

### 3.2 UUID v7 生成

```sql
-- 使用 pg_uuidv7 扩展（推荐）
CREATE EXTENSION IF NOT EXISTS pg_uuidv7;

-- 或自定义函数（如扩展不可用）
CREATE OR REPLACE FUNCTION gen_uuid_v7() RETURNS UUID AS $$
DECLARE
    unix_ts_ms BIGINT;
    uuid_bytes BYTEA;
BEGIN
    unix_ts_ms := (EXTRACT(EPOCH FROM clock_timestamp()) * 1000)::BIGINT;
    uuid_bytes := substring(int8send(unix_ts_ms) FROM 3 FOR 6)
                  || gen_random_bytes(10);
    -- 设置版本 7 和变体位
    uuid_bytes := set_byte(uuid_bytes, 6, (get_byte(uuid_bytes, 6) & 15) | 112);
    uuid_bytes := set_byte(uuid_bytes, 8, (get_byte(uuid_bytes, 8) & 63) | 128);
    RETURN encode(uuid_bytes, 'hex')::UUID;
END;
$$ LANGUAGE plpgsql VOLATILE;
```

### 3.3 外键引用解析

迁移时按依赖拓扑顺序处理，确保被引用表先于引用表迁移。外键关系通过 `_migration.id_mapping` 解析：

```sql
-- 示例：迁移 contact_data 时，解析 company 外键
INSERT INTO shared_contacts (id, company_id, name, ...)
SELECT
    m_contact.new_id,
    m_company.new_id,  -- 通过映射表解析
    cd.name, ...
FROM contact_data cd
JOIN _migration.id_mapping m_contact
    ON m_contact.source_table = 'contact_data' AND m_contact.old_id = cd.id
JOIN _migration.id_mapping m_company
    ON m_company.source_table = 'company_data' AND m_company.old_id = cd.id  -- 需通过 sys_company_id 关联
...
```

---

## 4. 表级迁移映射

### 4.1 `company_data` → `shared_companies` + `company_sources` + `tenant_companies`

**拆分逻辑**：原始公司数据拆为三层——共享池基础信息、数据来源追踪、租户关联。注意：由于 `shared_companies` 需要去重，不能继续直接复用逐行 `company_data.id -> new_id` 的映射结果；必须先生成“去重后的 canonical company 映射”。

```sql
-- Step 0: 建立去重后的 canonical company 映射
CREATE TABLE _migration.company_canonical_map AS
SELECT
    cd.id AS old_company_row_id,
    FIRST_VALUE(gen_uuid_v7()) OVER (
        PARTITION BY COALESCE(domain, company_name || '::' || COALESCE(country, ''))
        ORDER BY cd.created_at DESC
    ) AS canonical_company_id,
    COALESCE(domain, company_name || '::' || COALESCE(country, '')) AS dedupe_key
FROM company_data cd;

-- Step 1: 去重后写入 shared_companies（以 domain 或 company_name+country 去重）
INSERT INTO shared_companies (id, name, country, domain, industry, raw_data, created_at)
SELECT DISTINCT ON (ccm.dedupe_key)
    ccm.canonical_company_id,
    cd.company_name,
    cd.country,
    cd.domain,
    NULL,  -- industry 需从 company_analysis 补充
    cd.raw_data,
    cd.created_at
FROM company_data cd
JOIN _migration.company_canonical_map ccm
    ON ccm.old_company_row_id = cd.id
ORDER BY ccm.dedupe_key,
         cd.created_at DESC;  -- 保留最新

-- Step 2: 写入 company_sources
INSERT INTO company_sources (id, company_id, source_type, source_id, source_data, first_seen_at)
SELECT
    gen_uuid_v7(),
    ccm.canonical_company_id,
    cd.source_type,
    COALESCE(cd.company_id, cd.api_company_id),
    jsonb_build_object('source_keyword', cd.source_keyword, 'source_tags', cd.source_tags),
    cd.created_at
FROM company_data cd
JOIN _migration.company_canonical_map ccm
    ON ccm.old_company_row_id = cd.id;

-- Step 3: 写入 tenant_companies（所有公司归入默认租户）
INSERT INTO tenant_companies (id, tenant_id, company_id, status, grade, created_at)
SELECT
    gen_uuid_v7(),
    (SELECT id FROM tenants WHERE slug = 'default'),
    ccm.canonical_company_id,
    'active',
    NULL,  -- grade 在 company_scores 迁移时处理
    cd.created_at
FROM company_data cd
JOIN _migration.company_canonical_map ccm
    ON ccm.old_company_row_id = cd.id;
```

**去重规则**：

| 优先级 | 去重键 | 说明 |
|--------|--------|------|
| 1 | `domain`（非空时） | 同域名视为同一公司 |
| 2 | `company_name + country` | 无域名时按名称+国家去重 |
| 3 | 取 `created_at` 最新记录 | 多条重复时保留最新 |

### 4.2 `contact_data` → `shared_contacts` + `tenant_contacts`

```sql
-- Step 1: shared_contacts
INSERT INTO shared_contacts (id, company_id, name, title, department, email, phone,
                             linkedin_url, source, raw_data, created_at)
SELECT
    m_contact.new_id,
    ccm.canonical_company_id,
    cd.name,
    cd.position,       -- position → title
    cd.department,
    cd.email,
    COALESCE(cd.phone, cd.mobile),
    cd.linkedin,
    cd.source,
    cd.raw_data,
    cd.created_at
FROM contact_data cd
JOIN _migration.id_mapping m_contact
    ON m_contact.source_table = 'contact_data' AND m_contact.old_id = cd.id
LEFT JOIN _migration.company_canonical_map ccm
    ON ccm.old_company_row_id = (
        SELECT d.id FROM company_data d
        WHERE d.sys_company_id = cd.sys_company_id
        LIMIT 1
    );

-- Step 2: tenant_contacts
INSERT INTO tenant_contacts (id, tenant_id, contact_id, tenant_company_id, status, grade, created_at)
SELECT
    gen_uuid_v7(),
    (SELECT id FROM tenants WHERE slug = 'default'),
    m_contact.new_id,
    tc.id,  -- 从已迁移的 tenant_companies 查
    'active',
    -- 联系人 A/B/X → A/B/C/D 映射（见 §5.2）
    CASE
        WHEN classify_contact(cd.position, cd.company_id).contact_category = 'A' THEN 'A'
        WHEN classify_contact(cd.position, cd.company_id).contact_category = 'B' THEN 'B'
        ELSE 'C'  -- X → C
    END,
    cd.created_at
FROM contact_data cd
JOIN _migration.id_mapping m_contact
    ON m_contact.source_table = 'contact_data' AND m_contact.old_id = cd.id
LEFT JOIN tenant_companies tc
    ON tc.company_id = (
        SELECT ccm2.canonical_company_id FROM _migration.company_canonical_map ccm2
        WHERE ccm2.old_company_row_id = (
            SELECT d.id FROM company_data d
            WHERE d.sys_company_id = cd.sys_company_id LIMIT 1
        )
    )
    AND tc.tenant_id = (SELECT id FROM tenants WHERE slug = 'default');
```

### 4.3 `company_analysis` → `company_scores`

见 [§5 评分体系映射](#5-评分体系映射)。

### 4.4 `keyword_list` → `collection_keywords`

```sql
INSERT INTO collection_keywords (id, tenant_id, keyword, countries, status,
                                  daily_limit, current_page, total_pages, created_at)
SELECT
    m.new_id,
    (SELECT id FROM tenants WHERE slug = 'default'),
    kl.keyword,
    kl.country,  -- JSONB 直接映射
    CASE kl.status
        WHEN 'pending' THEN 'pending'
        WHEN 'running' THEN 'active'
        WHEN 'done'    THEN 'completed'
        WHEN 'paused'  THEN 'paused'
        WHEN 'error'   THEN 'failed'
    END,
    kl.daily_limit,
    kl.current_page,
    kl.total_pages,
    kl.created_at
FROM keyword_list kl
JOIN _migration.id_mapping m
    ON m.source_table = 'keyword_list' AND m.old_id = kl.id;
```

### 4.5 `email_templates` → `email_templates`（新）

```sql
INSERT INTO email_templates (id, tenant_id, name, subject_template, body_template,
                              language, category, is_active, created_at)
SELECT
    m.new_id,
    (SELECT id FROM tenants WHERE slug = 'default'),
    et.name,
    et.subject_template,
    et.body_template,
    et.language,
    'outreach',  -- 默认类型
    et.is_active,
    et.created_at
FROM email_templates et
JOIN _migration.id_mapping m
    ON m.source_table = 'email_templates' AND m.old_id = et.id;
```

### 4.6 `email_plans` → `sending_plans` + `sequence_steps`

见 [§6 email_plans 状态拆分](#6-email_plans-状态拆分)。

### 4.7 `email_drafts` → `emails`（分区表）

```sql
-- 先建立 plan root 映射：每个旧 plan 都映射到所属链路根节点
CREATE TABLE _migration.plan_root_map AS
WITH RECURSIVE plan_chain AS (
    SELECT id, id AS root_id
    FROM email_plans
    WHERE linked_plan_id IS NULL
    UNION ALL
    SELECT ep.id, pc.root_id
    FROM email_plans ep
    JOIN plan_chain pc ON ep.linked_plan_id = pc.id
)
SELECT * FROM plan_chain;

INSERT INTO emails (id, tenant_id, plan_id, tenant_contact_id, step_id, step_number, enrollment_id,
                     from_email, to_email, subject, body_html,
                     status, sent_at, created_at)
SELECT
    m_draft.new_id,
    (SELECT id FROM tenants WHERE slug = 'default'),
    m_root.new_id,
    m_contact.new_id,
    ssm.new_step_id,
    ssm.step_number,
    NULL,  -- enrollment_id 在 §6.5 统一回填
    NULL,  -- from_email 从发送计划继承
    ed.email,
    ed.subject,
    ed.body_target,
    CASE ed.send_status
        WHEN 'draft'    THEN 'draft'
        WHEN 'approved' THEN 'scheduled'
        WHEN 'sent'     THEN 'delivered'  -- 假设已发送=已投递
        WHEN 'failed'   THEN 'failed'
    END,
    ed.sent_at,
    ed.created_at
FROM email_drafts ed
JOIN _migration.id_mapping m_draft
    ON m_draft.source_table = 'email_drafts' AND m_draft.old_id = ed.id
LEFT JOIN _migration.plan_root_map prm
    ON prm.id = ed.plan_id
LEFT JOIN _migration.id_mapping m_root
    ON m_root.source_table = 'email_plans' AND m_root.old_id = prm.root_id
LEFT JOIN _migration.sequence_step_map ssm
    ON ssm.old_plan_id = ed.plan_id
LEFT JOIN _migration.id_mapping m_contact
    ON m_contact.source_table = 'contact_data'
    AND m_contact.old_id = (
        SELECT c.id FROM contact_data c
        WHERE c.sys_contact_id = ed.sys_contact_id LIMIT 1
    );
```

**注意**：`emails` 是分区表，`created_at` 决定分区路由。确保迁移前已创建覆盖历史数据时间范围的所有分区。

### 4.8 `system_config` → `tenants.settings` + `ai_models` + `data_source_credentials`

```sql
-- 租户级设置
UPDATE tenants SET settings = jsonb_build_object(
    'mail_daily_limit', (SELECT value::INT FROM system_config WHERE key = 'mail.daily_limit'),
    'timezone', 'Asia/Shanghai'
)
WHERE slug = 'default';

-- AI 模型配置
INSERT INTO ai_models (id, name, provider, model_id, input_price_per_1k, output_price_per_1k, is_active)
VALUES (gen_uuid_v7(), 'GPT-4o', 'openrouter', 'openai/gpt-4o', 0.0025, 0.01, TRUE);

-- 数据源凭证
INSERT INTO data_source_credentials (id, tenant_id, source_type, credentials, is_active)
SELECT
    gen_uuid_v7(),
    (SELECT id FROM tenants WHERE slug = 'default'),
    'waimao_tong',
    jsonb_build_object(
        'token', (SELECT value FROM system_config WHERE key = 'auth.qiye_token'),
        'sess', (SELECT value FROM system_config WHERE key = 'auth.qiye_sess'),
        'uid', (SELECT value FROM system_config WHERE key = 'auth.qiye_uid')
    ),
    TRUE;
```

### 4.9 废弃表处理

| 旧表 | 处理 | 原因 |
|------|------|------|
| `flow_runs` | 废弃 | Prefect 自带运行记录 |
| `scheduled_tasks` | 概念映射到 `collection_tasks` | 结构完全不同，无法字段映射 |
| `product_industry_config` | 内嵌到 `scoring_templates.rules` JSONB | 行业配置变为租户级评分规则 |
| `draft_rewrite_logs` | 纳入 `audit_logs` | 统一审计 |
| `v_buyer_contacts` 视图 | 废弃 | 被 RLS 视图 `v_tenant_visible_contacts` 替代 |
| `classify_contact()` 函数 | 废弃 | 被 `contact_rules` JSONB 规则引擎替代 |

---

## 5. 评分体系映射

### 5.1 公司评分：A/B/X → S/A/B/C/D

现有 `company_analysis` 使用三维评分（relevance / market_fit / intent，满分 100）+ A/B/X 等级。

新系统使用 `scoring_templates` JSONB 规则引擎 + S/A/B/C/D 五级。

**映射规则**：

| 旧等级 | 旧 score 范围 | 新等级 | 映射逻辑 |
|--------|--------------|--------|---------|
| A | ≥ 80 | S | 旧 A 级中的高分段 |
| A | 60-79 | A | 旧 A 级中的中低分段 |
| B | ≥ 50 | B | 旧 B 级 |
| B | < 50 | C | 旧 B 级低分 |
| X | 任意 | D | 未匹配 |
| _(无等级)_ | _(无分数)_ | D | 缺数据默认 |

```sql
-- 迁移 company_analysis → company_scores
INSERT INTO company_scores (id, tenant_company_id, template_version_id,
                             total_score, grade, dimension_scores, scored_at)
SELECT
    gen_uuid_v7(),
    tc.id,
    (SELECT id FROM scoring_template_versions
     WHERE template_id = (SELECT id FROM scoring_templates
                          WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'default')
                          LIMIT 1)
     ORDER BY version DESC LIMIT 1),
    ca.score,
    CASE
        WHEN ca.grade = 'A' AND ca.score >= 80 THEN 'S'
        WHEN ca.grade = 'A' THEN 'A'
        WHEN ca.grade = 'B' AND ca.score >= 50 THEN 'B'
        WHEN ca.grade = 'B' THEN 'C'
        ELSE 'D'
    END,
    COALESCE(ca.score_details, '{}')::JSONB,
    ca.created_at
FROM company_analysis ca
JOIN _migration.id_mapping m_company
    ON m_company.source_table = 'company_data'
    AND m_company.old_id = (
        SELECT cd.id FROM company_data cd
        WHERE cd.sys_company_id::TEXT = ca.company_id
           OR cd.company_id = ca.company_id
        LIMIT 1
    )
JOIN tenant_companies tc
    ON tc.company_id = m_company.new_id
    AND tc.tenant_id = (SELECT id FROM tenants WHERE slug = 'default');

-- 同步 grade 到 tenant_companies
UPDATE tenant_companies tc
SET grade = cs.grade
FROM company_scores cs
WHERE cs.tenant_company_id = tc.id;
```

### 5.2 联系人分级：A/B/X → A/B/C/D

| 旧等级（classify_contact 函数） | 新等级 | 说明 |
|---------------------------------|--------|------|
| A（决策层：CEO/VP/采购总监） | A | 直接映射 |
| B（管理层：经理/工程师） | B | 直接映射 |
| X（未匹配） | C | 降为执行层（而非 D） |
| _(无分级)_ | D | 缺数据默认其他 |

### 5.3 默认评分模板初始化

迁移前需先创建默认租户的评分模板，将现有 `product_industry_config` 的 16 类 PCB 行业转化为 JSONB 规则：

```sql
-- 创建默认评分模板
INSERT INTO scoring_templates (id, tenant_id, name, is_active, created_at)
VALUES (gen_uuid_v7(),
        (SELECT id FROM tenants WHERE slug = 'default'),
        '默认评分模板（从 PCB 行业配置迁移）',
        TRUE, now());

-- 创建初始版本，将 product_industry_config 转为 rules JSONB
INSERT INTO scoring_template_versions (id, template_id, version, rules, created_at)
SELECT
    gen_uuid_v7(),
    st.id,
    1,
    jsonb_build_object('dimensions', jsonb_agg(
        jsonb_build_object(
            'id', 'industry_' || pic.id,
            'name', pic.name,
            'weight', ROUND(100.0 / COUNT(*) OVER ()),
            'type', 'rule',
            'rules', jsonb_build_array(
                jsonb_build_object('condition', 'industry_contains', 'values', pic.keywords, 'score', 100),
                jsonb_build_object('condition', 'default', 'score', 20)
            )
        )
    )),
    now()
FROM product_industry_config pic
CROSS JOIN scoring_templates st
WHERE st.name LIKE '默认评分模板%'
  AND pic.enabled = TRUE
GROUP BY st.id;
```

---

## 6. email_plans 状态拆分

### 6.1 现有模型

`email_plans` 承载 9 种状态，混合了采集、清洗、生成、发送等不同阶段：

```
draft → approved → keyword_gen → collecting → cleaning → generating → pending_approval → sending → done
```

### 6.2 目标模型

新系统将其拆分为独立关注点：

| 现有概念 | 新表 | 说明 |
|---------|------|------|
| 计划主体 | `sending_plans` | 发送计划基本信息 |
| 关键词+采集 | `collection_keywords` + `collection_tasks` | 独立采集服务 |
| 清洗+评分 | `company_scores` + `scoring_templates` | 独立评分体系 |
| 邮件生成 | `sequence_steps`（模板） + `emails`（实例） | 序列化邮件 |
| 发送执行 | `sequence_enrollments` + `emails` | 序列驱动发送 |

### 6.2.1 历史计划迁移决策

为保证迁移后行为可实现且不误发邮件，发送链采用以下统一策略：

1. **终态历史计划只读归档**：旧系统已结束的链路迁移后只保留统计与时间线，不再继续执行。
2. **迁移窗口内未终态链路可继续执行**：旧系统仍在 `sending` 且存在后续待发轮次的链路，迁移后保留为可继续执行。
3. **默认先落为 `paused` 再人工恢复**：所有“可继续执行”链路迁移后统一进入 `paused`，由运营在新系统核验后显式 `resume`。
4. **sequence_enrollments 是执行真源**：恢复执行时只看迁移后的 `sequence_enrollments.current_step / next_step_due_at / status`，不再读取旧 `email_plans`。

### 6.3 迁移 SQL

```sql
-- email_plans → sending_plans
INSERT INTO sending_plans (id, tenant_id, created_by, name, description, status,
                            recipient_source, recipient_config, send_strategy,
                            created_at, updated_at)
SELECT
    m.new_id,
    (SELECT id FROM tenants WHERE slug = 'default'),
    (SELECT id FROM users WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'default') ORDER BY created_at LIMIT 1),
    ep.plan_name,
    ep.description,
    CASE ep.status
        WHEN 'draft'             THEN 'draft'
        WHEN 'approved'          THEN 'draft'
        WHEN 'keyword_gen'       THEN 'draft'
        WHEN 'collecting'        THEN 'draft'
        WHEN 'cleaning'          THEN 'draft'
        WHEN 'generating'        THEN 'draft'
        WHEN 'pending_approval'  THEN 'paused'
        WHEN 'sending'           THEN 'paused'
        WHEN 'done'              THEN 'completed'
    END,
    'manual',
    '{"migrated_from":"email_plans"}'::jsonb,
    jsonb_build_object(
        'timezone_aware', true,
        'preferred_hours', jsonb_build_array(9, 17),
        'interval_minutes', 5,
        'migrated_from', 'legacy_email_plans'
    ),
    ep.created_at,
    ep.updated_at
FROM email_plans ep
JOIN _migration.id_mapping m
    ON m.source_table = 'email_plans' AND m.old_id = ep.id;

CREATE TABLE _migration.sequence_step_map (
    old_plan_id BIGINT PRIMARY KEY,
    root_plan_id BIGINT NOT NULL,
    new_plan_id UUID NOT NULL,
    new_step_id UUID NOT NULL,
    step_number INTEGER NOT NULL
);

-- 为每个计划的每一轮创建 sequence_step
INSERT INTO sequence_steps (id, plan_id, tenant_id, step_number, template_id,
                            delay_days, condition_type, use_ai_personalization,
                            created_at, updated_at)
SELECT
    gen_uuid_v7(),
    m.new_id,
    (SELECT id FROM tenants WHERE slug = 'default'),
    ep.round_number,
    (SELECT id FROM email_templates ORDER BY created_at LIMIT 1),
    COALESCE(ep.interval_days, 0),
    CASE WHEN ep.round_number = 1 THEN 'always' ELSE 'no_reply' END,
    false,
    ep.created_at,
    ep.updated_at
FROM email_plans ep
JOIN _migration.id_mapping m
    ON m.source_table = 'email_plans' AND m.old_id = ep.id;

INSERT INTO _migration.sequence_step_map (old_plan_id, root_plan_id, new_plan_id, new_step_id, step_number)
SELECT
    ep.id,
    prm.root_id,
    m_root.new_id,
    ss.id,
    ep.round_number
FROM email_plans ep
JOIN _migration.plan_root_map prm ON prm.id = ep.id
JOIN _migration.id_mapping m_root
  ON m_root.source_table = 'email_plans' AND m_root.old_id = prm.root_id
JOIN sequence_steps ss
  ON ss.plan_id = m_root.new_id
 AND ss.step_number = ep.round_number;
```

### 6.4 linked_plan_id 处理

现有 `email_plans.linked_plan_id` 实现多轮跟进。新系统中多轮由 `sequence_steps` 表达：

- 同一 `sending_plan` 下的多个 `sequence_steps`（按 `step_number` 排序）= 现有多轮
- 旧系统中通过 `linked_plan_id` 关联的计划链，合并为同一个 `sending_plan` 的多个 steps

```sql
-- 使用 _migration.plan_root_map 统一把 linked plan 链收敛到根计划
UPDATE sequence_steps ss
SET plan_id = m_root.new_id
FROM _migration.plan_root_map prm
JOIN _migration.id_mapping m_this ON m_this.source_table = 'email_plans' AND m_this.old_id = prm.id
JOIN _migration.id_mapping m_root ON m_root.source_table = 'email_plans' AND m_root.old_id = prm.root_id
WHERE ss.plan_id = m_this.new_id
  AND prm.root_id != prm.id;  -- 仅更新非根节点

-- 同步修正 emails.plan_id，避免后续删除非根 sending_plans 后出现孤儿邮件
UPDATE emails e
SET plan_id = m_root.new_id
FROM _migration.plan_root_map prm
JOIN _migration.id_mapping m_this ON m_this.source_table = 'email_plans' AND m_this.old_id = prm.id
JOIN _migration.id_mapping m_root ON m_root.source_table = 'email_plans' AND m_root.old_id = prm.root_id
WHERE e.plan_id = m_this.new_id
  AND prm.root_id != prm.id;

-- 删除非根节点产生的冗余 sending_plans
DELETE FROM sending_plans
WHERE id IN (
    SELECT m.new_id
    FROM email_plans ep
    JOIN _migration.id_mapping m ON m.source_table = 'email_plans' AND m.old_id = ep.id
    WHERE ep.linked_plan_id IS NOT NULL
);
```

### 6.5 `sequence_enrollments` 迁移

`sequence_enrollments` 是发送链恢复执行的真源，需要按“根计划 + 联系人”聚合构建：

```sql
CREATE TABLE _migration.enrollment_seed AS
SELECT
    e.plan_id,
    e.tenant_contact_id,
    MAX(e.step_number) AS current_step,
    MIN(e.created_at) AS enrolled_at,
    MAX(e.sent_at) AS last_step_sent_at,
    BOOL_OR(e.status = 'replied') AS has_replied,
    BOOL_OR(e.status = 'bounced') AS has_bounced,
    BOOL_OR(e.status = 'unsubscribed') AS has_unsubscribed
FROM emails e
GROUP BY e.plan_id, e.tenant_contact_id;

INSERT INTO sequence_enrollments (
    id, plan_id, tenant_id, tenant_contact_id,
    current_step, status, enrolled_at, last_step_sent_at,
    next_step_due_at, completed_at, created_at, updated_at
)
SELECT
    gen_uuid_v7(),
    es.plan_id,
    (SELECT id FROM tenants WHERE slug = 'default'),
    es.tenant_contact_id,
    es.current_step,
    CASE
        WHEN es.has_replied      THEN 'replied'
        WHEN es.has_bounced      THEN 'bounced'
        WHEN es.has_unsubscribed THEN 'unsubscribed'
        WHEN sp.status = 'completed' THEN 'completed'
        WHEN sp.status = 'paused'    THEN 'paused'
        ELSE 'active'
    END,
    es.enrolled_at,
    es.last_step_sent_at,
    CASE
        WHEN es.has_replied OR es.has_bounced OR es.has_unsubscribed THEN NULL
        WHEN sp.status = 'completed' THEN NULL
        WHEN next_ss.id IS NULL THEN NULL
        ELSE es.last_step_sent_at + make_interval(days => next_ss.delay_days)
    END,
    CASE
        WHEN es.has_replied OR es.has_bounced OR es.has_unsubscribed OR sp.status = 'completed'
        THEN COALESCE(es.last_step_sent_at, es.enrolled_at)
        ELSE NULL
    END,
    es.enrolled_at,
    NOW()
FROM _migration.enrollment_seed es
JOIN sending_plans sp ON sp.id = es.plan_id
LEFT JOIN sequence_steps next_ss
  ON next_ss.plan_id = es.plan_id
 AND next_ss.step_number = es.current_step + 1;

UPDATE emails e
SET enrollment_id = se.id
FROM sequence_enrollments se
WHERE e.plan_id = se.plan_id
  AND e.tenant_contact_id = se.tenant_contact_id
  AND e.enrollment_id IS NULL;
```

### 6.6 历史计划“继续执行 vs 归档”判定

```sql
CREATE TABLE _migration.plan_execution_policy AS
SELECT
    prm.root_id,
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM email_plans ep
            WHERE ep.id = prm.root_id
              AND ep.status = 'sending'
        ) THEN 'resumable_paused'
        ELSE 'readonly_archive'
    END AS migration_policy
FROM _migration.plan_root_map prm
GROUP BY prm.root_id;
```

`readonly_archive` 链路只保留时间线和统计，不再继续执行。  
`resumable_paused` 链路保留 `sequence_enrollments`，迁移后默认 `sending_plans.status = paused`，由运营核验后显式 `resume`。

恢复发送前必须完成以下核验：
1. 关联域名仍已验证且有可用额度。
2. 未来步骤模板在新系统中存在且可用。
3. 收件人未退订、未黑名单、未被排除。
4. `sequence_enrollments.next_step_due_at` 已正确回填。

---

## 7. 迁移脚本执行顺序

按依赖拓扑排序，分为 **10 个 Migration 批次**：

| 批次 | Migration | 操作 | 依赖 |
|------|-----------|------|------|
| M01 | ENUM 类型创建 | 创建所有 ENUM（不可事务回滚） | 无 |
| M02 | Schema + 临时表 | `CREATE SCHEMA _migration`; 创建 `id_mapping` 表 | M01 |
| M03 | 平台层表 | `tenants`, `users`, `user_roles`, `ai_models` | M02 |
| M04 | 默认租户初始化 | INSERT 默认租户 + 管理员用户 + 评分模板 | M03 |
| M05 | 共享数据池 | `shared_companies`, `company_sources`, `shared_contacts` | M04 |
| M06 | 租户-公司 | `tenant_companies`, `company_scores` | M05 |
| M07 | 租户-联系人 | `tenant_contacts`, `groups`, `group_members` | M06 |
| M08 | 邮件系统 | `sending_plans`, `sequence_steps`, `sequence_enrollments`, `emails`(含分区), `email_events`, `email_templates` | M06, M07 |
| M09 | 系统支撑 | `collection_keywords`, `collection_tasks`, `audit_logs`(含分区), `notifications`, `domain_warmup_*`, `balance_transactions`, `data_source_credentials` | M04 |
| M10 | 数据迁移 | 执行 §4-§6 的所有 INSERT/UPDATE 语句 | M03-M09 |

```
M01 → M02 → M03 → M04 ─┬─ M05 → M06 → M07 ─┐
                        │                     ├─ M08
                        └─ M09 ───────────────┘
                                              └─ M10
```

### 7.1 分批迁移参数

| 参数 | 值 | 说明 |
|------|-----|------|
| `BATCH_SIZE` | 1,000 | 每批处理行数 |
| `CHECKPOINT_INTERVAL` | 每批写 checkpoint | 记录已处理的 max(old_id) |
| `SLEEP_BETWEEN_BATCHES` | 100ms | 避免锁争用 |
| `MAX_RETRIES` | 3 | 单批失败重试次数 |

---

## 8. 双写过渡方案

### 8.1 双写层实现

在应用层（FastAPI 中间件/Repository 层）实现双写，不使用数据库触发器：

```python
class DualWriteRepository:
    """双写期间同时写入新旧表"""

    def __init__(self, old_repo, new_repo, migration_phase: str):
        self.old_repo = old_repo
        self.new_repo = new_repo
        self.phase = migration_phase  # 'dual_write' | 'new_primary' | 'old_readonly'

    async def create_company(self, data: dict) -> dict:
        if self.phase == 'old_readonly':
            return await self.new_repo.create(data)

        # 写旧表（主）
        old_result = await self.old_repo.create(data)

        # 写新表（异步，允许失败但记录告警）
        try:
            new_data = self._transform_to_new_schema(data, old_result['id'])
            await self.new_repo.create(new_data)
        except Exception as e:
            logger.warning(f"Dual-write to new table failed: {e}")
            # 记入补偿队列
            await self._enqueue_compensation(old_result['id'], data)

        return old_result
```

### 8.2 双写阶段

```
Phase 2a: 双写启动
  ├── 旧表 = 读 + 写（主）
  └── 新表 = 写（副），失败记录补偿队列

Phase 2b: 读切换
  ├── 新表 = 读 + 写（主）
  └── 旧表 = 写（副），仅做备份

Phase 2c: 旧表只读
  ├── 新表 = 读 + 写
  └── 旧表 = 只读（REVOKE INSERT/UPDATE/DELETE）
```

### 8.3 补偿队列

双写失败时记录到补偿表，后台任务定期重试：

```sql
CREATE TABLE _migration.compensation_queue (
    id          BIGSERIAL PRIMARY KEY,
    source_table TEXT NOT NULL,
    old_id      BIGINT NOT NULL,
    operation   TEXT NOT NULL,  -- 'INSERT' / 'UPDATE' / 'DELETE'
    payload     JSONB NOT NULL,
    retries     INT DEFAULT 0,
    status      TEXT DEFAULT 'pending',  -- pending / completed / failed
    created_at  TIMESTAMPTZ DEFAULT now(),
    processed_at TIMESTAMPTZ
);
```

---

## 9. 数据验证与一致性检查

### 9.1 行数校验

```sql
-- 自动生成校验查询
SELECT
    'company_data → shared_companies' AS migration,
    (SELECT COUNT(DISTINCT COALESCE(domain, company_name || country))
     FROM company_data) AS expected,
    (SELECT COUNT(*) FROM shared_companies) AS actual,
    CASE WHEN (SELECT COUNT(DISTINCT COALESCE(domain, company_name || country))
               FROM company_data)
              = (SELECT COUNT(*) FROM shared_companies)
    THEN 'PASS' ELSE 'FAIL' END AS result

UNION ALL

SELECT
    'contact_data → shared_contacts',
    (SELECT COUNT(*) FROM contact_data),
    (SELECT COUNT(*) FROM shared_contacts),
    CASE WHEN (SELECT COUNT(*) FROM contact_data) = (SELECT COUNT(*) FROM shared_contacts)
    THEN 'PASS' ELSE 'FAIL' END

UNION ALL

SELECT
    'email_plans → sending_plans',
    (SELECT COUNT(*) FROM email_plans WHERE linked_plan_id IS NULL),  -- 仅根节点
    (SELECT COUNT(*) FROM sending_plans WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'default')),
    CASE WHEN (SELECT COUNT(*) FROM email_plans WHERE linked_plan_id IS NULL)
              = (SELECT COUNT(*) FROM sending_plans WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'default'))
    THEN 'PASS' ELSE 'FAIL' END

UNION ALL

SELECT
    'email_drafts → emails',
    (SELECT COUNT(*) FROM email_drafts),
    (SELECT COUNT(*) FROM emails WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'default')),
    CASE WHEN (SELECT COUNT(*) FROM email_drafts)
              = (SELECT COUNT(*) FROM emails WHERE tenant_id = (SELECT id FROM tenants WHERE slug = 'default'))
    THEN 'PASS' ELSE 'FAIL' END;
```

### 9.2 抽样比对

每张表随机抽 100 行，逐字段比对关键数据：

```python
SAMPLE_CHECKS = {
    'company': {
        'old_query': "SELECT company_name, country, domain FROM company_data WHERE id = %s",
        'new_query': "SELECT name, country, domain FROM shared_companies WHERE id = %s",
        'field_mapping': {'company_name': 'name', 'country': 'country', 'domain': 'domain'},
    },
    'contact': {
        'old_query': "SELECT name, position, email FROM contact_data WHERE id = %s",
        'new_query': "SELECT name, title, email FROM shared_contacts WHERE id = %s",
        'field_mapping': {'name': 'name', 'position': 'title', 'email': 'email'},
    },
}

async def verify_sample(table_key: str, sample_size: int = 100):
    """抽样比对旧表与新表数据一致性"""
    config = SAMPLE_CHECKS[table_key]
    old_ids = await db.fetch_all(
        f"SELECT old_id, new_id FROM _migration.id_mapping "
        f"WHERE source_table = '{table_key}' ORDER BY random() LIMIT {sample_size}"
    )
    mismatches = []
    for row in old_ids:
        old_data = await db.fetch_one(config['old_query'], row['old_id'])
        new_data = await db.fetch_one(config['new_query'], row['new_id'])
        for old_field, new_field in config['field_mapping'].items():
            if old_data[old_field] != new_data[new_field]:
                mismatches.append({
                    'old_id': row['old_id'], 'field': old_field,
                    'old_value': old_data[old_field], 'new_value': new_data[new_field]
                })
    return {'total': len(old_ids), 'mismatches': len(mismatches), 'details': mismatches}
```

### 9.3 外键完整性

```sql
-- 检查所有 tenant_companies 都有对应的 shared_companies
SELECT COUNT(*) AS orphaned_tenant_companies
FROM tenant_companies tc
LEFT JOIN shared_companies sc ON tc.company_id = sc.id
WHERE sc.id IS NULL;

-- 检查所有 emails 都有对应的 sending_plans
SELECT COUNT(*) AS orphaned_emails
FROM emails e
LEFT JOIN sending_plans sp ON e.plan_id = sp.id
WHERE sp.id IS NULL AND e.plan_id IS NOT NULL;

-- 检查所有 company_scores 都有对应的 tenant_companies
SELECT COUNT(*) AS orphaned_scores
FROM company_scores cs
LEFT JOIN tenant_companies tc ON cs.tenant_company_id = tc.id
WHERE tc.id IS NULL;
```

### 9.4 验证通过标准

| 检查项 | 通过标准 |
|--------|---------|
| 行数校验 | 100% 匹配（考虑去重差异） |
| 抽样比对 | 错误率 < 0.1% |
| 外键完整性 | 孤立记录 = 0 |
| 评分映射 | 所有旧评分都有对应新评分 |
| ID 映射 | `_migration.id_mapping` 覆盖所有旧表记录 |

---

## 10. 回滚策略

### 10.1 逐步回滚矩阵

与 `09_DATABASE_DESIGN.md` §12 一致，补充具体操作：

| 迁移操作 | 回滚命令 | 数据影响 |
|----------|---------|---------|
| M01 ENUM 创建 | `DROP TYPE IF EXISTS xxx CASCADE` | 无数据 |
| M02 Schema + 映射表 | `DROP SCHEMA _migration CASCADE` | 仅临时数据 |
| M03-M09 表创建 | `DROP TABLE IF EXISTS xxx CASCADE` | 无生产数据 |
| M10 数据迁移 | `TRUNCATE TABLE xxx`（新表）| 旧表完整保留 |
| 双写层代码 | 回滚应用代码到旧 Repository | 旧表数据完整 |
| 读切换 | 回滚应用代码，恢复读旧表 | 无数据损失 |

### 10.2 紧急回滚流程

```
1. 停止双写（应用配置 migration_phase = 'disabled'）
2. 回滚应用代码到旧表 Repository
3. 验证旧表服务正常
4. （可选）清空新表数据，保留表结构以便重试
```

### 10.3 不可回滚操作

| 操作 | 原因 | 应对 |
|------|------|------|
| `ALTER TYPE ... ADD VALUE` | PostgreSQL 限制 | 需 DROP TYPE + 重建 |
| 旧表 DROP（Phase 7） | 数据不可恢复 | 执行前完整备份 |

---

## 11. 迁移工具与脚本规范

### 11.1 工具选型

| 工具 | 用途 |
|------|------|
| Alembic | DDL 迁移（CREATE/ALTER/DROP） |
| 自定义 Python 脚本 | DML 迁移（INSERT/UPDATE 数据搬迁） |
| pytest | 迁移验证测试 |

### 11.2 脚本命名规范

```
migrations/
├── versions/
│   ├── 001_create_enums.py              # M01
│   ├── 002_create_migration_schema.py    # M02
│   ├── 003_create_platform_tables.py     # M03
│   ├── 004_init_default_tenant.py        # M04
│   ├── 005_create_shared_pool.py         # M05
│   ├── 006_create_tenant_company.py      # M06
│   ├── 007_create_tenant_contact.py      # M07
│   ├── 008_create_email_system.py        # M08
│   ├── 009_create_support_tables.py      # M09
│   └── 010_migrate_data.py              # M10
├── data/
│   ├── migrate_companies.py
│   ├── migrate_contacts.py
│   ├── migrate_scores.py
│   ├── migrate_plans.py
│   ├── migrate_emails.py
│   └── migrate_config.py
└── verify/
    ├── check_row_counts.py
    ├── check_sample_data.py
    └── check_foreign_keys.py
```

### 11.3 每个迁移脚本必须包含

```python
def upgrade():
    """正向迁移"""
    ...

def downgrade():
    """回滚"""
    ...

def verify():
    """验证迁移结果"""
    ...
```

---

> **文档结束**
> 下一步：`12_COLLECTION_SERVICE.md`（采集服务独立部署架构）
