# ClientGet vs 外贸通原项目 — 数据表字段对比

> 调研日期：2026-05-18（**数据来自线上数据库 `\d` 输出**，非迁移文件推导）

---

## 一、原始公司表

### ClientGet 线上: `waimaotong_raw_companies`（63 列）

| # | 字段 | 类型 | Nullable | 默认值 | 释义 | 来自迁移 | 来自后加列 |
|---|------|------|----------|--------|------|:--------:|:--------:|
| 1 | `id` | bigint | NOT NULL | identity | 主键 | 0035 | |
| 2 | `keyword_master_id` | uuid | | | FK → keyword_master | 0035 | |
| 3 | `collection_type` | text | NOT NULL | 'direct_search' | direct_search / reverse_lookup | 0035 | |
| 4 | `source_id` | text | NOT NULL | | 网易外贸通公司ID | 0035 | |
| 5 | `real_id` | text | | | 网易 realId | 0035 | |
| 6 | `name` | text | | | 公司名称 | 0035 | |
| 7 | `country_iso3` | char(3) | | | ISO3 国家代码 | 0035 | |
| 8 | `domain` | text | | | 公司域名 | 0035 | |
| 9 | `industry` | text | | | 行业 | 0035 | |
| 10 | `address` | text | | | 地址 | 0035 | |
| 11 | `phone` | text | | | 电话 | 0035 | |
| 12 | `employee_size` | text | | | 员工规模 | 0035 | |
| 13 | `founded_year` | integer | | | 成立年份 | 0035 | |
| 14 | `description` | text | | | 公司描述 | 0035 | |
| 15 | `products` | text[] | | | 产品列表 | 0035 | |
| 16 | `source_tags` | text[] | | | 来源标签 | 0035 | |
| 17 | `emails` | text[] | | | 邮箱列表 | 0035 | |
| 18 | `trade_amount_3y_usd` | numeric | | | 近3年贸易额(USD) | 0035 | |
| 19 | `trade_count` | integer | | | 贸易次数 | 0035 | |
| 20 | `contacts_count` | integer | | | 联系人数量 | 0035 | |
| 21 | `has_trade_data` | boolean | | | 是否有海关数据 | 0035 | |
| 22 | `customs_data` | jsonb | | | 海关数据 | 0035 | |
| 23 | `search_payload` | jsonb | | | 搜索API原始响应 | 0035 | |
| 24 | `detail_payload` | jsonb | | | 详情API原始响应 | 0035 | |
| 25 | `trade_payload` | jsonb | | | 海关API原始响应 | 0035 | |
| 26 | `raw_payload` | jsonb | | | 兜底原始JSON | 0035 | |
| 27 | `detail_status` | text | NOT NULL | 'pending' | 详情获取状态 | 0035 | |
| 28 | `detail_fetched_at` | timestamptz | | | 详情获取时间 | 0035 | |
| 29 | `trade_status` | text | NOT NULL | 'pending' | 海关获取状态 | 0035 | |
| 30 | `trade_fetched_at` | timestamptz | | | 海关获取时间 | 0035 | |
| 31 | `contacts_status` | text | NOT NULL | 'pending' | 联系人获取状态 | 0035 | |
| 32 | `contacts_fetched_at` | timestamptz | | | 联系人获取时间 | 0035 | |
| 33 | `enrichment_error` | jsonb | | | 补全错误信息 | 0035 | |
| 34 | `created_at` | timestamptz | | now() | 创建时间 | 0035 | |
| 35 | `updated_at` | timestamptz | | now() | 更新时间 | 0035 | |
| 36 | `company_id` | text | | | 兼容原项目 company_id | | ✅ |
| 37 | `country_name` | text | | | 国家名称（自然语言） | | ✅ |
| 38 | `country_code` | text | | | 国家代码（2位） | | ✅ |
| 39 | `logo` | text | | | 公司 logo URL | | ✅ |
| 40 | `origin` | text | | | 数据来源标记 | | ✅ |
| 41 | `social_medias` | jsonb | | | 社交媒体链接集合 | | ✅ |
| 42 | `tags` | text[] | | | 通用标签 | | ✅ |
| 43 | `revenue` | text | | | 营收 | | ✅ |
| 44 | `founded_date` | text | | | 成立日期（文本） | | ✅ |
| 45 | `legal_name` | text | | | 法定名称 | | ✅ |
| 46 | `company_type` | text | | | 公司类型 | | ✅ |
| 47 | `sic_codes` | jsonb | | | SIC 行业代码 | | ✅ |
| 48 | `naics_codes` | jsonb | | | NAICS 行业代码 | | ✅ |
| 49 | `website_url` | text | | | 官网URL（独立字段） | | ✅ |
| 50 | `sys_company_id` | uuid | | gen_random_uuid() | 兼容原项目内部标识 | | ✅ |
| 51 | `api_company_id` | text | | | 兼容原项目 API ID | | ✅ |
| 52 | `company_name` | text | | | 兼容原项目公司名 | | ✅ |
| 53 | `country` | text | | | 兼容原项目国家字段 | | ✅ |
| 54 | `source_type` | text | | | 兼容原项目 buyer/competitor/search | | ✅ |
| 55 | `source_keyword` | text | | | 兼容原项目来源关键词 | | ✅ |
| 56 | `source_competitor` | text | | | 兼容原项目同行关键词 | | ✅ |
| 57 | `id_verified` | boolean | | false | 兼容原项目ID验证标记 | | ✅ |
| 58 | `plan_id` | integer | | | 兼容原项目计划ID | | ✅ |
| 59 | `full_address` | text | | | 兼容原项目完整地址 | | ✅ |
| 60 | `website` | text | | | 兼容原项目官网 | | ✅ |
| 61 | `has_detail` | boolean | | false | 兼容原项目详情标记 | | ✅ |
| 62 | `has_contacts` | boolean | | false | 兼容原项目联系人标记 | | ✅ |
| 63 | `email_count` | integer | | | 兼容原项目邮箱数量 | | ✅ |
| 64 | `detail_raw_data` | text | | | 兼容原项目详情原始数据 | | ✅ |
| 65 | `raw_data` | text | | | 兼容原项目原始数据 | | ✅ |
| 66 | `error_msg` | text | | | 兼容原项目错误信息 | | ✅ |

