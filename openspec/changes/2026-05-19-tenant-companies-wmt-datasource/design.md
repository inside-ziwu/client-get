## 概述

将 tenant 端所有公司/联系人查询和写入从 `clean_companies` / `clean_contacts` 切换到 `waimaotong_clean_companies` / `waimaotong_clean_contacts`。桥接表 `tenant_companies` / `tenant_contacts` 保留，FK 指向改变。

## 1. 核心 JOIN 模式变更

所有 tenant 端查询共享同一个基本 JOIN 结构，变更统一：

```
-- 旧
FROM clean_companies cc
JOIN tenant_companies tc ON tc.clean_company_id = cc.id AND tc.tenant_id = :tenant_id

-- 新
FROM waimaotong_clean_companies wc
JOIN tenant_companies tc ON tc.clean_company_id = wc.id AND tc.tenant_id = :tenant_id
```

别名从 `cc` 改为 `wc`，后续所有字段引用跟随。影响函数：
- `companies_page()` — tenant_query_service.py:139
- `v3_company_detail()` — tenant_query_service.py:413
- `prospects()` — tenant_query_service.py:604
- `companies_filters()` — tenant_ops_service.py:40
- `export_companies()` — tenant_ops_service.py:63
- `get_company()` — tenant_ops_service.py:194

## 2. SELECT 列映射

每个查询的 SELECT 列需逐一替换。以 `companies_page()` 为例：

```
旧 SELECT                    新 SELECT                       说明
─────────────────────────    ─────────────────────────       ──────
cc.id                    →   wc.id                           ✓
cc.name                  →   wc.company_name                 列名变化
cc.name_normalized       →   (移除)                          wmt 无此列
cc.country_iso3          →   wc.country_iso3                 ✓
cc.website               →   wc.website                      ✓
cc.industry_desc         →   wc.industry                     列名变化
cc.industry_tags         →   (移除)                          wmt 无 text[]，用 wc.sub_industry 替代
cc.employee_num          →   wc.employee_size                列名变化
cc.contacts_count        →   wc.contacts_count               ✓
cc.product_tags          →   wc.product_tags                 ✓
(无)                     →   wc.grade                        新增
(无)                     →   wc.score AS wmt_score           新增（注意与 tc.score 区分）
(无)                     →   wc.domain                       新增
(无)                     →   wc.english_name                 新增
```

**硬约束（Review D5）**：API 响应的 key 不得变化。后端查询中使用 `wc.company_name`，但返回字典 key 必须保持 `"name"` 不变，使用 SQL 别名 `wc.company_name AS name` 或 Python 层映射。同理 `industry`、`employee_size` 等列名变化均在后端映射，前端不感知列名差异。

## 3. WHERE 过滤器适配

### 3.1 直接列名替换

| 旧过滤器 | 新过滤器 | 说明 |
|---------|---------|------|
| `cc.name ILIKE` | `wc.company_name ILIKE` | 关键词搜索 |
| `cc.website ILIKE` | `(wc.website ILIKE ... OR wc.domain ILIKE ...)` | 域名搜索，wmt 有两列 |
| `cc.country_iso3` | `wc.country_iso3` | ✓ |
| `cc.product_tags &&` | `wc.product_tags &&` | ✓ |
| `cc.trade_amount_3y_usd` | `wc.trade_amount_3y_usd` | ✓ |
| `cc.trade_count` | `wc.trade_count` | ✓ |
| `cc.contacts_count` | `wc.contacts_count` | ✓ |

### 3.2 语义变化的过滤器

| 旧过滤器 | 新过滤器 | 说明 |
|---------|---------|------|
| `cc.industry_desc = ANY(:sub_industries) OR cc.industry_tags && :sub_industries` | `wc.industry = ANY(:sub_industries) OR wc.sub_industry = ANY(:sub_industries)` | 双列精确匹配，保持与旧代码相同的双列语义（Review D6 + Outside Voice D13） |
| `cc.employee_num = :employee_num` | `wc.employee_size = :employee_scale` | 列名变化 |
| `cc.employee_num IN (...)` (规模档位) | `wc.employee_size IN (...)` | 档位值需确认兼容性 |
| `EXTRACT(YEAR FROM cc.incorporation_date)` | `wc.founded_year` | date → int，直接比较 |
| `cc.reg_capital >= :min` | (移除) | wmt 无此列 |
| `cc.pcb_suppliers` | (移除) | wmt 无此列 |

### 3.3 来源过滤器重写

```sql
-- 旧：通过 clean_company_sources 子查询
EXISTS (
  SELECT 1 FROM clean_company_sources ccs_filter
  WHERE ccs_filter.clean_company_id = cc.id
    AND ccs_filter.source_type = ANY(:sources)
)

-- 新：通过 wmt 表的 data_source_tags 列（text[]）
wc.data_source_tags && :sources
```

### 3.4 游标分页

```sql
-- 旧：用 clean_companies.id 做游标
cc.id < :cursor

-- 新：用 wmt 表 id 做游标（同为 bigint，语义一致）
wc.id < :cursor
```

