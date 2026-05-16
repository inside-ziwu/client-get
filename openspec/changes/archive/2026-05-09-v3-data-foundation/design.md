# Design · v3-data-foundation

> **范围**：V3 数据基础层真源。本文只定义 schema、关系、索引、API contract 与迁移边界；不定义 cleanup_service、worker base、Sealos 部署、AI 回填、同行重构等实现细节。
> **审查状态（2026-05-08）**：Spec Review Passed / Ready for Implementation。该状态仅表示规格审查通过，不表示 migration / API / 前端实现已完成。

## 1. Scope

本 change 覆盖：

| 模块 | 表 / 内容 |
|---|---|
| 关键词 | `keyword_master` / `tenant_keyword` |
| 励销云 raw | `lixiaoyun_raw_companies` / `lixiaoyun_raw_contacts` |
| 腾道 raw | `tendata_raw_companies` / `tendata_raw_contacts` |
| clean 客户 | `clean_companies` / `clean_contacts` / `clean_company_sources` / `clean_company_keywords` |
| 租户视图 | `tenant_companies` / `tenant_contacts` |
| 采集运行 | `collection_runs` / `collection_tasks.run_id` |
| API | admin + tenant contract 初稿 |
| 索引 | 支持 10 项客户筛选 |

本 change 不覆盖：

| 移出内容 | 建议归属 |
|---|---|
| cleanup_service 实现 | `v3-cleanup-pipeline` 或后续 collection 实施 change |
| worker base class | worker runtime / deploy change |
| Sealos / Docker 部署 | deploy change |
| AI 回填 / OpenRouter 计费 | enrichment change |
| competitor 同行重构 | competitor change |
| 群组 / 邮件计划 / 调分历史 | 对应业务模块 change |

## 2. Schema

### 2.1 keyword_master

平台级关键词。租户输入先归一化，再映射到这里。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | uuid | 平台关键词 ID | 主键 |
| keyword | text | 平台展示关键词 | 例如 `PCB` |
| keyword_normalized | text | 平台归一化关键词 | 全局唯一；大小写、空格、标点归一 |
| created_at | timestamptz | 创建时间 | 平台关键词首次写入时间 |

关键词归一化规则：
- 去除首尾空白，连续空白折叠为一个空格
- 英文字母统一小写
- 全角字符转半角
- 移除不承载业务语义的常见分隔符与标点，例如空格、`.`、`_`
- 保留可能承载业务语义的符号，不自动合并，例如 `FR-4` 不等价于 `FR4`，`C++` 不等价于 `C`
- 例：`P.C.B` / `pcb` / `PCB ` 归一为同一个平台关键词

约束 / 索引：

```sql
PRIMARY KEY (id)
UNIQUE (keyword_normalized)
```

### 2.2 tenant_keyword

租户级关键词。保存租户原始输入，并关联平台关键词。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 租户关键词 ID | 主键 |
| tenant_id | uuid | 租户 ID | FK → tenants.id |
| keyword_master_id | uuid | 平台关键词 ID | FK → keyword_master.id |
| keyword_raw | text | 租户原始输入 | 例如 `P.C.B` / `pcb` / `PCB ` |
| created_by | uuid | 创建人 | FK → users.id，可为空 |
| created_at | timestamptz | 创建时间 | 订阅关系首次创建时间 |
| status | text | 状态 | `active` / `deleted` |

逻辑：
- 新增关键词：归一化 `keyword_raw` → upsert `keyword_master` → insert / restore `tenant_keyword`
- 删除关键词：软删为 `deleted`
- 删除后重新添加同一平台关键词：恢复旧行并更新 `keyword_raw`
- 租户新增同词只改变订阅关系，不创建、不重启、不停止采集 run

约束 / 索引：

```sql
PRIMARY KEY (id)
UNIQUE (tenant_id, keyword_master_id)
CHECK (status IN ('active', 'deleted'))
INDEX (tenant_id, status)
INDEX (keyword_master_id)
```

### 2.3 lixiaoyun_raw_companies