### 原项目: `company_data` + `company_detail`

| # | 字段 | 类型 | 释义 | 所在表 |
|---|------|------|------|--------|
| 1 | `id` | SERIAL | 主键 | company_data |
| 2 | `company_id` | TEXT | 网易公司ID | company_data |
| 3 | `company_name` | TEXT | 公司名称 | company_data |
| 4 | `country` | TEXT | 国家（自然语言） | company_data |
| 5 | `domain` | TEXT | 域名 | company_data |
| 6 | `source_type` | TEXT | buyer/competitor/search | company_data |
| 7 | `source_keyword` | TEXT | 来源关键词 | company_data |
| 8 | `source_competitor` | TEXT | 同行关键词 | company_data |
| 9 | `real_id` | TEXT | 网易 realId | company_data |
| 10 | `id_verified` | BOOLEAN | ID 已验证 | company_data |
| 11 | `raw_data` | TEXT | 原始 JSON | company_data |
| 12 | `source_tags` | TEXT | 标签 JSON 字符串 | company_data |
| 13 | `api_company_id` | TEXT | 网易 API ID | company_data |
| 14 | `plan_id` | INTEGER (FK) | 邮件计划 ID | company_data |
| 15 | `sys_company_id` | UUID | 内部唯一标识 | company_data |
| 16 | `created_at` | TIMESTAMP | 创建时间 | company_data |
| 17 | `updated_at` | TIMESTAMP | 更新时间 | company_data |
| 18 | `has_detail` | BOOLEAN | 已获取详情 | company_data |
| 19 | `has_contacts` | BOOLEAN | 已获取联系人 | company_data |
| 20 | `contact_count` | INTEGER | 联系人数量 | company_data |
| 21 | `email_count` | INTEGER | 邮箱数量 | company_data |
| 22 | `detail_status` | TEXT | 详情状态 | company_data |
| 23 | `error_msg` | TEXT | 错误信息 | company_data |
| 24 | `full_address` | TEXT | 地址 | company_detail |
| 25 | `website` | TEXT | 官网 | company_detail |
| 26 | `phone` | TEXT | 电话 | company_detail |
| 27 | `industry` | TEXT | 行业 | company_detail |
| 28 | `employee_size` | TEXT | 员工规模 | company_detail |
| 29 | `founded_year` | TEXT | 成立年份 | company_detail |
| 30 | `description` | TEXT | 公司描述 | company_detail |
| 31 | `products` | TEXT | 产品（逗号拼接） | company_detail |
| 32 | `raw_data` | TEXT | 详情原始 JSON | company_detail |

