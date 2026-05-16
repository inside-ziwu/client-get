# 数据模型 - 数据库表结构与关系

> 数据库名：`ft_data` | PostgreSQL
> 共 12 张核心表 + 1 个视图 + 1 个函数

---

## 1. 实体关系图

```
                    email_plans (核心枢纽)
                         │
          ┌──────────────┼──────────────┬──────────────┐
          │              │              │              │
     keyword_list   company_data   email_drafts   (self-ref)
          │              │              │         linked_plan_id
          │              │              │
          │         company_analysis    │
          │              │              │
          │         contact_data ───────┘
          │              │
          │         v_buyer_contacts (VIEW)
          │
     ─────┴─────
     独立表:
     - system_config
     - email_templates
     - product_industry_config
     - flow_runs
     - scheduled_tasks
     - draft_rewrite_logs
```

---

## 2. 表详细结构

### 2.1 `email_plans` - 营销计划（核心表）

**作用**：驱动整个系统的执行单元，每个计划代表一次完整的获客活动。

| 列名 | 类型 | 默认值 | 约束 | 说明 |
|------|------|--------|------|------|
| id | SERIAL | 自增 | PK | |
| plan_name | TEXT | | NOT NULL | 计划名称 |
| description | TEXT | | | 描述 |
| country | TEXT | | | 目标国家 |
| industry | TEXT | | | 目标行业 |
| country_filter | JSONB | | | 国家筛选条件 |
| industry_filter | JSONB | | | 行业筛选条件 |
| status | TEXT | `'draft'` | CHECK 9值 | 生命周期状态 |
| approval_status | TEXT | | | 审批状态 |
| priority | INT | `0` | | 优先级（越大越优先） |
| round_number | INT | `1` | NOT NULL, CHECK(1-7) | 邮件轮次 |
| interval_days | INT | NULL | | 跟进间隔天数 |
| linked_plan_id | INT | NULL | FK→self | 关联的上一轮计划 |
| target_collect | INT | | | 采集目标数 |
| target_clean | INT | | | 清洗目标数 |
| target_send | INT | | | 发送目标数 |
| approved_at | TIMESTAMP | | | 审批时间 |
| created_at | TIMESTAMP | NOW() | | |
| updated_at | TIMESTAMP | NOW() | | |

**状态值**：`draft, approved, keyword_gen, collecting, cleaning, generating, pending_approval, sending, done`

**产品化标注**：
- 缺少 `tenant_id`（多租户必需）
- 缺少 `created_by`（用户归属）
- `linked_plan_id` 自引用设计合理，可保留

---

### 2.2 `keyword_list` - 关键词

| 列名 | 类型 | 默认值 | 约束 | 说明 |
|------|------|--------|------|------|
| id | SERIAL | 自增 | PK | |
| keyword | TEXT | | NOT NULL | 搜索关键词 |
| country | JSONB | | | 目标国家列表 |
| daily_limit | INT | | | 每日采集页数上限 |
| status | TEXT | `'pending'` | | pending/running/done/paused/error |
| plan_id | INT | | FK→email_plans | 所属计划 |
| current_page | INT | | | 当前采集到的页码 |
| total_pages | INT | | | 总页数 |
| today_pages | INT | | | 今日已采集页数 |
| last_run_date | DATE | | | 上次运行日期（用于重置today_pages） |
| error_msg | TEXT | | | 错误信息 |
| created_at | TIMESTAMP | NOW() | | |
| updated_at | TIMESTAMP | NOW() | | |

**索引**：`idx_keyword_list_plan_id (plan_id)`

---

### 2.3 `company_data` - 原始公司数据

**作用**：Flow01 采集的原始公司信息，未经 AI 分析。