励销云 raw 公司表。保存来源侧原始公司数据。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 励销云 raw 公司 ID | 主键 |
| keyword_master_id | uuid | 平台关键词 ID | FK → keyword_master.id；关联采集关键词 |
| source_id | text | 励销云公司 ID | 来源侧唯一标识 |
| name | text | 公司中文名 | 来源字段 |
| english_name | text | 公司英文名 | 来源字段 |
| domain | text | 域名 | 来源字段 |
| esdate | date | 成立日期 | 来源字段 |
| legalperson | text | 法人 | 来源字段 |
| uncid | text | 统一社会信用代码 | 来源字段 |
| reg_capital | text | 注册资金 | 来源原始口径 |
| employee_scale | text | 人员规模 | 来源原始口径 |
| reg_address | text | 注册地址 | 来源字段 |
| raw_payload | jsonb | 原始返回体 | 保存完整来源数据，便于追溯 |
| created_at | timestamptz | 入库时间 | raw 行创建时间 |

不保留：
- `task_id`
- `keyword_normalized`
- `last_seen_at`

约束 / 索引：

```sql
PRIMARY KEY (id)
UNIQUE (keyword_master_id, source_id)
INDEX (keyword_master_id)
INDEX (source_id)
```

### 2.4 lixiaoyun_raw_contacts

励销云 raw 联系人表。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 励销云 raw 联系人 ID | 主键 |
| raw_company_id | bigint | raw 公司 ID | FK → lixiaoyun_raw_companies.id |
| source_contact_id | text | 来源联系人 ID | 来源侧联系人唯一标识，可为空 |
| name | text | 姓名 | 来源字段 |
| position | text | 职位 | 来源字段 |
| email | citext | 邮箱 | 来源字段 |
| phone | text | 联系方式 | 来源字段 |
| raw_payload | jsonb | 原始返回体 | 保存完整来源联系人数据 |
| created_at | timestamptz | 入库时间 | raw 行创建时间 |

约束 / 索引：

```sql
PRIMARY KEY (id)
INDEX (raw_company_id)
UNIQUE (raw_company_id, source_contact_id) WHERE source_contact_id IS NOT NULL
UNIQUE (raw_company_id, email) WHERE source_contact_id IS NULL AND email IS NOT NULL
INDEX (email) WHERE email IS NOT NULL
```

API 暴露边界：
- admin raw 列表 / 详情 API 默认不返回 `raw_payload`
- `raw_payload` 仅作为内部排查字段，由后端按现有 admin 鉴权边界决定是否提供专门调试接口
- 本 change 不新增独立的 email / phone 字段级权限模型；raw API 如返回联系人字段，沿用现有 admin 权限边界

### 2.5 tendata_raw_companies

腾道 raw 公司表。采集回来就是数组的字段在 raw 表保留数组。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 腾道 raw 公司 ID | 主键 |
| keyword_master_id | uuid | 平台关键词 ID | FK → keyword_master.id；关联采集关键词 |
| source_id | text | 腾道公司 ID | 来源侧唯一标识；承接旧 `tid` |
| globiz_id | text | 腾道企业全局 ID | 可空；用于跨接口追溯 |
| name | text | 公司名 | 来源字段 |
| name_local | text | 本地名 | 来源字段 |
| country_iso3 | char(3) | 国家 | ISO3 |
| website | text | 官网 | 来源字段 |
| tax_no | text | 税号 | 来源字段 |
| incorporation_date | date | 成立日期 | 来源字段 |
| employee_num | text | 公司规模 | 来源原始口径 |
| industry_desc | text | 行业描述 | 来源字段 |
| product_tags | text[] | 产品标签 | 来源数组 |
| pcb_suppliers | text[] | 中国 PCB 供应商名单 | 来源数组；反推证据 |
| trade_amount_3y_usd | numeric | 近 3 年进出口金额 | 来源口径一致，不额外拆币种 |
| trade_count | int | 进出口次数 | 来源字段 |
| contacts_count | int | 联系人数 | 来源字段 |
| has_trade_data | boolean | 是否有贸易数据 | 来源字段 |
| aliases | text[] | 别名 | 来源数组 |
| raw_payload | jsonb | 原始返回体 | 保存完整来源数据 |
| created_at | timestamptz | 入库时间 | raw 行创建时间 |

不保留：
- `task_id`
- `keyword_normalized`
- `last_seen_at`

约束 / 索引：

```sql
PRIMARY KEY (id)
UNIQUE (keyword_master_id, source_id)
INDEX (keyword_master_id)
INDEX (source_id)
INDEX (globiz_id) WHERE globiz_id IS NOT NULL
INDEX (country_iso3)
```