### 差异

| 维度 | ClientGet 线上（66列） | 原项目（32列） |
|------|-------|-------|
| **兼容列** | 线上已加入原项目全部字段作为兼容列（#36-66，共31列） | — |
| **原始 schema** | 0035 迁移定义 35 列 | company_data 23列 + company_detail 13列 |
| **新增字段** | `company_id`, `country_name`, `country_code`, `logo`, `origin`, `social_medias`, `tags`, `revenue`, `founded_date`, `legal_name`, `company_type`, `sic_codes`, `naics_codes`, `website_url` 等 14 列新业务字段 | 无对应 |
| **两者皆有** | source_id↔company_id, name↔company_name, country_iso3↔country, domain, real_id, source_tags, phone, industry, employee_size, founded_year, description, products, has_trade_data, created_at, updated_at, detail_status, error_msg | — |

---

## 二、原始联系人表

### ClientGet 线上: `waimaotong_raw_contacts`（27 列）

| # | 字段 | 类型 | Nullable | 默认值 | 释义 | 来自迁移 | 来自后加列 |
|---|------|------|----------|--------|------|:--------:|:--------:|
| 1 | `id` | bigint | NOT NULL | identity | 主键 | 0035 | |
| 2 | `raw_company_id` | bigint | NOT NULL | | FK → waimaotong_raw_companies.id | 0035 | |
| 3 | `source_contact_id` | text | | | 网易联系人ID | 0035 | |
| 4 | `name` | text | | | 姓名 | 0035 | |
| 5 | `position` | text | | | 职位 | 0035 | |
| 6 | `department` | text | | | 部门 | 0035 | |
| 7 | `email` | citext | | | 邮箱（大小写不敏感） | 0035 | |
| 8 | `email_status` | text | | | 邮箱验证状态 | 0035 | |
| 9 | `phone` | text | | | 电话 | 0035 | |
| 10 | `mobile` | text | | | 手机 | 0035 | |
| 11 | `linkedin` | text | | | LinkedIn | 0035 | |
| 12 | `whatsapp` | text | | | WhatsApp | 0035 | |
| 13 | `source` | text | | | 数据来源 | 0035 | |
| 14 | `confidence` | numeric | | | 置信度 | 0035 | |
| 15 | `raw_payload` | jsonb | | | 原始 JSON | 0035 | |
| 16 | `created_at` | timestamptz | | now() | 创建时间 | 0035 | |
| 17 | `job_title` | text | | | 职位标题（独立字段） | | ✅ |
| 18 | `country` | text | | | 联系人国家 | | ✅ |
| 19 | `region` | text | | | 地区 | | ✅ |
| 20 | `score` | integer | | | 联系人评分 | | ✅ |
| 21 | `emails` | text[] | | | 多邮箱列表 | | ✅ |
| 22 | `linkedin_url` | text | | | LinkedIn URL | | ✅ |
| 23 | `twitter_url` | text | | | Twitter URL | | ✅ |
| 24 | `facebook_url` | text | | | Facebook URL | | ✅ |
| 25 | `sys_contact_id` | uuid | | gen_random_uuid() | 兼容原项目系统联系人ID | | ✅ |
| 26 | `contact_id` | text | | | 兼容原项目联系人ID | | ✅ |
| 27 | `sys_company_id` | uuid | | | 兼容原项目系统公司ID | | ✅ |
| 28 | `api_company_id` | text | | | 兼容原项目 API 公司ID | | ✅ |
| 29 | `company_id` | text | | | 兼容原项目公司ID | | ✅ |

### 原项目: `contact_data`（19 列）

| # | 字段 | 类型 | 释义 |
|---|------|------|------|
| 1 | `id` | SERIAL | 主键 |
| 2 | `sys_contact_id` | UUID | 系统联系人标识 |
| 3 | `contact_id` | TEXT | 网易联系人ID |
| 4 | `sys_company_id` | UUID | 系统公司标识 |
| 5 | `api_company_id` | TEXT | 网易公司ID |
| 6 | `company_id` | TEXT | 公司ID |
| 7 | `name` | TEXT | 姓名 |
| 8 | `position` | TEXT | 职位 |
| 9 | `department` | TEXT | 部门 |
| 10 | `email` | TEXT | 邮箱 |
| 11 | `email_status` | TEXT | 验证状态 |
| 12 | `phone` | TEXT | 电话 |
| 13 | `mobile` | TEXT | 手机 |
| 14 | `linkedin` | TEXT | LinkedIn |
| 15 | `whatsapp` | TEXT | WhatsApp |
| 16 | `source` | TEXT | 来源 |
| 17 | `confidence` | TEXT | 置信度（TEXT） |
| 18 | `raw_data` | TEXT | 原始 JSON（TEXT） |
| 19 | `created_at` | TIMESTAMP | 创建时间 |

