## Context

外贸通数据源的线上表结构（`waimaotong_raw_companies` 33 列、`waimaotong_raw_contacts` 21 列）与 Alembic 迁移严重不同步——18+5 个列是线上直接添加的，迁移文件中不存在。Admin 端需要新增外贸通数据展示页面，同时移除废弃的腾道页面。

## Goals / Non-Goals

**Goals:**
- Admin 端可查看外贸通公司列表、筛选、查看详情和联系人
- 后端 SQL 映射线上真实 33+21 列
- Alembic 迁移与线上同步

**Non-Goals:**
- 不重写采集管道
- 不删除 tendata 表
- 不展示原始采集数据（detail_raw_data / raw_data）

## Decisions

### D1: 复用 V3 API 架构，不新建端点

**选择**：复用现有 `GET /api/v1/raw/{provider}/companies` 端点体系，重写 waimaotong 分支的 SQL。

**理由**：端点路径、分页、权限校验已就绪。只需修改 service 层 SQL 和新增筛选参数。

### D2: 前端参照 tendata 页面结构，替换字段

**选择**：新建 `/collection/waimaotong/` 页面，结构参考 tendata 页面（列表 + 筛选 + Sheet 详情），替换为外贸通字段。

**理由**：交互模式一致，降低开发和使用认知成本。

### D3: 国家字段使用 text 而非 ISO3

**选择**：筛选和展示使用 `country`（text，英文全称如 "China"、"Hong Kong"），不再使用 `country_iso3`。

**理由**：线上新增的 `country` 字段是 text 类型英文全称（100% 填充），旧的 `country_iso3` 已被迁移 0043 删除。

### D4: 联系人表格隐藏空字段，保留 department

**选择**：隐藏 `mobile`、`whatsapp`（0% 填充）；保留 `department`（0% 填充但预期未来有数据）。

### D5: 迁移策略——只加列，不改数据

**选择**：新建 Alembic revision，使用 `ADD COLUMN IF NOT EXISTS` 补齐 18+5 列。upgrade 是幂等的（线上已有这些列，跑迁移不会报错）。

**理由**：让迁移文件追平线上状态，不修改数据、不删列、不重建表。

## 线上真实表结构

### waimaotong_raw_companies（33 列）

原有 15 列：`id`, `real_id`, `name`, `domain`, `industry`, `phone`, `employee_size`, `founded_year`, `description`, `products`, `source_tags`, `contacts_count`, `detail_status`, `created_at`, `updated_at`

线上新增 18 列：

| 字段 | 类型 | 说明 | 填充率 |
|------|------|------|--------|
| company_id | text | 公司标识（常为域名） | - |
| sys_company_id | uuid | 系统内部 UUID | - |
| api_company_id | text | 外贸通 API ID | - |
| company_name | text | 公司名（统一使用此字段展示） | - |
| country | text | 国家英文全称 | 100% |
| source_type | text | 来源类型（目前仅 buyer） | - |
| source_keyword | text | 采集关键词 | - |
| source_competitor | text | 来源同行公司名 | - |
| id_verified | boolean | 是否已验证 | 100% |
| plan_id | int | 采集计划 ID | 0% |
| full_address | text | 注册地址 | 0% |
| website | text | 网站完整 URL | 36% |
| has_detail | boolean | 是否已获取详情 | - |
| has_contacts | boolean | 是否已获取联系人 | - |
| email_count | int | 邮箱数量 | - |
| detail_raw_data | text | 详情页原始 JSON 文本 | 84% |
| raw_data | text | 搜索结果原始 JSON 文本 | 100% |
| error_msg | text | 错误信息 | - |

### waimaotong_raw_contacts（21 列）

原有 16 列 + 线上新增 5 列：`sys_contact_id`(uuid), `contact_id`(text), `sys_company_id`(uuid), `api_company_id`(text), `company_id`(text)

## 后端 API 设计

### 列表查询：`list_v3_raw_companies(provider="waimaotong")`

重写 SELECT：

```sql
SELECT c.id, c.company_name, c.country, c.domain, c.industry,
       c.employee_size, c.founded_year, c.full_address,
       c.source_keyword, c.source_competitor, c.source_type,
       c.contacts_count, c.email_count,
       c.has_detail, c.has_contacts, c.id_verified,
       c.website, c.api_company_id,
       c.created_at
FROM waimaotong_raw_companies c
ORDER BY c.created_at DESC, c.id DESC
LIMIT :limit OFFSET :offset
```