API 暴露边界：
- admin raw 列表 / 详情 API 默认不返回 `raw_payload`
- `raw_payload` 仅作为内部排查字段，由后端按现有 admin 鉴权边界决定是否提供专门调试接口

### 2.6 tendata_raw_contacts

腾道 raw 联系人表。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 腾道 raw 联系人 ID | 主键 |
| raw_company_id | bigint | raw 公司 ID | FK → tendata_raw_companies.id |
| source_contact_id | text | 来源联系人 ID | 来源侧联系人唯一标识，可为空 |
| name | text | 姓名 | 来源字段 |
| position | text | 职位 | 来源字段 |
| email | citext | 邮箱 | 来源字段 |
| phone | text | 联系方式 | 来源字段 |
| raw_payload | jsonb | 原始返回体 | 保存完整来源联系人数据 |
| created_at | timestamptz | 入库时间 | raw 行创建时间 |

约束 / 索引：

```sql
PRIMARY KEY (id)
INDEX (raw_company_id)
UNIQUE (raw_company_id, source_contact_id) WHERE source_contact_id IS NOT NULL
UNIQUE (raw_company_id, email) WHERE source_contact_id IS NULL AND email IS NOT NULL
INDEX (email) WHERE email IS NOT NULL
```

API 暴露边界：
- admin raw 列表 / 详情 API 默认不返回 `raw_payload`
- 本 change 不新增独立的 email / phone 字段级权限模型；raw API 如返回联系人字段，沿用现有 admin 权限边界

### 2.7 clean_companies

平台级干净客户公司资产。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 干净客户公司 ID | 主键，平台级客户资产 |
| name | text | 公司名 | 展示名 |
| name_normalized | text | 归一化公司名 | 用于去重 |
| country_iso3 | char(3) | 国家 | 10 项筛选：国家 |
| website | text | 官网 | 清洗后字段 |
| tax_no | text | 税号 | 清洗后字段 |
| incorporation_date | date | 成立日期 | 10 项筛选：成立时间 |
| reg_capital | numeric | 注册资金 | 10 项筛选：注册资金；来源口径一致 |
| employee_num | text | 公司规模 | 10 项筛选：公司规模 |
| industry_desc | text | 行业描述 | 展示 / 清洗输入 |
| industry_tags | text[] | 行业细分 | 10 项筛选：行业细分 |
| product_tags | text[] | 产品标签 | 10 项筛选：产品标签 |
| pcb_suppliers | text[] | 中国 PCB 供应商名单 | 来源数组；保留在主表 |
| trade_amount_3y_usd | numeric | 近 3 年进出口金额 | 10 项筛选：进出口金额 |
| trade_count | int | 进出口次数 | 10 项筛选：进出口次数 |
| contacts_count | int | 联系人数 | 10 项筛选：联系人数；由联系人同步维护 |
| created_at | timestamptz | 创建时间 | 首次进入 clean 层时间 |
| updated_at | timestamptz | 更新时间 | clean 数据更新时间 |

不保留：
- `data_completeness`
- `sources text[]`，改用 `clean_company_sources`

公司规模口径：
- 本期不新增 `employee_num` 档位归一字段
- `employee_num` 保留来源文本口径，筛选按来源枚举值 / 前端选项映射处理
- 如后续需要区间筛或统一档位，再独立增加 `employee_num_min/max` 或 `employee_band`

约束 / 索引：

```sql
PRIMARY KEY (id)
UNIQUE (name_normalized, country_iso3)
INDEX (country_iso3)
INDEX (incorporation_date)
INDEX (reg_capital)
GIN (industry_tags)
GIN (product_tags)
INDEX (employee_num)
INDEX (trade_amount_3y_usd)
INDEX (trade_count)
INDEX (contacts_count)
```

### 2.8 clean_contacts

平台级干净联系人。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 干净联系人 ID | 主键 |
| clean_company_id | bigint | 干净客户公司 ID | FK → clean_companies.id |
| name | text | 姓名 | 清洗后字段 |
| position | text | 职位 | 清洗后字段 |
| email | citext | 邮箱 | 清洗后字段 |
| phone | text | 联系方式 | 清洗后字段 |
| created_at | timestamptz | 创建时间 | 首次进入 clean 层时间 |
| updated_at | timestamptz | 更新时间 | clean 联系人更新时间 |

