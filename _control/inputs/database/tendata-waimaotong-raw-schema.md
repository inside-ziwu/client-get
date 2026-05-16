# 腾道与外贸通 Raw Schema 整理

> 生成日期：2026-05-09  
> 范围：腾道与外贸通 raw companies / raw contacts 表  
> 依据：`backend/alembic/versions/20260509_0035_provider_raw_schema_alignment.py`、`backend/03_database/schema.sql`、`docs/research/tendata-field-mapping.md`、`docs/plan-waimaotong-adapter.md`  
> 状态说明：V3 当前决策为 **腾道启用，外贸通采集推迟到 V3.1+，但 schema 保留**。

## 1. 总览

| 数据源 | 表 | V3 状态 | 释义 |
| --- | --- | --- | --- |
| 腾道 | `tendata_raw_companies` | 启用 | 腾道反推得到的海外买家公司原始表 |
| 腾道 | `tendata_raw_contacts` | 启用 | 腾道联系人原始表，挂在腾道 raw company 下 |
| 外贸通 | `waimaotong_raw_companies` | 保留，V3 暂空 | 外贸通直采 / 未来反推得到的海外公司原始表 |
| 外贸通 | `waimaotong_raw_contacts` | 保留，V3 暂空 | 外贸通联系人原始表，挂在外贸通 raw company 下 |

## 2. `tendata_raw_companies`

| 字段 | 类型 | 释义 |
| --- | --- | --- |
| `id` | `bigint` | 系统内部主键 |
| `keyword_master_id` | `uuid` | 对应统一关键词 `keyword_master.id`，用于追踪由哪个关键词触发 |
| `source_id` | `text` | 腾道侧公司主键，通常对应 `tid` |
| `collection_type` | `text` | 采集类型，默认 `reverse_lookup`；可选 `direct_search` / `reverse_lookup` |
| `globiz_id` | `text` | 腾道 Globiz 公司 ID |
| `name` | `text` | 标准公司名，通常来自 BRIEF `name` |
| `name_local` | `text` | 本地语言公司名 |
| `country_iso3` | `char(3)` | ISO3 国家码，如 `IND`、`MYS` |
| `website` | `text` | 官网 |
| `tax_no` | `text` | 税号 / 注册号 |
| `incorporation_date` | `date` | 成立日期 |
| `employee_num` | `text` | 员工人数原始值，覆盖率较低 |
| `industry_desc` | `text` | 细分行业描述，覆盖率较低 |
| `product_tags` | `text[]` | 产品标签，来自贸易搜索聚合 |
| `pcb_suppliers` | `text[]` | PCB 供应商 / 中国供应商名称聚合 |
| `trade_amount_3y_usd` | `numeric` | 近 3 年进出口总额，美元口径 |
| `trade_count` | `int` | 进出口次数 |
| `contacts_count` | `int` | 采集到的联系人数量 |
| `has_trade_data` | `boolean` | 是否有贸易数据 |
| `aliases` | `text[]` | 公司别名 |
| `raw_payload` | `jsonb` | 腾道各端点原始响应归档 |
| `detail_status` | `text` | 详情抓取状态：`pending` / `fetched` / `failed` / `skipped` |
| `detail_fetched_at` | `timestamptz` | 详情抓取时间 |
| `trade_status` | `text` | 贸易统计抓取状态：`pending` / `fetched` / `failed` / `skipped` |
| `trade_fetched_at` | `timestamptz` | 贸易统计抓取时间 |
| `contacts_status` | `text` | 联系人抓取状态：`pending` / `fetched` / `failed` / `skipped` |
| `contacts_fetched_at` | `timestamptz` | 联系人抓取时间 |
| `enrichment_error` | `jsonb` | 富化 / 抓取失败详情 |
| `created_at` | `timestamptz` | 入库时间 |

约束与索引：

| 名称 / 字段 | 释义 |
| --- | --- |
| `UNIQUE(keyword_master_id, source_id, collection_type)` | 同一关键词、同一腾道公司、同一采集类型只保留一条 |
| `idx_tendata_raw_companies_keyword` | 按关键词查 raw company |
| `idx_tendata_raw_companies_source` | 按腾道 source id 查 raw company |
| `idx_tendata_raw_companies_globiz` | 按 Globiz ID 查 raw company，仅索引非空值 |
| `idx_tendata_raw_companies_country` | 按国家查 raw company |

## 3. `tendata_raw_contacts`

| 字段 | 类型 | 释义 |
| --- | --- | --- |
| `id` | `bigint` | 系统内部主键 |
| `raw_company_id` | `bigint` | 关联 `tendata_raw_companies.id` |
| `source_contact_id` | `text` | 腾道联系人侧 ID；没有则用邮箱兜底去重 |
| `name` | `text` | 联系人姓名 |
| `position` | `text` | 职位 |
| `email` | `citext` | 邮箱，大小写不敏感 |
| `phone` | `text` | 电话 |
| `raw_payload` | `jsonb` | 联系人原始响应 |
| `created_at` | `timestamptz` | 入库时间 |

约束与索引：

| 名称 / 字段 | 释义 |
| --- | --- |
| `raw_company_id -> tendata_raw_companies.id` | 联系人从属于同源 raw company，company 删除时级联删除联系人 |
| `uq_tendata_raw_contacts_source_contact` | 同一公司下 `source_contact_id` 唯一；只约束非空值 |
| `uq_tendata_raw_contacts_email_fallback` | 无联系人 ID 时，同一公司下 `email` 唯一 |
| `idx_tendata_raw_contacts_company` | 按公司查联系人 |
| `idx_tendata_raw_contacts_email` | 按邮箱查联系人，仅索引非空值 |

## 4. `waimaotong_raw_companies`

