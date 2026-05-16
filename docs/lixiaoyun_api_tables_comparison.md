# lixiaoyun_api_clean_companies vs lixiaoyun_api_companies 字段对比

> 数据来源：线上数据库 (Sealos)，查询时间 2026-05-16（第三次拉取）

## 共有字段（48 个）

| # | 字段名 | clean_companies | companies | 差异 |
|---|---|---|---|---|
| 1 | `id` | bigint, PK, 自增 | bigint, PK, 自增 | 无 |
| 2 | `pid` | text, NOT NULL, **UNIQUE** | text, NOT NULL | clean 多唯一约束 |
| 3 | `entname` | text | text | 无 |
| 4 | `entname_eng` | text | text | 无 |
| 5 | `legalperson` | text | text | 无 |
| 6 | `uncid` | text | text | 无 |
| 7 | `esdate` | bigint | bigint | 无 |
| 8 | `reg_cap` | text | text | 无 |
| 9 | `regccap` | text | text | 无 |
| 10 | `enttype` | text | text | 无 |
| 11 | `entstatus` | text | text | 无 |
| 12 | `geo_address` | text | text | 无 |
| 13 | `dom` | text | text | 无 |
| 14 | `province` | integer | integer | 无 |
| 15 | `city` | integer | integer | 无 |
| 16 | `district` | integer | integer | 无 |
| 17 | `industryphy_desc` | text | text | 无 |
| 18 | `opscope` | text | text | 无 |
| 19 | `scale` | text | text | 无 |
| 20 | `annual_turnover` | text | text | 无 |
| 21 | `official_website` | text | text | 无 |
| 22 | `ent_introduction` | text | text | 无 |
| 23 | `location_code` | text | text, **NOT NULL**, default '' | companies 有非空约束+默认值 |
| 24 | `collected_at` | timestamptz | timestamptz, **NOT NULL**, default now() | companies 有非空约束+默认值 |
| 25 | `enttype_code` | text | text | 无 |
| 26 | `regno` | text | text | 无 |
| 27 | `organizational_code` | text | text | 无 |
| 28 | `opfrom` | bigint | bigint | 无 |
| 29 | `opto` | bigint | bigint | 无 |
| 30 | `regorg` | text | text | 无 |
| 31 | `apprdate` | bigint | bigint | 无 |
| 32 | `revokedate` | bigint | bigint | 无 |
| 33 | `reg_province` | integer | integer | 无 |
| 34 | `reg_city` | integer | integer | 无 |
| 35 | `reg_district` | integer | integer | 无 |
| 36 | `oploc` | text | text | 无 |
| 37 | `entstatus_code` | integer | integer | 无 |
| 38 | `industryphy` | text | text | 无 |
| 39 | `secindustry` | jsonb | jsonb | 无 |
| 40 | `secindustry_desc` | jsonb | jsonb | 无 |
| 41 | `industry_l3` | text | text | 无 |
| 42 | `industry_l3_desc` | text | text | 无 |
| 43 | `industry_l4` | text | text | 无 |
| 44 | `industry_l4_desc` | text | text | 无 |
| 45 | `historyname_list` | jsonb | jsonb | 无 |
| 46 | `legalperson_desc` | text | text | 无 |
| 47 | `search_payload` | jsonb | jsonb | 无 |
| 48 | `baseinfo_payload` | jsonb | jsonb | 无 |

## 仅 clean_companies 有的字段（5 个）

| 字段名 | 类型 | 说明 |
|---|---|---|
| `keyword_master_ids` | **uuid[]** | 关联的关键词主表 ID（数组，聚合多来源） |
| `source_record_ids` | bigint[] | 聚合来源的原始记录 ID |
| `created_at` | timestamptz, NOT NULL, default now() | 创建时间 |
| `updated_at` | timestamptz, NOT NULL, default now() | 更新时间 |
| `industry_tags` | **text** | 行业标签（纯文本） |

## 仅 companies（原始表）有的字段（1 个）

| 字段名 | 类型 | 说明 |
|---|---|---|
| `keyword_master_id` | **uuid**, FK -> keyword_master | 关联关键词（单值外键） |

## 索引对比

| 索引 | clean_companies | companies |
|---|---|---|
| PK | btree (id) | btree (id) |
| pid | btree (pid) + UNIQUE | btree (pid) |
| entname | btree (entname) | btree (entname) |
| uncid | btree (uncid) | btree (uncid) |
| keyword | **GIN** (keyword_master_ids) | btree (keyword_master_id) |
| location_code | - | btree (location_code) |
| collected_at | - | btree (collected_at DESC) |

## 关键差异总结

- **字段数量**：clean 53 列，原始表 49 列（clean 是超集）
- **keyword 关联**：原始表用单个 `keyword_master_id`（一对一 FK），清洗表用 `keyword_master_ids` 数组（聚合多来源）
- **约束差异**：`location_code` 和 `collected_at` 在原始表有 NOT NULL + 默认值，在清洗表为可空
- **industry_tags**：clean 表独有，类型为 `text`（非数组）
- **设计思路**：`companies` 是按关键词采集的原始记录（一个公司可有多条），`clean_companies` 是按 pid 去重聚合后的结果（一条/公司）