约束 / 索引：

```sql
PRIMARY KEY (id)
INDEX (clean_company_id)
UNIQUE (clean_company_id, email) WHERE email IS NOT NULL
INDEX (email) WHERE email IS NOT NULL
```

### 2.9 clean_company_sources

clean 公司与 raw 来源的 1:N 关系。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 来源关联 ID | 主键 |
| clean_company_id | bigint | 干净客户公司 ID | FK → clean_companies.id |
| source_type | text | 来源类型 | `tendata` / 后续扩展其他来源 |
| source_company_id | bigint | raw 公司 ID | 对应来源 raw 表主键 |
| source_key | text | 来源侧唯一 key | 例如腾道 `source_id` |
| created_at | timestamptz | 创建时间 | 建立来源关系时间 |

逻辑：
- V3 clean 客户来源只允许 `tendata`
- 励销云 raw 只作为同行 / 反推输入，不进入 `clean_company_sources`
- 未来接入外贸通时再扩展 `source_type = 'waimaotong'`

约束 / 索引：

```sql
PRIMARY KEY (id)
UNIQUE (source_type, source_company_id)
CHECK (source_type IN ('tendata'))
INDEX (clean_company_id)
INDEX (source_type)
```

### 2.10 clean_company_keywords

clean 公司与平台关键词的 M:N 事实表。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 关联 ID | 主键 |
| clean_company_id | bigint | 干净客户公司 ID | FK → clean_companies.id |
| keyword_master_id | uuid | 平台关键词 ID | FK → keyword_master.id |
| created_at | timestamptz | 创建时间 | 建立关键词命中关系时间 |

逻辑：
- 存平台级事实，不直接存 `tenant_keyword_id`
- tenant API 通过 `clean_company_keywords + tenant_keyword` join 透出租户当前 `keyword_raw`

约束 / 索引：

```sql
PRIMARY KEY (id)
UNIQUE (clean_company_id, keyword_master_id)
INDEX (keyword_master_id)
```

### 2.11 tenant_companies

租户客户公司视图表。只存租户私有状态与评分结果，不重复 clean 主数据。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 租户客户公司 ID | 主键 |
| tenant_id | uuid | 租户 ID | FK → tenants.id |
| clean_company_id | bigint | 干净客户公司 ID | FK → clean_companies.id |
| business_status | text | 业务状态 | 租户推进状态，如 `new` / `selected` / `in_plan` / `contacted` / `archived` |
| data_status | text | 数据状态 | 租户视角数据可用性，如 `ready` / `missing_contacts` / `insufficient_data` |
| model_score | numeric | 任务自动评分结果 | 原模型评分 |
| score | numeric | 当前评分值 | 本期等于模型评分；未来调分历史独立表改写 |
| note | text | 备注 | 租户私有 |
| tags | text[] | 标签 | 租户私有标签 |
| created_at | timestamptz | 创建时间 | 进入租户视图时间 |
| updated_at | timestamptz | 更新时间 | 租户视图更新时间 |

不保留：
- `matched_keywords jsonb`，改由 `clean_company_keywords + tenant_keyword` 关联查询
- 所有调分字段，未来独立调分历史表
- 群组 / 邮件计划关联，归对应模块表

约束 / 索引：

```sql
PRIMARY KEY (id)
UNIQUE (tenant_id, clean_company_id)
INDEX (tenant_id, business_status)
INDEX (tenant_id, data_status)
INDEX (tenant_id, score)
GIN (tags)
```

### 2.12 tenant_contacts

租户联系人视图表。关联 clean 联系人并存租户侧状态；不作为联系人可见性的唯一入口。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 租户联系人 ID | 主键 |
| tenant_id | uuid | 租户 ID | FK → tenants.id |
| clean_contact_id | bigint | 干净联系人 ID | FK → clean_contacts.id |
| clean_company_id | bigint | 干净客户公司 ID | FK → clean_companies.id；便于列表查询 |
| contact_status | text | 联系人状态 | 租户侧联系人状态 |
| is_sendable | boolean | 是否可投递 | 来自职位分类 / 邮件规则结果 |
| created_at | timestamptz | 创建时间 | 进入租户视图时间 |
| updated_at | timestamptz | 更新时间 | 租户联系人更新时间 |