| 列名 | 类型 | 默认值 | 约束 | 说明 |
|------|------|--------|------|------|
| id | SERIAL | 自增 | PK | |
| company_id | TEXT | | | 网易外贸通公司ID |
| company_name | TEXT | | | 公司名 |
| country | TEXT | | | 国家 |
| domain | TEXT | | | 官网域名 |
| source_type | TEXT | | | 数据来源类型 |
| source_keyword | TEXT | | | 来源关键词 |
| source_tags | TEXT | | | 来源标签（如"采购商"） |
| detail_status | TEXT | | | 详情获取状态 |
| has_detail | BOOLEAN | | | 是否已获取详情 |
| has_contacts | BOOLEAN | | | 是否已获取联系人 |
| contact_count | INT | | | 联系人数量 |
| email_count | INT | | | 邮箱数量 |
| sys_company_id | UUID | | | 系统内部公司ID |
| api_company_id | TEXT | | | API返回的公司ID |
| raw_data | JSONB | | | 原始API返回数据 |
| plan_id | INT | | FK→email_plans | 所属计划 |
| created_at | TIMESTAMP | NOW() | | |
| updated_at | TIMESTAMP | NOW() | | |

**索引**：`idx_company_data_plan_id (plan_id)`

---

### 2.4 `company_analysis` - 公司分析结果

**作用**：Flow02 的 AI 评级结果，是系统最核心的数据资产。

| 列名 | 类型 | 默认值 | 约束 | 说明 |
|------|------|--------|------|------|
| id | SERIAL | 自增 | PK | |
| company_id | TEXT | | | 公司ID |
| company_name | TEXT | | | |
| english_name | TEXT | | | 英文名 |
| country | TEXT | | | |
| **grade** | TEXT | | | **A/B/X 等级** |
| **score** | INT | | | **综合评分(0-100)** |
| **score_details** | JSONB | | | **三维评分明细** |
| sub_industry | TEXT | | | 细分行业（16类） |
| email_priority | TEXT | | CHECK(selected/skipped) | 是否入选发信 |
| product_tags | JSONB | `'[]'` | | 产品标签 |
| tag_confidence | JSONB | `'{}'` | | 标签置信度 |
| main_business | TEXT | | | 主营业务 |
| products_services | TEXT | | | 产品/服务 |
| match_reasons | JSONB | | | 匹配理由 |
| potential_needs | JSONB | | | 潜在需求 |
| recommended_products | JSONB | | | 推荐产品 |
| sales_approach | TEXT | | | 销售建议 |
| risk_factors | TEXT | | | 风险因素 |
| company_size | TEXT | | | 公司规模 |
| website | TEXT | | | |
| has_trade_data | BOOLEAN | | | 有无海关数据 |
| trade_summary | JSONB | | | 贸易数据摘要 |
| plan_id | INT | | FK→email_plans | 所属计划 |
| is_new_collection | BOOLEAN | | | 是否新采集 |
| created_at | TIMESTAMP | NOW() | | |
| updated_at | TIMESTAMP | NOW() | | |

**score_details 结构**：
```json
{
  "relevance": 35,      // 相关性 (满分40)
  "market_fit": 25,     // 市场匹配度 (满分30)
  "intent": 20          // 意向度 (满分30)
}
```

**唯一约束**（条件索引）：
- `(company_id)` WHERE `plan_id IS NULL`
- `(company_id, plan_id)` WHERE `plan_id IS NOT NULL`
- `(sys_company_id)` WHERE `plan_id IS NULL`
- `(sys_company_id, plan_id)` WHERE `plan_id IS NOT NULL`

---

### 2.5 `contact_data` - 联系人

| 列名 | 类型 | 默认值 | 约束 | 说明 |
|------|------|--------|------|------|
| id | SERIAL | 自增 | PK | |
| contact_id | TEXT | | | 外部联系人ID |
| sys_contact_id | UUID | gen_random_uuid() | | 系统联系人ID |
| sys_company_id | UUID | | | 关联的系统公司ID |
| api_company_id | TEXT | | | API公司ID |
| company_id | TEXT | | | 公司ID |
| name | TEXT | | | 姓名 |
| position | TEXT | | | 职位 |
| department | TEXT | | | 部门 |
| email | TEXT | | | 邮箱 |
| email_status | TEXT | | | 邮箱验证状态 |
| phone | TEXT | | | 电话 |
| mobile | TEXT | | | 手机 |
| linkedin | TEXT | | | LinkedIn |
| whatsapp | TEXT | | | WhatsApp |
| source | TEXT | | | 来源 |
| confidence | TEXT | | | 置信度 |
| raw_data | JSONB | | | 原始数据 |
| created_at | TIMESTAMP | NOW() | | |

