# Tasks · lixiaoyun-clean-companies-api

## T1 — 提取 CASE 表达式为共享辅助函数

**文件**：`backend/app/services/admin_collection_service.py`

在文件顶部（类定义外）新增两个辅助函数：

```python
def _reg_cap_case(col: str) -> str:
    """注册资本中文万/亿 → 万元数值 CASE 表达式"""
    return f"""
CASE
  WHEN {col} ~ E'^[0-9.]+(亿|亿元)' THEN (substring({col}, E'^([0-9.]+)'))::numeric * 10000
  WHEN {col} ~ E'^[0-9.]+(万|万元)' THEN (substring({col}, E'^([0-9.]+)'))::numeric
  ELSE NULL
END"""

REG_CAP_RANGE = {
    "lt100": "< 100",
    "100_500": "BETWEEN 100 AND 499.999",
    "500_2000": "BETWEEN 500 AND 1999.999",
    "2000_1e": "BETWEEN 2000 AND 9999.999",
    "gt1e": ">= 10000",
}

def _employee_scale_case(col: str) -> str:
    """人员规模中文 → 下界整数 CASE 表达式"""
    return f"""
CASE
  WHEN {col} ~ E'^([0-9]+)人以下' THEN 1
  WHEN {col} ~ E'^([0-9]+)[-–]([0-9]+)' THEN (substring({col}, E'^([0-9]+)'))::int
  WHEN {col} ~ E'^([0-9]+)人以上' THEN (substring({col}, E'^([0-9]+)'))::int
  ELSE NULL
END"""

EMPLOYEE_SCALE_RANGE = {
    "lt10": "< 10",
    "10_50": "BETWEEN 10 AND 49",
    "50_200": "BETWEEN 50 AND 199",
    "200_1000": "BETWEEN 200 AND 999",
    "gt1000": ">= 1000",
}
```

然后替换以下两处内联 CASE 表达式为调用共享函数：

1. `list_raw_companies()` line 709-742（旧原始 API，`elif table == "lixiaoyun":` 分支）
   - 使用 `_reg_cap_case("reg_capital")` + `_employee_scale_case("employee_scale")`（无表别名）
2. `list_v3_raw_companies()` line 1156-1190（V3 原始 API）
   - 使用 `_reg_cap_case("c.reg_cap")` + `_employee_scale_case("c.scale")`

注意：`_peer_filter_parts()`（line 2010）使用 `regexp_replace` 方式，**不改动**。

**验收**：现有筛选行为不变，grep 搜索 `_RC_EXPR` / `_ES_EXPR` 只出现在共享函数中。

---

## T2 — 新增 `_lixiaoyun_clean_filter_parts()` 筛选方法

**文件**：`backend/app/services/admin_collection_service.py`

新增私有方法，返回 `(where_parts: list[str], params: dict)`。筛选逻辑：

| 参数 | SQL |
|---|---|
| `keyword` | `c.entname ILIKE / c.entname_eng ILIKE / c.official_website ILIKE / c.pid ILIKE` |
| `keyword_filter` | `EXISTS (SELECT 1 FROM keyword_master km WHERE km.id = ANY(c.keyword_master_ids) AND (km.keyword ILIKE ... OR km.keyword_normalized ILIKE ...))` |
| `industry_tag` | `c.industry_tags = :industry_tag` |
| `found_date_start` | `c.esdate >= EXTRACT(EPOCH FROM ...)` 毫秒时间戳 |
| `found_date_end` | `c.esdate <= EXTRACT(EPOCH FROM ...)` 毫秒时间戳 |
| `reg_capital` | 使用 T1 共享函数 `_reg_cap_case("c.reg_cap")` |
| `employee_scale` | 使用 T1 共享函数 `_employee_scale_case("c.scale")` |
| `has_name_en` True | `c.entname_eng IS NOT NULL AND c.entname_eng != ''` |
| `has_name_en` False | `(c.entname_eng IS NULL OR c.entname_eng = '')` |
| `has_domain` True | `c.official_website IS NOT NULL AND c.official_website != ''` |
| `has_domain` False | `(c.official_website IS NULL OR c.official_website = '')` |

参考 `_peer_filter_parts()`（line 2010）和 `list_v3_raw_companies()` 中的 esdate 时间戳处理。

---

## T3 — 新增 `list_lixiaoyun_clean_companies()` 列表方法

**文件**：`backend/app/services/admin_collection_service.py`

CTE 结构：