| 字段 | 类型 | 释义 |
| --- | --- | --- |
| `id` | `bigint` | 系统内部主键 |
| `keyword_master_id` | `uuid` | 对应统一关键词 |
| `collection_type` | `text` | 采集类型，默认 `direct_search`；未来可支持 `reverse_lookup` |
| `source_id` | `text` | 外贸通公司 ID；无 ID 时可降级用域名 |
| `real_id` | `text` | 外贸通真实 ID / 补全 ID |
| `name` | `text` | 公司名 |
| `country_iso3` | `char(3)` | ISO3 国家码 |
| `domain` | `text` | 公司域名 |
| `industry` | `text` | 行业 |
| `address` | `text` | 地址 |
| `phone` | `text` | 公司电话 |
| `employee_size` | `text` | 公司规模原始值 |
| `founded_year` | `int` | 成立年份 |
| `description` | `text` | 公司简介 |
| `products` | `text[]` | 产品列表 |
| `source_tags` | `text[]` | 外贸通标签 |
| `emails` | `text[]` | 公司级邮箱列表 |
| `trade_amount_3y_usd` | `numeric` | 近 3 年贸易额，若外贸通提供 |
| `trade_count` | `int` | 贸易次数 |
| `contacts_count` | `int` | 联系人数量 |
| `has_trade_data` | `boolean` | 是否有贸易数据 |
| `customs_data` | `jsonb` | 海关 / 贸易数据原始片段 |
| `search_payload` | `jsonb` | SEARCH 响应 |
| `detail_payload` | `jsonb` | DETAIL 响应 |
| `trade_payload` | `jsonb` | TRADE 响应 |
| `raw_payload` | `jsonb` | 汇总原始响应 |
| `detail_status` | `text` | 详情抓取状态：`pending` / `fetched` / `failed` / `skipped` |
| `detail_fetched_at` | `timestamptz` | 详情抓取时间 |
| `trade_status` | `text` | 贸易数据抓取状态：`pending` / `fetched` / `failed` / `skipped` |
| `trade_fetched_at` | `timestamptz` | 贸易数据抓取时间 |
| `contacts_status` | `text` | 联系人抓取状态：`pending` / `fetched` / `failed` / `skipped` |
| `contacts_fetched_at` | `timestamptz` | 联系人抓取时间 |
| `enrichment_error` | `jsonb` | 富化失败详情 |
| `created_at` | `timestamptz` | 创建时间 |
| `updated_at` | `timestamptz` | 更新时间 |

约束与索引：

| 名称 / 字段 | 释义 |
| --- | --- |
| `UNIQUE(keyword_master_id, source_id, collection_type)` | 同一关键词、同一外贸通公司、同一采集类型只保留一条 |
| `idx_wmt_raw_companies_keyword` | 按关键词查 raw company |
| `idx_wmt_raw_companies_source` | 按外贸通 source id 查 raw company |

## 5. `waimaotong_raw_contacts`

| 字段 | 类型 | 释义 |
| --- | --- | --- |
| `id` | `bigint` | 系统内部主键 |
| `raw_company_id` | `bigint` | 关联 `waimaotong_raw_companies.id` |
| `source_contact_id` | `text` | 外贸通联系人 ID |
| `name` | `text` | 联系人姓名 |
| `position` | `text` | 职位 |
| `department` | `text` | 部门 |
| `email` | `citext` | 邮箱，大小写不敏感 |
| `email_status` | `text` | 邮箱状态 / 验证状态 |
| `phone` | `text` | 电话 |
| `mobile` | `text` | 手机 |
| `linkedin` | `text` | LinkedIn |
| `whatsapp` | `text` | WhatsApp |
| `source` | `text` | 联系人来源 |
| `confidence` | `numeric` | 置信度 |
| `raw_payload` | `jsonb` | 联系人原始响应 |
| `created_at` | `timestamptz` | 入库时间 |

约束与索引：

| 名称 / 字段 | 释义 |
| --- | --- |
| `raw_company_id -> waimaotong_raw_companies.id` | 联系人从属于同源 raw company，company 删除时级联删除联系人 |
| `uq_wmt_raw_contacts_source_contact` | 同一公司下 `source_contact_id` 唯一；只约束非空值 |
| `uq_wmt_raw_contacts_email_fallback` | 无联系人 ID 时，同一公司下 `email` 唯一 |
| `idx_wmt_raw_contacts_company` | 按公司查联系人 |
| `idx_wmt_raw_contacts_email` | 按邮箱查联系人，仅索引非空值 |

## 6. 采集来源补充

| 数据源 | 上游接口 / 端点 | 主要入库字段 |
| --- | --- | --- |
| 腾道 T1 Search | 贸易搜索 | `product_tags`、`pcb_suppliers`、`has_trade_data`、部分贸易原始数据 |
| 腾道 BRIEF | 公司 BRIEF | `source_id` / `tid`、`globiz_id`、`name`、`country_iso3`、`website`、`tax_no`、`aliases` |
| 腾道 T3 ALL | 公司详情 | `name_local`、`incorporation_date`、`employee_num`、`industry_desc` |
| 腾道 volume_of_trade | 贸易量统计 | `trade_amount_3y_usd`、`trade_count` |
| 腾道 T4 Contacts | LinkedIn / Internet / More 等联系人端点 | `tendata_raw_contacts` |
| 外贸通 SEARCH | 公司搜索 | `source_id`、`name`、`domain`、`country_iso3`、`source_tags`、`search_payload` |
| 外贸通 DETAIL | 公司详情 | `industry`、`phone`、`employee_size`、`founded_year`、`products`、`description`、`address`、`detail_payload` |
| 外贸通 CONTACT | 联系人列表 | `waimaotong_raw_contacts` |

## 