联系人可见性：
- 租户是否可看某联系人，由其所属 `clean_company_id` 是否对当前租户可见决定
- 公司可见性通过 `clean_company_keywords + tenant_keyword` 判断：该 clean 公司命中当前租户 active 关键词即可见
- 一家公司对租户可见后，该公司下的 `clean_contacts` 均可见
- `tenant_contacts` 仅保存租户侧联系人状态，不新增“联系人单独授权”规则

约束 / 索引：

```sql
PRIMARY KEY (id)
UNIQUE (tenant_id, clean_contact_id)
INDEX (tenant_id, clean_company_id)
INDEX (tenant_id, contact_status)
INDEX (tenant_id, is_sendable)
```

### 2.13 collection_runs

一个平台关键词的一轮持续采集。

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| id | bigint identity | 采集 run ID | 主键 |
| keyword_master_id | uuid | 平台关键词 ID | FK → keyword_master.id |
| provider | text | 数据源 | `lixiaoyun` / `tendata` |
| stage | text | 采集阶段 | provider-specific；`lixiaoyun_competitors` / `tendata_customers` |
| status | text | run 状态 | `not_started` / `running` / `daily_limit_reached` / `completed` / `stopped` / `failed` |
| daily_limit | int | 每日上限 | 励销云默认 1000 |
| request_page_size | int | 单次请求条数 | 默认 10，最大 100 |
| cursor | jsonb | 续采 cursor | 跨天续采位置 |
| skip_source_ids | jsonb | 跳过/已见来源 ID | 防重复 |
| total_fetched | int | 本轮累计采集数 | run 统计 |
| today_fetched | int | 今日采集数 | 北京时间自然日统计 |
| biz_date | date | 业务日期 | 北京时间日期 |
| next_run_at | timestamptz | 下次运行时间 | 达上限后的次日 08:00 |
| manual_stopped_at | timestamptz | 手动停止时间 | 可为空 |
| completed_at | timestamptz | 完成时间 | 可为空 |
| error_message | text | 错误摘要 | 可为空 |
| triggered_by | uuid | 触发用户 | FK → users.id，可为空 |
| triggered_tenant_id | uuid | 首采归属租户 | FK → tenants.id，可为空；admin 点击采集时，从该关键词当前 active 订阅中取最早订阅租户写入 |
| created_at | timestamptz | 创建时间 | run 创建时间 |
| updated_at | timestamptz | 更新时间 | run 更新时间 |

约束 / 索引：

```sql
PRIMARY KEY (id)
CHECK (provider IN ('lixiaoyun', 'tendata'))
CHECK (stage IN ('lixiaoyun_competitors', 'tendata_customers'))
CHECK (
  (provider = 'lixiaoyun' AND stage = 'lixiaoyun_competitors')
  OR
  (provider = 'tendata' AND stage = 'tendata_customers')
)
CHECK (status IN ('not_started', 'running', 'daily_limit_reached', 'completed', 'stopped', 'failed'))
INDEX (keyword_master_id, provider, stage, status)
INDEX (next_run_at) WHERE status = 'daily_limit_reached'
INDEX (triggered_tenant_id) WHERE triggered_tenant_id IS NOT NULL
UNIQUE (keyword_master_id, provider, stage)
  WHERE status IN ('not_started', 'running', 'daily_limit_reached')
```

首采归属租户写入规则：
- 租户新增关键词只写 `tenant_keyword` 订阅关系，不直接创建或触发采集 run
- admin 点击采集并创建 `collection_run` 时，查询该 `keyword_master_id` 当前仍 `active` 的 `tenant_keyword`
- 按 `tenant_keyword.created_at ASC, tenant_keyword.id ASC` 取最早订阅租户
- 将该租户写入 `collection_runs.triggered_tenant_id`
- 如果该关键词当前没有 active 租户订阅，`triggered_tenant_id` 可以为空
- 删除后恢复同一 `tenant_keyword` 时不刷新 `created_at`；“最早订阅”始终按原始 `created_at` 判断
- 本期不新增 `activated_at`；若未来需要按“最近恢复订阅时间”归属，再单独扩展

参考查询：

```sql
SELECT tenant_id
FROM tenant_keyword
WHERE keyword_master_id = :keyword_master_id
  AND status = 'active'
ORDER BY created_at ASC, id ASC
LIMIT 1;
```