### 差异

| 维度 | ClientGet 线上（29列） | 原项目（19列） |
|------|-------|-------|
| **兼容列** | 已加入 sys_contact_id, contact_id, sys_company_id, api_company_id, company_id（#25-29） | — |
| **新增字段** | `job_title`, `country`, `region`, `score`, `emails`(数组), `linkedin_url`, `twitter_url`, `facebook_url`（#17-24，8列新业务字段） | 无对应 |
| **邮箱类型** | CITEXT | TEXT |
| **置信度** | NUMERIC | TEXT |
| **原始数据** | `raw_payload` JSONB | `raw_data` TEXT |
| **关联** | `raw_company_id` BIGINT FK（单字段） | sys_company_id + api_company_id + company_id（三字段冗余） |
| **去重** | DB 唯一索引两级 | 应用层三级查重 |

---

## 三、清洗公司表

### ClientGet 线上: `clean_companies`（20 列）

| # | 字段 | 类型 | Nullable | 默认值 | 释义 |
|---|------|------|----------|--------|------|
| 1 | `id` | bigint | NOT NULL | identity | 主键 |
| 2 | `name` | text | | | 公司名称 |
| 3 | `name_normalized` | text | NOT NULL | | 标准化名（normalize函数） |
| 4 | `country_iso3` | char(3) | | | ISO3 国家代码 |
| 5 | `website` | text | | | 官网 |
| 6 | `tax_no` | text | | | 税号 |
| 7 | `incorporation_date` | date | | | 成立日期 |
| 8 | `reg_capital` | numeric | | | 注册资本 |
| 9 | `employee_num` | text | | | 员工数 |
| 10 | `industry_desc` | text | | | 行业描述 |
| 11 | `industry_tags` | text[] | | '{}' | 行业标签 |
| 12 | `product_tags` | text[] | | '{}' | 产品标签 |
| 13 | `pcb_suppliers` | text[] | | '{}' | PCB 供应商 |
| 14 | `trade_amount_3y_usd` | numeric | | | 近3年贸易额 |
| 15 | `trade_count` | integer | | | 贸易次数 |
| 16 | `contacts_count` | integer | | 0 | 联系人数量 |
| 17 | `aliases` | text[] | | '{}' | 公司别名 |
| 18 | `latest_tendata_summary_at` | timestamptz | | | 最新腾道汇总时间 |
| 19 | `created_at` | timestamptz | NOT NULL | now() | 创建时间 |
| 20 | `updated_at` | timestamptz | NOT NULL | now() | 更新时间 |

与迁移文件一致，无后加列。

### 原项目: `company_analysis`（44 列）

| # | 字段 | 类型 | 释义 | 数据来源 |
|---|------|------|------|---------|
| 1-5 | id, company_id, company_name, english_name, country | — | 基础信息 | 继承/LLM |
| 6-8 | grade, score, sub_industry | — | AI 评级评分 | LLM |
| 9-13 | match_reasons, potential_needs, recommended_products, sales_approach, risk_factors | — | AI 分析 | LLM |
| 14-21 | website, region, founded_year, company_size, revenue_estimate, industry, main_business, products_services | — | 公司画像 | LLM |
| 22-28 | company_type, target_customers, market_coverage, linkedin, youtube, other_social, recent_activities | — | 扩展画像 | LLM |
| 29-32 | key_contacts, data_sources, search_raw, ai_raw | — | 原始存档 | 系统/LLM |
| 33-35 | sys_company_id, plan_id, email_priority | — | 关联/状态 | 系统 |
| 36-38 | product_tags, tag_confidence, data_source_tags | — | 标签 | LLM+规则 |
| 39-40 | has_trade_data, trade_summary | — | 海关 | API |
| 41-42 | score_details, is_new_collection | — | 评分明细 | LLM |
| 43-44 | created_at, updated_at | — | 时间 | 系统 |

### 差异

