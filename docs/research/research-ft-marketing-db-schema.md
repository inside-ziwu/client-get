# 外贸通核心数据表字段定义

> 来源仓库：https://github.com/aoqi-ai/sysdev-ft-marketing
> 调研日期：2026-05-16

---

## 一、company_data（原始采集公司）

由 Flow 01 关键词采集入库写入，存储网易外贸通搜索 API 返回的原始公司数据。

| # | 字段 | 类型 | 释义 | 数据来源 |
|---|------|------|------|---------|
| 1 | `id` | SERIAL | 自增主键 | 系统生成 |
| 2 | `company_id` | TEXT | 网易外贸通公司ID（API id 或 domain） | 网易搜索API |
| 3 | `company_name` | TEXT | 公司名称 | 网易搜索API |
| 4 | `country` | TEXT | 国家 | 网易搜索API |
| 5 | `domain` | TEXT | 公司域名 | 网易搜索API |
| 6 | `source_type` | TEXT | 数据来源类型：buyer / competitor / search | 系统推断（根据标签判定） |
| 7 | `source_keyword` | TEXT | 来源搜索关键词（逗号分隔，可追加合并） | Flow 01 关键词名 |
| 8 | `source_competitor` | TEXT | 来源同行关键词（source_type=competitor 时） | Flow 01 |
| 9 | `real_id` | TEXT | 网易 realId | 网易搜索API |
| 10 | `id_verified` | BOOLEAN | company_id 是否已验证（非公司名同名） | Flow 01 / Flow 02 |
| 11 | `raw_data` | TEXT | 原始 API 返回完整 JSON | 网易搜索API |
| 12 | `source_tags` | TEXT | 来源标签 JSON 数组（如"采购商"、"同行"） | 网易搜索API（标签提取） |
| 13 | `api_company_id` | TEXT | 网易外贸通原始 id 字段 | 网易搜索API / BaseInfo API |
| 14 | `plan_id` | INTEGER | 关联邮件计划 ID（FK → email_plans.id） | 系统生成 |
| 15 | `sys_company_id` | UUID | 系统内部唯一公司标识 | 系统生成（gen_random_uuid()） |
| 16 | `created_at` | TIMESTAMP | 创建时间 | 系统生成 |
| 17 | `updated_at` | TIMESTAMP | 更新时间 | 系统生成 |
| 18 | `has_detail` | BOOLEAN | 是否已获取公司详情 | Flow 02 回写 |
| 19 | `has_contacts` | BOOLEAN | 是否已获取联系人 | Flow 02 回写 |
| 20 | `contact_count` | INTEGER | 联系人数量 | Flow 02 回写 |
| 21 | `email_count` | INTEGER | 邮箱数量 | Flow 02 / 系统计算 |
| 22 | `detail_status` | TEXT | 详情获取状态（completed / id_complete_failed） | Flow 02 回写 |
| 23 | `error_msg` | TEXT | 错误信息 | Flow 02 异常时回写 |

**关键约束**：
- 幂等写入：按 `company_id + plan_id` 查重
- `plan_id` 有 FK 约束 + 索引（由 migrate_plan_schema.py 添加）

---

## 二、company_analysis（清洗分析结果）

由 Flow 02 公司清洗评估写入（UPSERT），存储 LLM 分析后的公司画像和评分。