### 2.14 collection_tasks 调整

`collection_tasks` 只表达单次执行批次的数据结构，run 级状态放在 `collection_runs`。任务调度、领取和执行策略归后续 collection / worker change 定义。

新增 / 调整字段：

| 字段 | 类型 | 中文释义 | 逻辑 |
|---|---|---|---|
| run_id | bigint | 采集 run ID | FK → collection_runs.id |
| scheduled_biz_date | date | 计划业务日期 | 北京时间日期 |
| batch_no | int | 批次号 | run 内第几批 |
| page_size | int | 本批请求条数 | 默认 10，最大 100 |
| cursor_snapshot | jsonb | 执行前 cursor | 单批快照 |

索引：

```sql
INDEX (run_id, status, scheduled_at)
```

## 3. Relationships

```text
keyword_master
  ├─ tenant_keyword
  ├─ collection_runs
  │   └─ collection_tasks
  └─ clean_company_keywords
      └─ clean_companies

tendata_raw_companies
  └─ clean_company_sources
      └─ clean_companies
          ├─ clean_contacts
          ├─ tenant_companies
          └─ tenant_contacts
```

关键词透出逻辑：

```sql
SELECT tk.id AS tenant_keyword_id, tk.keyword_raw, km.id AS keyword_master_id
FROM clean_company_keywords cck
JOIN keyword_master km ON km.id = cck.keyword_master_id
JOIN tenant_keyword tk ON tk.keyword_master_id = km.id
WHERE cck.clean_company_id = :clean_company_id
  AND tk.tenant_id = :tenant_id
  AND tk.status = 'active';
```

租户公司可见性逻辑：

```sql
SELECT cc.*
FROM clean_companies cc
JOIN clean_company_keywords cck ON cck.clean_company_id = cc.id
JOIN tenant_keyword tk ON tk.keyword_master_id = cck.keyword_master_id
WHERE cc.id = :clean_company_id
  AND tk.tenant_id = :tenant_id
  AND tk.status = 'active';
```

说明：
- 租户侧客户详情的 `{id}` 指 `clean_companies.id`
- 详情展示的是干净公司库数据，并通过当前租户 active 关键词关系确认可见
- `tenant_companies` 只承载租户私有状态、评分、备注、标签；详情接口可按 `(tenant_id, clean_company_id)` left join 这些私有字段
- 联系人列表先按同一套公司可见性校验公司，再返回该 `clean_company_id` 下的 `clean_contacts`，并 left join `tenant_contacts` 叠加租户侧联系人状态

## 4. Index Strategy For 10 Filters

| 筛选项 | 字段 / 表 | 索引 |
|---|---|---|
| 国家 | `clean_companies.country_iso3` | btree |
| 行业细分 | `clean_companies.industry_tags` | GIN |
| 成立时间 | `clean_companies.incorporation_date` | btree |
| 注册资金 | `clean_companies.reg_capital` | btree |
| 产品标签 | `clean_companies.product_tags` | GIN |
| 公司规模 | `clean_companies.employee_num` | btree |
| 数据来源 | `clean_company_sources.source_type` | btree + `clean_company_id`；V3 仅 `tendata` |
| 进出口金额 | `clean_companies.trade_amount_3y_usd` | btree |
| 进出口次数 | `clean_companies.trade_count` | btree |
| 联系人数 | `clean_companies.contacts_count` | btree |

租户侧组合查询先用 `clean_company_keywords + tenant_keyword` 限定当前租户可见 clean 公司，再 join `clean_companies / clean_company_sources`。`tenant_companies(tenant_id, clean_company_id)` 作为租户私有状态 overlay，不作为客户可见性的唯一入口。

## 5. API Contract

### 5.1 Admin APIs