---

### 2.6 `email_drafts` - 邮件草稿

| 列名 | 类型 | 默认值 | 约束 | 说明 |
|------|------|--------|------|------|
| id | SERIAL | 自增 | PK | |
| sys_draft_id | UUID | gen_random_uuid() | | |
| sys_company_id | UUID | | | |
| sys_contact_id | UUID | | | |
| plan_id | INT | | FK→email_plans | |
| round_number | INT | `1` | CHECK(1-7) | 邮件轮次 |
| email | TEXT | | | 收件邮箱 |
| contact_name | TEXT | | | 联系人名 |
| position | TEXT | | | 职位 |
| country | TEXT | | | 国家 |
| language_code | TEXT | | | 语言代码 |
| subject | TEXT | | | 邮件主题 |
| body_target | TEXT | | | 目标语言正文 |
| body_zh | TEXT | | | 中文翻译 |
| anti_spam_notes | TEXT | | | 反垃圾邮件备注 |
| **send_status** | TEXT | `'draft'` | | draft/approved/sent/failed |
| review_note | TEXT | | | 审批/错误备注 |
| approved_by | TEXT | | | 审批人 |
| approved_at | TIMESTAMP | | | 审批时间 |
| sent_at | TIMESTAMP | | | 发送时间 |
| created_at | TIMESTAMP | NOW() | | |
| updated_at | TIMESTAMP | NOW() | | |

**唯一约束**：`(sys_contact_id, round_number)` - 同一联系人同一轮次只有一封邮件

---

### 2.7 `email_templates` - 邮件模板

| 列名 | 类型 | 默认值 | 约束 | 说明 |
|------|------|--------|------|------|
| id | SERIAL | 自增 | PK | |
| name | TEXT | | NOT NULL | 模板名称 |
| subject_template | TEXT | | NOT NULL | 主题模板（含变量） |
| body_template | TEXT | | NOT NULL | 正文模板（含变量） |
| round_number | INT | `1` | CHECK(1-5) | 适用轮次 |
| language | TEXT | `'en'` | | 语言 |
| is_active | BOOLEAN | TRUE | | 是否启用 |
| country | TEXT | | | 适用国家 |
| industry | TEXT | | | 适用行业 |
| created_at | TIMESTAMPTZ | NOW() | | |
| updated_at | TIMESTAMPTZ | NOW() | | |

**模板变量**：`{company_name}`, `{industry}`, `{contact_name}`, `{country}`

**索引**：`idx_email_templates_match (country, industry, round_number, language) WHERE is_active = TRUE`

---

### 2.8 `product_industry_config` - 产品行业配置（清洗规则）

| 列名 | 类型 | 默认值 | 约束 | 说明 |
|------|------|--------|------|------|
| id | SERIAL | 自增 | PK | |
| name | VARCHAR(100) | | NOT NULL, UNIQUE | 行业名称 |
| description | TEXT | `''` | | 描述 |
| keywords | JSONB | `'[]'` | | 关键词列表 |
| enabled | BOOLEAN | TRUE | | 是否启用 |
| sort_order | INT | `0` | | 排序 |
| created_at | TIMESTAMP | NOW() | | |
| updated_at | TIMESTAMP | NOW() | | |

**用途**：定义 16 类 PCB 细分行业，生成 LLM prompt 注入清洗/评级流程。

---

### 2.9 `system_config` - 系统配置

| 列名 | 类型 | 说明 |
|------|------|------|
| key | TEXT | 配置键（如 `auth.admin_username`） |
| value | TEXT | 配置值 |
| category | TEXT | 分类（auth/mail/llm） |