```sql
WITH filtered AS (
    SELECT c.* FROM lixiaoyun_api_clean_companies c
    WHERE {where_clause}
    ORDER BY c.created_at DESC, c.id DESC
    LIMIT :limit OFFSET :offset
),
keyword_agg AS (
    SELECT f.id AS company_id,
           jsonb_agg(
               jsonb_build_object(
                   'keyword_master_id', km.id::text,
                   'keyword', km.keyword,
                   'keyword_normalized', km.keyword_normalized
               ) ORDER BY km.keyword_normalized
           ) AS keyword_master
    FROM filtered f
    JOIN keyword_master km ON km.id = ANY(f.keyword_master_ids)
    GROUP BY f.id
)
SELECT f.*, COALESCE(ka.keyword_master, '[]'::jsonb) AS keyword_master
FROM filtered f
LEFT JOIN keyword_agg ka ON ka.company_id = f.id
ORDER BY f.created_at DESC, f.id DESC
```

count 查询：`SELECT COUNT(*) FROM lixiaoyun_api_clean_companies c WHERE {where_clause}`

返回列表字段通过 `_format_lixiaoyun_clean_row()` 格式化。

---

## T4 — 新增 `get_lixiaoyun_clean_company_detail()` 详情方法

**文件**：`backend/app/services/admin_collection_service.py`

```sql
SELECT c.*,
       COALESCE(
           (SELECT jsonb_agg(
               jsonb_build_object(
                   'keyword_master_id', km.id::text,
                   'keyword', km.keyword,
                   'keyword_normalized', km.keyword_normalized
               ) ORDER BY km.keyword_normalized
           )
           FROM keyword_master km
           WHERE km.id = ANY(c.keyword_master_ids)),
           '[]'::jsonb
       ) AS keyword_master
FROM lixiaoyun_api_clean_companies c
WHERE c.id = :company_id
```

若找不到返回 404。返回详情字段通过 `_format_lixiaoyun_clean_row(row, detail=True)` 格式化。

---

## T5 — 新增 `_format_lixiaoyun_clean_row()` 格式化方法

**文件**：`backend/app/services/admin_collection_service.py`

参考 `_format_peer_row()`（line 2111）。

**列表字段**：id(str), pid, entname, entname_eng, esdate(毫秒→date), reg_cap, official_website, regccap, scale, annual_turnover, legalperson, geo_address, dom, industry_tag(来自 industry_tags 列), keyword_master(jsonb), created_at(ISO)

**详情额外字段**（`detail=True` 时）：uncid, enttype, enttype_code, entstatus, entstatus_code, regno, organizational_code, opfrom, opto, regorg, apprdate, revokedate, province, city, district, reg_province, reg_city, reg_district, oploc, industryphy, industryphy_desc, opscope, secindustry, secindustry_desc, industry_l3, industry_l3_desc, industry_l4, industry_l4_desc, historyname_list, legalperson_desc, location_code, updated_at(ISO)

esdate 转换：`毫秒时间戳 → datetime → date 字符串`，与 lixiaoyun raw API 相同。

---

## T6 — 新增路由

**文件**：`backend/app/api/admin/collection.py`

```python
@router.get("/collection/lixiaoyun-clean-companies")
async def list_lixiaoyun_clean_companies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    keyword_filter: str | None = None,
    industry_tag: str | None = None,
    found_date_start: str | None = None,
    found_date_end: str | None = None,
    reg_capital: str | None = None,
    employee_scale: str | None = None,
    has_name_en: bool | None = None,
    has_domain: bool | None = None,
    context: PlatformAuthContext = Depends(get_current_platform_user),
):
    ...  # 使用 context.connection

@router.get("/collection/lixiaoyun-clean-companies/{company_id}")
async def get_lixiaoyun_clean_company_detail(
    company_id: int,
    context: PlatformAuthContext = Depends(get_current_platform_user),
):
    ...  # 使用 context.connection
```

路由放在 peer-companies 路由附近。

---

## T7 — 合约测试

**文件**：`backend/tests/test_lixiaoyun_clean_companies_contract.py`（新建）

参考 `test_admin_raw_company_pagination_contract.py` 的 pattern，验证：

**新 API 合约：**
1. 列表 SQL 包含 `lixiaoyun_api_clean_companies` 表名
2. CTE 包含 `keyword_agg` 和 `ORDER BY km.keyword_normalized`
3. keyword_filter EXISTS 同时匹配 `km.keyword` 和 `km.keyword_normalized`
4. industry_tag 精确匹配 `c.industry_tags = :industry_tag`
5. 使用共享的 `_reg_cap_case` 和 `_employee_scale_case`
6. 排序为 `created_at DESC, id DESC`
7. 详情 SQL 包含 `WHERE c.id = :company_id`

**T1 回归：**
8. `list_raw_companies` 方法源码仍包含 `_reg_cap_case` 或 `REG_CAP_RANGE` 引用
9. `list_v3_raw_companies` 方法源码仍包含 `_reg_cap_case` 或 `REG_CAP_RANGE` 引用