| 方法 | 路径 | 用途 | 关键参数 | 返回核心字段 |
|---|---|---|---|---|
| GET | `/admin/api/v1/keywords` | 平台关键词列表 | `q,status,provider,stage` | `keyword_master`, latest `collection_run`, active tenant count |
| POST | `/admin/api/v1/keywords/{keyword_master_id}/runs` | 启动采集 run | `provider,stage,request_page_size` | `collection_run` |
| POST | `/admin/api/v1/collection-runs/{run_id}/stop` | 停止 run | - | `collection_run.status` |
| GET | `/admin/api/v1/collection-runs/{run_id}/tasks` | run 下 task 列表 | `status` | `collection_tasks` |
| GET | `/admin/api/v1/raw/lixiaoyun/companies` | 励销云 raw 公司 | `keyword_master_id,q,page` | `lixiaoyun_raw_companies`，默认不含 `raw_payload` |
| GET | `/admin/api/v1/raw/tendata/companies` | 腾道 raw 公司 | `keyword_master_id,country,page` | `tendata_raw_companies`，默认不含 `raw_payload` |
| GET | `/admin/api/v1/clean/companies` | clean 客户列表 | 10 项筛选 | `clean_companies` + source/keyword summary |
| GET | `/admin/api/v1/clean/companies/{id}` | clean 客户详情 | - | company + contacts + sources + keywords |

### 5.2 Tenant APIs

| 方法 | 路径 | 用途 | 关键参数 | 返回核心字段 |
|---|---|---|---|---|
| GET | `/t/{tenant_slug}/api/v1/keywords` | 租户关键词列表 | `status` | `tenant_keyword` + `keyword_master` |
| POST | `/t/{tenant_slug}/api/v1/keywords` | 新增租户关键词 | `keyword_raw` | restored/created `tenant_keyword` |
| DELETE | `/t/{tenant_slug}/api/v1/keywords/{id}` | 删除租户关键词 | - | `status=deleted` |
| GET | `/t/{tenant_slug}/api/v1/companies` | 租户客户列表 | 10 项筛选 + `business_status,data_status,score` | 当前租户可见 `clean_companies` + tenant state overlay |
| GET | `/t/{tenant_slug}/api/v1/companies/{id}` | 租户客户详情 | `{id}` = `clean_companies.id` | clean company + tenant state overlay + sources + matched tenant keywords |
| GET | `/t/{tenant_slug}/api/v1/companies/{id}/contacts` | 租户客户联系人 | `{id}` = `clean_companies.id`; `contact_status,is_sendable` | `clean_contacts` + tenant contact state overlay |

租户 API 统一使用现有 V3 路由风格 `/t/{tenant_slug}/api/v1/...`。后端必须从当前租户上下文读取 `tenant_id`，不得信任请求参数传入的 `tenant_id`。

### 5.3 Tenant Company List Filters

| API 参数 | 对应字段 |
|---|---|
| `country_iso3` | `clean_companies.country_iso3` |
| `industry_tags` | `clean_companies.industry_tags` |
| `incorporation_date_from/to` | `clean_companies.incorporation_date` |
| `reg_capital_min/max` | `clean_companies.reg_capital` |
| `product_tags` | `clean_companies.product_tags` |
| `employee_num` | `clean_companies.employee_num`；本期按来源文本枚举 / 前端选项映射 |
| `source_type` | `clean_company_sources.source_type`；V3 仅 `tendata` |
| `trade_amount_min/max` | `clean_companies.trade_amount_3y_usd` |
| `trade_count_min/max` | `clean_companies.trade_count` |
| `contacts_count_min/max` | `clean_companies.contacts_count` |

## 6. Legacy Table Policy

| 旧表 | V3 处理 |
|---|---|
| `collection_keywords` | 只作为迁移输入：归一化后写入 `keyword_master` + `tenant_keyword` |
| `collection_task_keywords` | 只作为历史任务归属迁移输入；目标模型不再依赖 |
| `competitor_companies / competitor_contacts` | 不在本 change 定义；同行模型另行处理 |

新 API / worker / 前端不得读取旧表字段作为 V3 真源。

## 7. Closed Decisions

| 问题 | 决策 |
|---|---|
| `employee_num` 是否后续归一成档位 | 本期不新增归一字段，保留来源文本口径；筛选用来源枚举值 / 前端选项映射处理 |

## 8. Verification Checklist

- [ ] 12 张表全部存在且字段口径一致
- [ ] `collection_runs` 与 `collection_tasks.run_id` 存在
- [ ] 旧 `collection_keywords / collection_task_keywords` 不再是目标真源
- [ ] 10 项筛选都有字段与索引支撑
- [ ] API contract 的字段均能追溯到表或关联关系
- [ ] 本 change 不包含 cleanup_service / worker base / Sealos / AI 回填 / competitor 重构实现范围
