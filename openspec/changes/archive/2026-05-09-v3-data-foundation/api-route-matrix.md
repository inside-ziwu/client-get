# API Route Matrix · v3-data-foundation

> 范围：只定义 data foundation contract，确保前后端字段、参数、schema 来源对齐。不包含 worker 执行、cleanup_service、AI enrichment、群组、邮件计划、调分历史实现。

## 1. Admin Routes

| 方法 | 路径 | 用途 | 参数 | 字段来源 | 关键响应字段 |
|---|---|---|---|---|---|
| GET | `/admin/api/v1/keywords` | 平台关键词列表 | `q,status,provider,stage,page,page_size` | `keyword_master` + `tenant_keyword` + latest `collection_runs` | `id,keyword,keyword_normalized,created_at,active_tenant_count,latest_run` |
| POST | `/admin/api/v1/keywords/{keyword_master_id}/runs` | 启动采集 run | body: `provider,stage,request_page_size` | `collection_runs` | `id,keyword_master_id,provider,stage,status,triggered_tenant_id` |
| POST | `/admin/api/v1/collection-runs/{run_id}/stop` | 停止 run | - | `collection_runs` | `id,status,manual_stopped_at` |
| GET | `/admin/api/v1/collection-runs/{run_id}/tasks` | run 下 task 列表 | `status,page,page_size` | `collection_tasks` | `id,run_id,status,scheduled_at,scheduled_biz_date,batch_no,page_size,cursor_snapshot` |
| GET | `/admin/api/v1/raw/lixiaoyun/companies` | 励销云 raw 公司列表 | `keyword_master_id,q,page,page_size` | `lixiaoyun_raw_companies` | raw 公司字段；默认不返回 `raw_payload` |
| GET | `/admin/api/v1/raw/tendata/companies` | 腾道 raw 公司列表 | `keyword_master_id,country_iso3,page,page_size` | `tendata_raw_companies` | raw 公司字段；默认不返回 `raw_payload` |
| GET | `/admin/api/v1/clean/companies` | clean 客户列表 | 10 项筛选 | `clean_companies` + `clean_company_sources` + `clean_company_keywords` | clean 公司字段 + source / keyword summary |
| GET | `/admin/api/v1/clean/companies/{id}` | clean 客户详情 | `{id}=clean_companies.id` | `clean_companies` + `clean_contacts` + sources + keywords | company + contacts + sources + keywords |

### Compatibility Routes

| 现有路径 | V3 状态 |
|---|---|
| `/admin/api/v1/collection-keywords*` | 兼容旧前端/旧采集控制，不作为 V3 data foundation 真源 |
| `/admin/api/v1/collection/raw/{table}` | 兼容旧路径；新增 raw contract 路径以 `/raw/{provider}/companies` 为准 |
| `/admin/api/v1/collection/clean-companies` | 兼容旧路径；新增 clean contract 路径以 `/clean/companies` 为准 |

## 2. Tenant Routes

| 方法 | 路径 | 用途 | 参数 | 字段来源 | 关键响应字段 |
|---|---|---|---|---|---|
| GET | `/t/{tenant_slug}/api/v1/keywords` | 租户关键词列表 | `status` | `tenant_keyword` + `keyword_master` | `id,tenant_id,keyword_master_id,keyword_raw,keyword,keyword_normalized,status,created_at` |
| POST | `/t/{tenant_slug}/api/v1/keywords` | 新增/恢复租户关键词 | body: `keyword_raw`（兼容 `keyword`） | `keyword_master` + `tenant_keyword` | restored/created tenant keyword |
| DELETE | `/t/{tenant_slug}/api/v1/keywords/{id}` | 删除租户关键词 | `{id}=tenant_keyword.id` | `tenant_keyword` | `status=deleted` |
| GET | `/t/{tenant_slug}/api/v1/companies` | 租户可见客户列表 | 10 项筛选 + `business_status,data_status,score` | visibility: `clean_company_keywords + tenant_keyword`; overlay: `tenant_companies` | clean 公司字段 + tenant state + matched tenant keywords |
| GET | `/t/{tenant_slug}/api/v1/companies/{id}` | 租户客户详情 | `{id}=clean_companies.id` | `clean_companies` + visibility join + tenant overlay + sources + keywords | company + sources + matched tenant keywords + tenant state |
| GET | `/t/{tenant_slug}/api/v1/companies/{id}/contacts` | 租户客户联系人 | `{id}=clean_companies.id`, `contact_status,is_sendable` | `clean_contacts` + `tenant_contacts` overlay | clean 联系人字段 + tenant contact state |

租户接口统一从 token / path 上下文解析当前租户，不接受请求参数中的 `tenant_id` 作为授权依据。

## 3. Tenant Company Filters

| API 参数 | schema 字段 | 说明 |
|---|---|---|
| `country_iso3` | `clean_companies.country_iso3` | 国家 |
| `industry_tags` | `clean_companies.industry_tags` | 行业细分，多值 OR |
| `incorporation_date_from/to` | `clean_companies.incorporation_date` | 成立日期区间 |
| `reg_capital_min/max` | `clean_companies.reg_capital` | 注册资金区间 |
| `product_tags` | `clean_companies.product_tags` | 产品标签，多值 OR |
| `employee_num` | `clean_companies.employee_num` | 公司规模，来源文本口径 |
| `source_type` | `clean_company_sources.source_type` | 数据来源；V3 仅 `tendata` |
| `trade_amount_min/max` | `clean_companies.trade_amount_3y_usd` | 进出口金额 |
| `trade_count_min/max` | `clean_companies.trade_count` | 进出口次数 |
| `contacts_count_min/max` | `clean_companies.contacts_count` | 联系人数 |
| `business_status` | `tenant_companies.business_status` | 租户私有推进状态 |
| `data_status` | `tenant_companies.data_status` | 租户视角数据状态 |
| `score_min/max` | `tenant_companies.score` | 当前评分值 |

## 4. Field Source Rules

| 响应字段类别 | 来源 |
|---|---|
| 公司基础字段 | `clean_companies` |
| 数据来源 | `clean_company_sources` |
| 命中关键词 | `clean_company_keywords` join `tenant_keyword` |
| 租户私有状态 | `tenant_companies` |
| 联系人基础字段 | `clean_contacts` |
| 租户联系人状态 | `tenant_contacts` |
| raw 详情追溯 | raw provider tables；默认响应不含 `raw_payload` |

## 5. Non-Goals

- 不在本 contract 实现采集 worker。
- 不在本 contract 实现 raw→clean 清洗。
- 不在本 contract 实现 AI enrichment。
- 不在本 contract 实现群组、邮件计划、调分历史。