## 4. 联系人查询模式变更

### 4.1 v3_company_contacts()（tenant_query_service.py:499）

```sql
-- 旧：直接 FK
FROM clean_contacts cc
WHERE cc.clean_company_id = :clean_company_id

-- 新：通过 sys_company_id 间接关联
FROM waimaotong_clean_contacts wcc
WHERE wcc.sys_company_id = (
    SELECT sys_company_id FROM waimaotong_clean_companies WHERE id = :company_id
)
```

这与 admin 端 `list_wmt_clean_company_contacts()` 使用完全相同的模式。

联系人列映射：

```
旧 (clean_contacts)          新 (waimaotong_clean_contacts)
──────────────────           ──────────────────────────────
id                       →   id
name                     →   name
email                    →   email
phone                    →   phone / mobile
position                 →   position / department
(无)                     →   email_status
(无)                     →   linkedin / whatsapp
(无)                     →   confidence
```

### 4.2 company_contacts()（tenant_ops_service.py:295）

同样改用 sys_company_id 模式。tenant_contacts 桥接表的 `clean_contact_id` 改为指向 `waimaotong_clean_contacts.id`，`clean_company_id` 改为指向 `waimaotong_clean_companies.id`。

## 5. 写操作重写

### 5.1 create_company()（tenant_ops_service.py:91）

```sql
-- 旧：写入 clean_companies，用 normalize_company_name() 去重
INSERT INTO clean_companies
  (name_normalized, name, country_iso3, website, industry_desc, product_tags, industry_tags)
VALUES
  (normalize_company_name(:name), :name, :country_iso3, :website, :industry, ...)
ON CONFLICT (name_normalized, country_iso3) DO UPDATE ...

-- 新：写入 wmt 表，domain 优先去重 + advisory lock 防并发（Review D2）
-- 步骤 0：获取 advisory lock，防止并发创建同一公司
SELECT pg_advisory_xact_lock(hashtext(:domain || :company_name || :country_iso3));

-- 步骤 1：先查是否已存在（domain 优先，回退 company_name + country_iso3）
SELECT id FROM waimaotong_clean_companies
WHERE domain = :domain AND domain IS NOT NULL AND domain != ''
LIMIT 1;

-- 若未命中 domain，回退：
SELECT id FROM waimaotong_clean_companies
WHERE company_name = :company_name AND country_iso3 = :country_iso3
LIMIT 1;

-- 步骤 2：不存在则 INSERT（无 ON CONFLICT，改用应用层查重）
INSERT INTO waimaotong_clean_companies
  (company_name, english_name, country_iso3, domain, website, industry, product_tags)
VALUES
  (:company_name, :english_name, :country_iso3, :domain, :website, :industry, :product_tags)
RETURNING id;
```

去重从数据库约束（UNIQUE + ON CONFLICT）变为应用层 SELECT-then-INSERT + `pg_advisory_xact_lock` 防并发（Review D2）。原因：wmt 表外部导入，不宜加 `(company_name, country_iso3)` UNIQUE 约束（可能与导入流程冲突）。D7 允许加索引但不加破坏性约束。

### 5.2 _ensure_contact_from_payload()（tenant_ops_service.py:924）

```sql
-- 旧：写入 clean_contacts
INSERT INTO clean_contacts (clean_company_id, name, email, position)
VALUES (:clean_company_id, :name, :email, :position)
ON CONFLICT (clean_company_id, email) WHERE email IS NOT NULL DO UPDATE ...

-- 新：写入 waimaotong_clean_contacts
-- 步骤 1：获取 sys_company_id
SELECT sys_company_id FROM waimaotong_clean_companies WHERE id = :wmt_company_id;

-- 步骤 2：查重 + 写入
INSERT INTO waimaotong_clean_contacts (sys_company_id, name, email, position)
VALUES (:sys_company_id, :name, :email, :position)
ON CONFLICT ... -- 需确认 wmt_clean_contacts 的唯一约束情况
```

### 5.3 blacklist_company()（tenant_ops_service.py:254）

`shared_company_id` 从 `company["clean_company_id"]` 改为 `company["wmt_company_id"]`（即 waimaotong_clean_companies.id）。语义不变，只是指向的表发生变化。

## 6. 详情页数据源替换

### 6.1 _company_sources() → data_source_tags

```python
# 旧：从 clean_company_sources 表查来源列表
sources = await self._company_sources(conn, company_id)
# 返回 [{"source_type": "...", "source_company_id": "...", ...}, ...]

# 新：直接从 wmt 表的 data_source_tags 列读取
# data_source_tags 是 text[]，直接在主查询中 SELECT，不需要额外函数
# 返回格式简化为 ["source_a", "source_b", ...]
```

### 6.2 _matched_tenant_keywords() → 移除

暂时移除（D8）。`v3_company_detail()` 返回值中 `matched_keywords` 设为空列表 `[]`，前端做兼容处理（已有的展示组件在列表为空时不渲染）。

## 7. messaging_service 适配