| # | 字段 | 类型 | 释义 | 数据来源 |
|---|------|------|------|---------|
| 1 | `id` | SERIAL | 自增主键 | 系统生成 |
| 2 | `company_id` | TEXT | 公司ID（api_company_id 或 company_id 或 sys_company_id） | 继承自 company_data |
| 3 | `company_name` | TEXT | 公司名称 | 继承自 company_data |
| 4 | `english_name` | TEXT | 英文名称 | LLM分析（company_profile.english_name） |
| 5 | `country` | TEXT | 国家 | LLM分析 / 继承自 company_data |
| 6 | `grade` | TEXT | 评级：A（精确命中）/ B（相关）/ X（无关） | LLM分析（强制校验后） |
| 7 | `score` | INTEGER | 综合评分 0-100 | LLM分析（强制校验后） |
| 8 | `sub_industry` | TEXT | 细分行业（16 个标准行业之一） | LLM分析（normalize 后） |
| 9 | `match_reasons` | TEXT/JSONB | 匹配原因 JSON 数组 | LLM分析 |
| 10 | `potential_needs` | TEXT/JSONB | 潜在 PCB 需求 JSON 数组 | LLM分析（pcb_relevance.potential_needs） |
| 11 | `recommended_products` | TEXT/JSONB | 推荐产品 JSON 数组 | LLM分析（pcb_relevance.recommended_products） |
| 12 | `sales_approach` | TEXT | 销售策略 | LLM分析（当前写空串） |
| 13 | `risk_factors` | TEXT/JSONB | 风险因素 JSON 数组 | LLM分析（pcb_relevance.risk_factors） |
| 14 | `website` | TEXT | 公司官网 | LLM分析（company_profile.website） |
| 15 | `region` | TEXT | 地区 | LLM分析（company_profile.region） |
| 16 | `founded_year` | TEXT | 成立年份 | LLM分析（company_profile.founded_year） |
| 17 | `company_size` | TEXT | 公司规模描述 | LLM分析（company_profile.company_size） |
| 18 | `revenue_estimate` | TEXT | 营收估计 | LLM分析（company_profile.revenue_estimate） |
| 19 | `industry` | TEXT | 行业 | LLM分析（company_profile.industry） |
| 20 | `main_business` | TEXT/JSONB | 主营业务 JSON 数组 | LLM分析（main_products） |
| 21 | `products_services` | TEXT/JSONB | 产品/服务 JSON 数组 | LLM分析（main_products） |
| 22 | `target_customers` | TEXT | 目标客户 | LLM分析（当前写空串） |
| 23 | `market_coverage` | TEXT | 市场覆盖 | LLM分析（当前写空串） |
| 24 | `company_type` | TEXT | 公司性质（生产制造/贸易商/OEM/ODM/EMS等） | LLM分析（company_profile.company_type） |
| 25 | `linkedin` | TEXT | LinkedIn 链接 | LLM分析（当前写空串） |
| 26 | `youtube` | TEXT | YouTube 链接 | LLM分析（当前写空串） |
| 27 | `other_social` | TEXT | 其他社媒 | LLM分析（当前写空串） |
| 28 | `recent_activities` | TEXT/JSONB | 近期动态 | LLM分析（当前写空串） |
| 29 | `key_contacts` | TEXT/JSONB | 关键联系人 | LLM分析（当前写空串） |
| 30 | `data_sources` | TEXT/JSONB | LLM 引用的数据来源 URL 数组 | LLM分析 |
| 31 | `search_raw` | TEXT | 原始搜索数据（company_data 整行 JSON） | 系统生成 |
| 32 | `ai_raw` | TEXT | LLM 完整原始输出 | LLM分析 |
| 33 | `sys_company_id` | UUID | 系统唯一公司标识 | 继承自 company_data |
| 34 | `plan_id` | INTEGER | 关联计划 ID（FK → email_plans.id） | 系统生成 |
| 35 | `email_priority` | TEXT | 邮件优先级：selected / skipped | 系统生成（A/B=selected, X=skipped） |
| 36 | `product_tags` | JSONB | 产品行业标签数组 | LLM分析 + 规则匹配 |
| 37 | `tag_confidence` | JSONB | 标签置信度 {标签名: "high"/"medium"/"low"} | 规则匹配（backfill 脚本） |
| 38 | `data_source_tags` | JSONB | 数据来源标签数组（"外贸通"/"海关数据"/"同行客户"） | 系统生成（从 source_type 汇总） |
| 39 | `has_trade_data` | BOOLEAN | 是否有海关贸易数据 | 网易BaseInfo海关API |
| 40 | `trade_summary` | JSONB | 海关贸易摘要 JSON | 网易BaseInfo海关API |
| 41 | `score_details` | JSONB | 三维度评分明细 [{dimension, score, max_possible, explanation}] | LLM分析（relevance/market_fit/intent） |
| 42 | `is_new_collection` | (推断) | 是否新采集 | 系统生成 |
| 43 | `created_at` | TIMESTAMP | 创建时间 | 系统生成 |
| 44 | `updated_at` | TIMESTAMP | 更新时间 | 系统生成 |

**关键约束**：
- UPSERT 冲突键（局部索引）：
  - `(sys_company_id) WHERE plan_id IS NULL`
  - `(sys_company_id, plan_id) WHERE plan_id IS NOT NULL`
- `email_priority` CHECK 约束：`IN ('selected', 'skipped')`
- `product_tags` 默认 `'[]'::jsonb`
- `tag_confidence` 默认 `'{}'::jsonb`

---

## 三、company_detail（公司详情）

由 Flow 02 的 `_upsert_company_detail` 函数写入，存储网易外贸通公司详情 API 返回数据。仅 A/B 级公司触发。

| # | 字段 | 类型 | 释义 | 数据来源 |
|---|------|------|------|---------|
| 1 | `id` | SERIAL | 自增主键 | 系统生成 |
| 2 | `sys_company_id` | UUID | 系统唯一公司标识 | 继承自 company_data |
| 3 | `api_company_id` | TEXT | 网易外贸通公司ID | 网易详情API |
| 4 | `company_id` | TEXT | 公司ID | 网易详情API |
| 5 | `full_address` | TEXT | 完整地址 | 网易详情API（detail.address / detail.location） |
| 6 | `website` | TEXT | 公司官网 | 网易详情API（detail.domain） |
| 7 | `phone` | TEXT | 公司电话 | 网易详情API（detail.phone） |
| 8 | `industry` | TEXT | 行业 | 网易详情API（detail.industry） |
| 9 | `employee_size` | TEXT | 员工规模 | 网易详情API（detail.employeeSize） |
| 10 | `founded_year` | TEXT | 成立年份 | 网易详情API（detail.foundedYear） |
| 11 | `description` | TEXT | 公司描述 | 网易详情API（detail.overviewDescription / detail.description） |
| 12 | `products` | TEXT | 产品列表（逗号分隔） | 网易详情API（detail.productList[].name 拼接） |
| 13 | `raw_data` | TEXT | 原始 API 返回完整 JSON | 网易详情API |