| 维度 | ClientGet (`clean_companies` 20列) | 原项目 (`company_analysis` 44列) |
|------|-------|-------|
| **定位** | 纯数据（多源去重，不含AI） | 数据+AI+邮件一体 |
| **AI 字段** | 无（评分在 tenant_companies） | grade/score/score_details 等 15+ 列 |
| **邮件字段** | 无（在 tenant 层） | email_priority + plan_id |
| **原始存档** | 无（在 raw 表） | search_raw + ai_raw |
| **多源** | aliases + clean_company_sources 关联表 | 无 |
| **CG 独有** | name_normalized, tax_no, reg_capital, incorporation_date, pcb_suppliers, aliases, latest_tendata_summary_at | — |
| **原项目独有** | — | 全部 AI/LLM 字段, email_priority, plan_id, sys_company_id, search_raw, ai_raw |

---

## 四、清洗联系人表

### ClientGet 线上: `clean_contacts`（8 列）

| # | 字段 | 类型 | Nullable | 默认值 | 释义 |
|---|------|------|----------|--------|------|
| 1 | `id` | bigint | NOT NULL | identity | 主键 |
| 2 | `clean_company_id` | bigint | NOT NULL | | FK → clean_companies（级联删除） |
| 3 | `name` | text | | | 姓名 |
| 4 | `position` | text | | | 职位 |
| 5 | `email` | citext | | | 邮箱 |
| 6 | `phone` | text | | | 电话 |
| 7 | `created_at` | timestamptz | NOT NULL | now() | 创建时间 |
| 8 | `updated_at` | timestamptz | NOT NULL | now() | 更新时间 |

唯一约束：`(clean_company_id, email) WHERE email IS NOT NULL`

### ClientGet 线上: `tenant_contacts`（8 列）

| # | 字段 | 类型 | Nullable | 默认值 | 释义 |
|---|------|------|----------|--------|------|
| 1 | `id` | bigint | NOT NULL | identity | 主键 |
| 2 | `tenant_id` | uuid | NOT NULL | | FK → tenants |
| 3 | `clean_contact_id` | bigint | NOT NULL | | FK → clean_contacts（级联删除） |
| 4 | `clean_company_id` | bigint | NOT NULL | | FK → clean_companies（级联删除） |
| 5 | `contact_status` | text | NOT NULL | 'available' | 联系人状态 |
| 6 | `is_sendable` | boolean | NOT NULL | true | 是否可发送 |
| 7 | `created_at` | timestamptz | NOT NULL | now() | 创建时间 |
| 8 | `updated_at` | timestamptz | NOT NULL | now() | 更新时间 |

被引用：emails, group_members, sending_plan_recipients, sequence_enrollments

### 原项目：无独立清洗联系人表

原项目 `contact_data`（19列）同时承担原始和业务角色，通过 `v_buyer_contacts` 视图按职位分 A/B 级。

### 差异

| 维度 | ClientGet | 原项目 |
|------|-----------|--------|
| 分层 | raw → clean(8列) → tenant(8列) 三层 | contact_data(19列) 单表 + 视图 |
| 精简 | clean_contacts 去掉 department/mobile/linkedin/whatsapp/source/confidence/email_status | 全部保留 |
| 去重 | DB `(clean_company_id, email)` UPSERT | 应用层三级查重 |
| 多租户 | tenant_contacts 带 is_sendable + RLS | 无 |

---

## 五、关键发现：线上 vs 迁移文件差异

线上 `waimaotong_raw_companies` 比迁移 0035 **多出 31 列**，`waimaotong_raw_contacts` **多出 13 列**。这些后加列分两类：

**1. 兼容原项目字段**（直接对齐外贸通原项目 schema）：
- raw_companies: `company_id`, `sys_company_id`, `api_company_id`, `company_name`, `country`, `source_type`, `source_keyword`, `source_competitor`, `id_verified`, `plan_id`, `full_address`, `website`, `has_detail`, `has_contacts`, `email_count`, `detail_raw_data`, `raw_data`, `error_msg`
- raw_contacts: `sys_contact_id`, `contact_id`, `sys_company_id`, `api_company_id`, `company_id`

**2. 新业务扩展字段**（超出原项目范围）：
- raw_companies: `country_name`, `country_code`, `logo`, `origin`, `social_medias`, `tags`, `revenue`, `founded_date`, `legal_name`, `company_type`, `sic_codes`, `naics_codes`, `website_url`
- raw_contacts: `job_title`, `country`, `region`, `score`, `emails`(数组), `linkedin_url`, `twitter_url`, `facebook_url`

`clean_companies` 和 `clean_contacts` 与迁移文件一致，无后加列。
