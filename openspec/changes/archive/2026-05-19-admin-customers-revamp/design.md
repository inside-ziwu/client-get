## Context

Admin 端 `/collection/customers` 页面当前查询 `clean_companies` 表（多源归一数据），仅展示 7 列基础字段。线上数据库已存在 `waimaotong_clean_companies`（70 列，含 AI 分析字段预留）和 `waimaotong_clean_contacts`（6335 条），需要将页面数据源切换到这两张表，并复刻外部仓库 sysdev-ft-marketing 的交互模式。

现有代码中已有类似模式可参照：
- 后端：`admin_collection_service.py` 中 `list_v3_raw_companies(provider="waimaotong")` 方法（查 `waimaotong_raw_companies`）
- 前端：`/collection/waimaotong/client-page.tsx`（外贸通原始数据页面）
- shared-api：`listWaimaotongRawCompanies` / `getWaimaotongRawCompanyDebug` / `listWaimaotongRawCompanyContacts`

## Goals / Non-Goals

**Goals:**
- Admin 端可查看 `waimaotong_clean_companies` 全量字段（基础 + AI 预留）
- 多维筛选能力对齐外部仓库（公司名/域名、国家、行业、员工规模、成立年份、有联系人）
- 详情 Sheet 分组展示 + 联系人表格
- AI 字段为空时优雅降级（不显示空分组）

**Non-Goals:**
- 不修改 `clean_companies` 相关 API
- 不新增 Alembic 迁移
- 不运行 AI Flow 填充数据

## Decisions

### D1: 后端新增独立方法，不复用 V3 provider 路由

**选择**：在 `admin_collection_service.py` 中新增 3 个独立方法（`list_wmt_clean_companies` / `get_wmt_clean_company` / `list_wmt_clean_company_contacts`），路由挂在 `/collection/wmt-clean-companies` 下。

**备选**：复用现有 `list_v3_raw_companies(provider=...)` 的 provider 分发模式。

**理由**：`waimaotong_clean_companies` 和 `waimaotong_raw_companies` 是两张不同的表，字段集差异极大（70 列 vs 33 列），强行塞进 provider 分发会让代码更复杂。独立方法更清晰，也更容易后续扩展 AI 字段筛选。

### D2: 联系人通过 sys_company_id 关联，不通过 id

**选择**：`waimaotong_clean_contacts` 通过 `sys_company_id` 关联 `waimaotong_clean_companies.sys_company_id`。

**理由**：线上数据就是这样关联的（已验证），`waimaotong_clean_contacts` 没有直接 FK 到 `waimaotong_clean_companies.id`。

### D3: 前端改造现有页面，不新建路由

**选择**：直接改造 `/collection/customers/client-page.tsx`，侧边栏路由不变。

**理由**：路由 `/collection/customers` 语义匹配（"客户数据"），避免新增菜单项增加导航复杂度。

### D4: AI 字段按分组条件显示

**选择**：详情 Sheet 中 AI 评估分组、贸易数据分组仅在对应字段有值时显示；表格中 AI 列当值为 null 时显示 `-`。

**理由**：当前 AI 字段全空，强制显示空分组会造成困惑。等 Flow 02 跑完自动有数据。

### D5: 列表 SELECT 分两档——基础列 + AI 列全部返回

**选择**：SQL SELECT 一次性返回所有可展示字段（基础 + AI），前端根据值是否为 null 决定是否渲染。

**备选**：只 SELECT 有数据的列，AI 字段后续再加。

**理由**：SQL 层面 SELECT NULL 列几乎无开销，一次到位避免后续重复改 API。前端类型定义中 AI 字段标记为 `| null`。

## 后端 API 设计

### `GET /collection/wmt-clean-companies`

查询参数：

| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，默认 1 |
| page_size | int | 每页条数，默认 20，最大 100 |
| q | str? | 公司名/域名模糊搜索 |
| country | str? | 国家精确匹配（country 字段） |
| industry | str? | 行业模糊搜索 |
| size | str? | 员工规模档位（tiny/small/medium/large） |
| year_min | int? | 成立年份最小值 |
| year_max | int? | 成立年份最大值 |
| has_contacts | bool? | 是否有联系人 |
| grade | str? | 评级筛选（A/B/C/X）—— AI 字段预留 |

SELECT 字段（列表查询）：

```sql
SELECT id, source_id, name, company_name, english_name,
       country, country_iso3, domain, industry, sub_industry,
       phone, employee_size, company_size, founded_year,
       website, full_address, description,
       grade, score, email_priority, company_type_analysis,
       product_tags, data_source_tags,
       has_trade_data, trade_amount_3y_usd, trade_count,
       contacts_count,
       detail_status, contacts_status, trade_status,
       sys_company_id,
       created_at, updated_at
FROM waimaotong_clean_companies
```

### `GET /collection/wmt-clean-companies/{id}`

返回完整字段（含 AI 分析字段：score_details, match_reasons, potential_needs, recommended_products, risk_factors, main_business, trade_summary 等 JSONB 字段）。

### `GET /collection/wmt-clean-companies/{id}/contacts`

```sql
SELECT id, name, position, department, email, email_status,
       phone, mobile, linkedin, whatsapp, source, confidence,
       created_at
FROM waimaotong_clean_contacts
WHERE sys_company_id = (
  SELECT sys_company_id FROM waimaotong_clean_companies WHERE id = :id
)
ORDER BY created_at ASC
```

## 前端表格列设计

| # | 列名 | 字段 | 宽度 | 说明 |
|---|------|------|------|------|
| 1 | 公司名 | company_name | 180 | 可点击打开详情 Sheet |
| 2 | 国家 | country | 100 | |
| 3 | 域名 | domain | 150 | |
| 4 | 行业 | industry | 140 | |
| 5 | 员工规模 | employee_size | 100 | |
| 6 | 成立 | founded_year | 80 | |
| 7 | 电话 | phone | 130 | |
| 8 | 评级 | grade | 70 | Badge 颜色：A=green B=blue C=orange X=red，null 时显示 `-` |
| 9 | 评分 | score | 80 | 数字，null 时显示 `-` |
| 10 | 细分行业 | sub_industry | 120 | AI 字段，null 时显示 `-` |
| 11 | 联系人数 | contacts_count | 80 | |
| 12 | 详情状态 | detail_status | 90 | Badge |
| 13 | 入库时间 | created_at | 150 | |

## 前端详情 Sheet 分组

**分组 1：基本信息**（始终显示）
company_name, english_name, country, domain, website, industry, phone, employee_size, company_size, founded_year, full_address, description

**分组 2：AI 评估**（仅当 grade 或 score 有值时显示）
grade, score, score_details（多维度进度条）, sub_industry, company_type_analysis, product_tags, match_reasons, potential_needs, recommended_products, risk_factors, main_business, sales_approach, email_priority

**分组 3：贸易数据**（仅当 has_trade_data 为 true 或 trade_summary 有值时显示）
has_trade_data, trade_amount_3y_usd, trade_count, trade_summary

**分组 4：联系人**（始终显示，通过独立 API 获取）
表格：name | position | department | email | email_status | phone | linkedin | source

**分组 5：数据来源与元数据**（始终显示）
data_source_tags, source_id, sys_company_id, detail_status, contacts_status, trade_status, created_at, updated_at

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| `waimaotong_clean_companies` 表不在 Alembic 管理中 | 本 change 不改表结构；后续单独 change 补迁移文件 |
| AI 字段当前全空，页面看起来可能信息稀疏 | 条件显示分组 + 基础字段已有足够数据（name/country/domain/industry/phone 等填充率 > 90%） |
| 联系人通过 sys_company_id 关联，无 FK 约束 | 查询时 subquery 确保 company 存在，不存在返回空列表 |
| 旧的 `/collection/clean-companies` API 仍在使用 | 保留不动，新旧并存 |