`tenant_messaging_service.py` 有 12 处 `clean_companies`/`clean_contacts` 引用，集中在邮件发送相关查询中。模式统一为：

```sql
-- 旧
JOIN clean_companies cc ON cc.id = tc.clean_company_id
LEFT JOIN clean_contacts shc ON shc.id = tco.clean_contact_id

-- 新
JOIN waimaotong_clean_companies wc ON wc.id = tc.clean_company_id
LEFT JOIN waimaotong_clean_contacts wcc ON wcc.id = tco.clean_contact_id
```

字段引用 `cc.name` → `wc.company_name`，`shc.email` → `wcc.email` 等，逐一对应。

## 8. Migration 设计

### 8.1 tenant_companies FK 变更

```sql
-- 1. 删除旧 FK
ALTER TABLE tenant_companies DROP CONSTRAINT IF EXISTS tenant_companies_clean_company_id_fkey;

-- 2. 重建关联（D6）：基于 name + country 匹配
UPDATE tenant_companies tc
SET clean_company_id = wc.id
FROM clean_companies cc
JOIN waimaotong_clean_companies wc
  ON wc.company_name = cc.name AND wc.country_iso3 = cc.country_iso3
WHERE tc.clean_company_id = cc.id;

-- 3. 直接删除未匹配的记录（Review D3：不做安全网，直接 DELETE）
DELETE FROM tenant_companies WHERE clean_company_id NOT IN (
  SELECT id FROM waimaotong_clean_companies
);

-- 4. 添加新 FK（如需要）
-- 注意：wmt 表外部导入，FK 约束可能阻碍导入流程，考虑只加索引不加 FK
CREATE INDEX IF NOT EXISTS idx_tenant_companies_clean_company_id
  ON tenant_companies (clean_company_id);
```

### 8.2 tenant_contacts 处理

清空 tenant_contacts 全表（Review D4）。原因：tenant_contacts 数据量小、无不可恢复的业务状态（仅 contact_status/is_sendable），逐条匹配 wmt 联系人成本高且匹配率不确定。用户重新添加联系人后自然重建。

```sql
DELETE FROM tenant_contacts;
```

### 8.3 wmt 表索引补建（D4 + D7）

```sql
-- sys_company_id 索引（联系人关联查询必需）
CREATE INDEX IF NOT EXISTS idx_wmt_clean_contacts_sys_company_id
  ON waimaotong_clean_contacts (sys_company_id);

-- domain 索引（去重查询优化）
CREATE INDEX IF NOT EXISTS idx_wmt_clean_companies_domain
  ON waimaotong_clean_companies (domain)
  WHERE domain IS NOT NULL AND domain != '';

-- company_name + country_iso3 索引（去重回退查询优化）
CREATE INDEX IF NOT EXISTS idx_wmt_clean_companies_name_country
  ON waimaotong_clean_companies (company_name, country_iso3);
```

### 8.4 blacklist 关联重建

```sql
UPDATE company_blacklist bl
SET shared_company_id = wc.id
FROM clean_companies cc
JOIN waimaotong_clean_companies wc
  ON wc.company_name = cc.name AND wc.country_iso3 = cc.country_iso3
WHERE bl.shared_company_id = cc.id;
```

## 9. 前端适配

### 9.1 Company 类型（shared-api/src/tenant/companies.ts）

后端返回字段变化后，前端类型已有的字段基本覆盖（`grade`、`total_score`、`domain` 等已定义）。主要变化：

- `name` 后端返回 key 从 `name` 改为 `company_name`，或后端做映射保持 `name` 不变
- 新增 `english_name`、`sub_industry`、`full_address`、`description` 等字段（前端按需展示）
- `industry_tags` 移除，`industry` 变为单值 text

**硬约束（Review D5）**：后端返回时必须做字段映射，保持 API 响应 key 不变（`name` 而非 `company_name`），前端零改动。

### 9.2 筛选器适配（CompanyListFilters）

- `sub_industries[]` — 从 text[] overlap 改为双列精确匹配 `wc.industry = ANY() OR wc.sub_industry = ANY()`（Review D6 + Outside Voice D13）
- `employee_scale[]` — 值格式需确认 wmt 的 employee_size 值域
- `sources[]` — 从子查询改为 data_source_tags overlap
- `founded_year_from/to` — 直接对比 int，无需 EXTRACT

## 10. fan_out.py 处理

D8 决定暂不改造 keyword pipeline。fan_out.py 中 5 处引用：

- `clean_company_keywords` 读写 — 保持不动，后续统一改造
- 但需确认 fan_out 是否也引用 `clean_companies` 做其他逻辑

fan_out.py 标注 `TODO: 后续 keyword pipeline 改造时切换到 wmt 表`。

## 11. 不需变更的部分

- `dashboard_overview()` — 仅查 tenant_companies 表，无 clean_companies 引用
- admin 端所有 wmt API — 不在本次范围
- `clean_companies` / `clean_contacts` / `clean_company_sources` 表结构 — 保留不动
