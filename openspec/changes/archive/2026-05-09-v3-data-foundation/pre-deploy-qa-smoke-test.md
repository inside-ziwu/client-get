# Pre-Deploy QA Checklist / Smoke Test · v3-data-foundation

> 日期：2026-05-09  
> 范围：仅 `v3-data-foundation` 上线前 QA。验证 schema、migration、关键词归一、admin/tenant API contract、前端 shared-api 对齐。  
> 不验证：cleanup_service、worker 执行、Sealos 编排、AI enrichment、邮件投递、评分、群组、完整采集闭环。

## 0. Go / No-Go 结论规则

| 结果 | 判定 |
|---|---|
| 所有 P0 通过，P1 无阻塞 | 可以进入部署窗口 |
| 任一 P0 失败 | 不允许部署 |
| P1 失败但有明确规避方案 | 可由负责人签字后部署 |
| P2 失败 | 记录为上线后观察项，不阻塞 |

## 1. P0 · 自动化验证

| # | 检查项 | 命令 | 期望 |
|---|---|---|---|
| P0-1 | Alembic 当前版本 | `uv run alembic current` | `20260508_0034 (head)` |
| P0-2 | 后端 schema/API/关键词测试 | `uv run pytest tests/test_v3_data_foundation_schema.py tests/test_v3_data_foundation_api_contract.py tests/test_keyword_service.py -v` | 全部通过 |
| P0-3 | 前端类型检查 | `pnpm -r type-check` | admin / tenant / shared packages 全部通过 |
| P0-4 | OpenSpec strict validate | `openspec validate v3-data-foundation --strict` | `Change 'v3-data-foundation' is valid` |
| P0-5 | OpenSpec task 状态 | `openspec instructions apply --change v3-data-foundation --json` | `29/30` 或 `30/30`；若 `29/30`，仅剩 `T-DF-92` 用户签字 |

记录：

| 检查项 | 结果 | 证据 / 备注 |
|---|---|---|
| P0-1 |  |  |
| P0-2 |  |  |
| P0-3 |  |  |
| P0-4 |  |  |
| P0-5 |  |  |

## 2. P0 · 数据库结构 Smoke

在目标业务库执行，只看结构和关键约束，不要求业务表为空。

```sql
SELECT version_num FROM alembic_version;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name IN (
    'keyword_master',
    'tenant_keyword',
    'lixiaoyun_raw_companies',
    'lixiaoyun_raw_contacts',
    'tendata_raw_companies',
    'tendata_raw_contacts',
    'clean_companies',
    'clean_contacts',
    'clean_company_sources',
    'clean_company_keywords',
    'tenant_companies',
    'tenant_contacts',
    'collection_runs',
    'collection_tasks'
  )
ORDER BY table_name;
```

必须确认：

| 检查项 | 期望 |
|---|---|
| 12 张 data foundation 表存在 | 全部存在 |
| `tenant_keyword.id` | bigint / identity |
| `tenant_keyword` | 含 `keyword_raw`, `created_by`, `status` |
| raw company 表 | 不含 `task_id`, `keyword_normalized`, `last_seen_at` |
| `clean_companies` | 不含 `data_completeness`, `sources` |
| `tenant_companies` | 不含 `score_adjustment*`, `matched_keywords` |
| `tenant_contacts` | 不含 `tenant_company_id` |
| `collection_runs` | 含 `provider`, `stage`, `triggered_tenant_id` |
| `collection_tasks` | 含 `run_id`, `scheduled_biz_date`, `batch_no`, `page_size`, `cursor_snapshot` |

## 3. P0 · API Smoke

> 以下用真实 token / 域名执行；文档不记录 token 和 secret。

### 3.1 Admin API

| # | 路径 | 检查点 | 期望 |
|---|---|---|---|
| A-1 | `GET /admin/api/v1/raw/tendata/companies?page_size=5` | raw tendata 列表 | 200；返回数组；默认不含 `raw_payload` |
| A-2 | `GET /admin/api/v1/raw/lixiaoyun/companies?page_size=5` | raw lixiaoyun 列表 | 200；返回数组；默认不含 `raw_payload` |
| A-3 | `GET /admin/api/v1/clean/companies?source_type=tendata&page_size=5` | clean 列表 source filter | 200；过滤走 `clean_company_sources.source_type` |
| A-4 | `GET /admin/api/v1/collection-keywords` | 旧兼容关键词页 | 200；不阻塞现有 admin 页面 |

### 3.2 Tenant API