**关键约束**：
- 幂等：通过 `SELECT ... FOR UPDATE WHERE sys_company_id=%s` 实现
- 存在则 UPDATE，不存在则 INSERT

---

## 四、contact_data（联系人）

由 Flow 02 的 `_insert_contacts` 函数写入，存储网易外贸通联系人 API 返回数据。仅 A/B 级公司触发。

| # | 字段 | 类型 | 释义 | 数据来源 |
|---|------|------|------|---------|
| 1 | `id` | SERIAL | 自增主键 | 系统生成 |
| 2 | `sys_contact_id` | UUID | 系统唯一联系人标识 | 系统生成（gen_random_uuid()） |
| 3 | `contact_id` | TEXT | 网易外贸通联系人ID | 网易联系人API（c.id / c.contactId） |
| 4 | `sys_company_id` | UUID | 系统唯一公司标识 | 继承自 company_data |
| 5 | `api_company_id` | TEXT | 网易外贸通公司ID | 继承自 company_data |
| 6 | `company_id` | TEXT | 公司ID | 继承自 company_data |
| 7 | `name` | TEXT | 联系人姓名 | 网易联系人API（c.name） |
| 8 | `position` | TEXT | 职位 | 网易联系人API（c.position / c.jobTitle） |
| 9 | `department` | TEXT | 部门 | 网易联系人API（c.department） |
| 10 | `email` | TEXT | 邮箱地址 | 网易联系人API（c.emails[0].email / c.contact） |
| 11 | `email_status` | TEXT | 邮箱验证状态 | 网易联系人API（c.emailStatus / c.email_status） |
| 12 | `phone` | TEXT | 电话 | 网易联系人API（c.phone） |
| 13 | `mobile` | TEXT | 手机 | 网易联系人API（c.mobile / c.cellphone） |
| 14 | `linkedin` | TEXT | LinkedIn 链接 | 网易联系人API（c.linkedin / c.linkedinUrl） |
| 15 | `whatsapp` | TEXT | WhatsApp 号码 | 网易联系人API（c.whatsapp） |
| 16 | `source` | TEXT | 数据来源（默认 "netease"） | 网易联系人API（c.source）/ 默认值 |
| 17 | `confidence` | TEXT | 置信度 | 网易联系人API（c.confidence） |
| 18 | `raw_data` | TEXT | 原始 API 返回完整 JSON | 网易联系人API |
| 19 | `created_at` | TIMESTAMP | 创建时间 | 系统生成 |

**关键约束**：
- 三级去重（只 INSERT 不 UPDATE）：
  1. `(sys_company_id, contact_id)` — 同公司同联系人ID
  2. `(sys_company_id, email)` — 同公司同邮箱
  3. `(sys_company_id, name, position)` — 同公司同姓名+职位
- 视图 `v_buyer_contacts` 使用 `classify_contact()` 函数按职位分级（A: 老板/高管/采购/进出口；B: 工程/生产/项目经理）

---

## 五、表间关联关系

```
email_plans (1)
    ├──< company_data (N)        via plan_id
    ├──< company_analysis (N)    via plan_id
    └──< email_drafts (N)        via plan_id

company_data (1)
    ├──< company_analysis (1)    via sys_company_id
    ├──< company_detail (1)      via sys_company_id
    └──< contact_data (N)        via sys_company_id

contact_data (1)
    └──< email_drafts (N)        via sys_contact_id
```

核心关联键：**`sys_company_id`**（UUID），在 company_data INSERT 时由 `gen_random_uuid()` 生成，贯穿所有下游表。

---

## 六、迁移脚本对这 4 表的变更

| 迁移脚本 | 表 | 变更 |
|---------|---|------|
| `migrate_plan_schema.py` | company_data | 加 `plan_id INT`（FK + 索引） |
| `migrate_plan_schema.py` | company_analysis | 加 `plan_id INT`（FK + 索引）+ `email_priority TEXT`（CHECK）+ 重建唯一索引为局部索引 |
| `migrate_product_tags.py` | company_analysis | 加 `product_tags JSONB DEFAULT '[]'::jsonb` |
| `backfill_product_tags_v2.py` | company_analysis | 加 `tag_confidence JSONB DEFAULT '{}'::jsonb` |
| `migrate_contact_classification_v2.sql` | contact_data (视图) | 重建 `classify_contact()` 函数和 `v_buyer_contacts` 视图 |