新增 WHERE 筛选（waimaotong 专属分支）：

| 参数 | SQL 条件 |
|------|---------|
| q | `c.company_name ILIKE :q OR c.domain ILIKE :q` |
| country | `c.country = :country` |
| source_keyword | `c.source_keyword = :source_keyword` |
| source_competitor | `c.source_competitor ILIKE :source_competitor` |
| year_min / year_max | `c.founded_year >= :year_min` / `<= :year_max` |
| employee_size | 从 text 中提取数字做区间比较（复用现有 `NULLIF(substring(...))::int` 模式） |
| industry | `c.industry ILIKE :industry` |
| has_contacts | `c.has_contacts = true` |

### 联系人查询：`list_v3_raw_company_contacts(provider="waimaotong")`

新增 SQL（当前 sql_by_provider 中缺失 waimaotong）：

```sql
SELECT id, raw_company_id, source_contact_id, name, position,
       department, email, email_status, phone,
       linkedin, source, confidence, created_at
FROM waimaotong_raw_contacts
WHERE raw_company_id = :raw_company_id
ORDER BY created_at ASC, id ASC
```

注意：不查 `mobile`、`whatsapp`（不展示）。

### Debug 查询：`get_v3_raw_company_debug(provider="waimaotong")`

返回公司全部可展示字段（排除 detail_raw_data / raw_data）：

```sql
SELECT id, company_name, country, domain, industry, phone,
       employee_size, founded_year, description, full_address,
       website, products, source_tags,
       source_keyword, source_competitor, source_type,
       id_verified, api_company_id,
       contacts_count, email_count,
       has_detail, has_contacts,
       created_at, updated_at
FROM waimaotong_raw_companies
WHERE id = :id
```

### API 路由层修改

`backend/app/api/admin/collection.py` 的 V3 端点需新增查询参数：
- `source_keyword: str | None = Query(None)`
- `source_competitor: str | None = Query(None)`
- `has_contacts: bool | None = Query(None)`

这些参数透传给 service 层。

## 前端设计

### 页面结构

```
/collection/waimaotong
├── page.tsx          # SSR 预加载
└── client-page.tsx   # WaimaotongArchivePage 组件
```

### 列表页 11 列

| 列名 | 字段 | 说明 |
|------|------|------|
| 公司名 | company_name | |
| 国家 | country | |
| 域名 | domain | 纯域名显示 |
| 行业 | industry | |
| 员工规模 | employee_size | |
| 成立日期 | founded_year | 仅年份 |
| 注册地址 | full_address | 当前 0%，保留 |
| 采集关键词 | source_keyword | |
| 来源同行 | source_competitor | |
| 联系人数 | contacts_count | |
| 入库时间 | created_at | |

### 筛选项 8 个

| 筛选项 | 类型 | 说明 |
|--------|------|------|
| 公司名 | 文本输入 | ILIKE 模糊搜索 |
| 国家 | 下拉选择 | 27 个值 |
| 采集关键词 | 下拉选择 | 电路/线路 |
| 来源同行 | 文本输入 | ILIKE 模糊搜索 |
| 成立日期 | 年份范围 | min/max 两个输入 |
| 员工规模 | 区间选择 | tiny/small/medium/large |
| 行业 | 文本输入 | ILIKE 模糊搜索 |
| 有联系人？ | 布尔开关 | has_contacts = true |

### 详情 Sheet

**基本信息区：**
company_name, country, website（可点击链接）, industry, phone, employee_size, founded_year, description, full_address, products（tag 列表）

**采集信息区：**
source_keyword, source_competitor, source_type, id_verified, api_company_id

**联系人表格：**
name | position | department | email | email_status | phone | linkedin | source

### 侧边栏

将"腾道"替换为"外贸通"，路由指向 `/collection/waimaotong`。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 迁移与线上不同步导致后续迁移出错 | 使用 `ADD COLUMN IF NOT EXISTS`，幂等操作 |
| tendata 共享代码分支改错影响 lixiaoyun | 只改 waimaotong 分支和 tendata 共享分支，lixiaoyun 独立分支不动 |
| employee_size 格式不统一（"10"/"1-20"/"50人"/"Over 400"） | 复用现有正则提取数字模式，接受有损匹配 |