**关键配置项**：
- `auth.admin_username` / `auth.admin_password_hash` / `auth.secret_key` - JWT 认证
- `auth.qiye_token` / `auth.qiye_sess` / `auth.qiye_uid` - 网易外贸通凭证
- `mail.engagelab_api_url` / `mail.engagelab_user` / `mail.engagelab_credential` - EngageLab
- `mail.daily_limit` - 每日发送上限
- `llm.openrouter_api_key` - LLM API 密钥

**产品化标注**：当前所有配置（含多用户凭证）存在同一张表，多租户需按租户隔离。

---

### 2.10 `flow_runs` - Flow 运行记录

| 列名 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| id | SERIAL | PK | |
| flow_id | VARCHAR(10) | NOT NULL | Flow 标识 |
| flow_name | VARCHAR(100) | NOT NULL | Flow 名称 |
| status | VARCHAR(20) | `'running'` | running/completed/failed/cancelled |
| started_at | TIMESTAMP | NOW() | |
| finished_at | TIMESTAMP | | |
| result | JSONB | `'{}'` | 执行结果（含 api_quota_allocated） |
| error_message | TEXT | `''` | |
| created_at | TIMESTAMP | NOW() | |

---

### 2.11 `scheduled_tasks` - 调度任务配置

| 列名 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| id | SERIAL | PK | |
| flow_id | VARCHAR(10) | UNIQUE | Flow 标识 |
| flow_name | VARCHAR(100) | | |
| cron_expression | VARCHAR(50) | | Cron 表达式 |
| enabled | BOOLEAN | TRUE | |
| parameters | JSONB | `'{}'` | |
| description | TEXT | | |
| last_run_at | TIMESTAMP | | |
| next_run_at | TIMESTAMP | | |

---

### 2.12 `draft_rewrite_logs` - 草稿重写日志

| 列名 | 类型 | 说明 |
|------|------|------|
| id | SERIAL | PK |
| draft_id | INT | FK→email_drafts |
| advice | TEXT | 修改建议 |
| original_body | TEXT | 原文 |
| rewritten_body | TEXT | 重写后 |
| operator | TEXT | 操作人 |
| created_at | TIMESTAMP | |

---

### 2.13 `v_buyer_contacts` - 买家联系人视图

```sql
-- 简化定义
SELECT c.*, cd.company_name, cd.country, cd.source_tags,
       classify_contact(c.position, c.company_id) AS (priority, contact_category)
FROM contact_data c
JOIN company_data cd ON c.sys_company_id = cd.sys_company_id
WHERE cd.source_tags LIKE '%采购商%'
  AND c.email IS NOT NULL AND c.email <> ''
  AND c.email ~ '^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,20}$'
```

### 2.14 `classify_contact()` - 联系人分级函数

根据职位关键词返回 A/B/X 分级：
- **A**: 老板/创始人, C级高管, 总监/VP, 采购/供应链, 进出口/贸易
- **B**: 工程/技术, 生产/质量, 产品/项目经理
- **X**: 未匹配

---

## 3. 数据流转关系

```
keyword_list ──Flow01──▶ company_data ──Flow02──▶ company_analysis
                                          │                │
                                          ▼                │
                                     contact_data          │
                                          │                │
                                          ▼                ▼
                                     email_drafts (JOIN company_analysis + contact_data)
                                          │
                                     ──Flow04──▶ send_status = 'sent'
```

---

## 4. 产品化改造要点

| 现状 | 产品化需求 | 影响范围 |
|------|-----------|----------|
| 无租户概念 | 所有核心表加 `tenant_id` | 全部表 |
| 单用户认证 | 多用户 + 角色权限 | system_config, auth |
| 硬编码 PCB 行业 | 租户自定义行业配置 | product_industry_config |
| 共享 API 凭证 | 租户级凭证隔离 | system_config |
| 无软删除 | 加 `deleted_at` 字段 | 核心表 |
| 无操作审计 | 加审计日志表 | 新增表 |