| # | 路径 | 检查点 | 期望 |
|---|---|---|---|
| T-1 | `GET /t/{tenant_slug}/api/v1/keywords` | 租户关键词列表 | 200；字段含 `keyword_raw`, `keyword_master_id`, `status` |
| T-2 | `POST /t/{tenant_slug}/api/v1/keywords` | 新增 / 恢复关键词 | 200；同归一关键词不重复创建平台关键词 |
| T-3 | `DELETE /t/{tenant_slug}/api/v1/keywords/{id}` | 软删除关键词 | 200 / 204；`tenant_keyword.status = deleted` |
| T-4 | `GET /t/{tenant_slug}/api/v1/companies` | 客户列表 | 200；可见性通过 `clean_company_keywords + tenant_keyword` |
| T-5 | `GET /t/{tenant_slug}/api/v1/companies/{id}` | 客户详情 | `{id}` 是 `clean_companies.id`；返回 `sources`, `matched_keywords`, `tenant_state` |
| T-6 | `GET /t/{tenant_slug}/api/v1/companies/{id}/contacts` | 联系人列表 | 公司可见则联系人可见；返回 `tenant_contact_state` |
| T-7 | `GET /t/{tenant_slug}/api/v1/companies/not-a-number` | 非法 id | 404，不应 500 |

### 3.3 Tenant 10 项筛选

对 `GET /t/{tenant_slug}/api/v1/companies` 逐项或组合验证：

| 筛选项 | 参数 | 字段来源 | 期望 |
|---|---|---|---|
| 国家 | `country_iso3` | `clean_companies.country_iso3` | 200，结果国家匹配 |
| 行业细分 | `industry_tags` | `clean_companies.industry_tags` | 200，多值 OR |
| 成立时间 | `incorporation_date_from/to` | `clean_companies.incorporation_date` | 200，日期区间有效 |
| 注册资金 | `reg_capital_min/max` | `clean_companies.reg_capital` | 200，数值区间有效 |
| 产品标签 | `product_tags[]` | `clean_companies.product_tags` | 200，多值 OR |
| 公司规模 | `employee_num` | `clean_companies.employee_num` | 200，按来源文本匹配 |
| 数据来源 | `source_type` | `clean_company_sources.source_type` | 200，V3 仅 `tendata` |
| 进出口金额 | `trade_amount_min/max` | `clean_companies.trade_amount_3y_usd` | 200，数值区间有效 |
| 进出口次数 | `trade_count_min/max` | `clean_companies.trade_count` | 200，数值区间有效 |
| 联系人数 | `contacts_count_min/max` | `clean_companies.contacts_count` | 200，数值区间有效 |

## 4. P1 · 前端 Smoke

### 4.1 Admin 前端

| 页面 | 路径 / 菜单 | 检查点 | 期望 |
|---|---|---|---|
| 采集关键词 / Dashboard | admin 采集相关页面 | 页面可打开 | 无白屏；接口 200 或空态正常 |
| Raw 数据 | tendata / lixiaoyun raw 列表 | 表格渲染 | 不依赖 `raw_payload` 必返 |
| Clean 客户 | clean companies 列表 | source filter | `source_type=tendata` 可筛 |
| 旧兼容页面 | CollectionArchive / PeersData | 页面可打开 | 旧路径未被本次改动打挂 |

### 4.2 Tenant 前端

| 页面 | 路径 / 菜单 | 检查点 | 期望 |
|---|---|---|---|
| 关键词设置 | tenant keywords | 列表 / 新增 / 删除 | 字段展示合理；删除为软删 |
| 公司列表 | tenant companies | 列表加载 | 无白屏；分页正常 |
| 公司筛选 | tenant companies filters | 10 项筛选 | 至少每类参数触发后不报错 |
| 公司详情 | drawer / detail | clean company detail | 展示基础字段、来源、命中关键词、租户状态 |
| 联系人 | company contacts | 联系人列表 | 展示姓名、职位、邮箱、状态 |

## 5. P1 · 部署环境 Smoke

| 检查项 | 期望 |
|---|---|
| 后端健康检查 | `/health` 200 |
| admin 前端健康检查 | `/healthz` 200 |
| tenant 前端健康检查 | `/healthz` 200 |
| 后端启动日志 | 无 migration / import / settings fatal error |
| API 访问日志 | smoke 请求无 500 |
| 数据库连接 | backend pod 能连接业务库 `clientget` |
| Alembic head | 线上执行后仍为 `20260508_0034 (head)` |

## 6. P2 · 可接受风险 / 非本次阻塞

| 项 | 说明 |
|---|---|
| cleanup_service raw → clean | 不在 `v3-data-foundation` 范围；本次不要求完整清洗闭环 |
| worker 调度 / 执行 | 不在本 change 范围；不以采集任务真实执行作为阻塞 |
| AI enrichment | 不在本 change 范围 |
| 邮件投递 | 不在本 change 范围 |
| 群组 / 邮件计划 / 调分历史 | 不在本 change 范围 |
| 完整 V3 E2E | 仍受 `_control/v3/04-v3-e2e-test-plan.md` Gate 7 约束；不能因本 smoke 通过就声明“V3 完成” |

## 7. 部署前人工确认

| 确认项 | 负责人 | 结果 |
|---|---|---|
| 已有数据库备份 |  |  |
| 目标库确认是 `clientget` |  |  |
| migration 已在目标库 dry-run / staging 验证 |  |  |
| 本次上线范围已告知：data foundation only |  |  |
| 回滚负责人已确认 |  |  |
| T-DF-92 是否签字 |  |  |

签字：

```text
QA smoke accepted for v3-data-foundation
签字人：
日期：
```

