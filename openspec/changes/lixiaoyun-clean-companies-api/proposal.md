# Proposal · lixiaoyun-clean-companies-api

## Why

"同行公司（清洗）"页面当前后端基于 `peer_companies` + `peer_company_keywords` + `peer_company_sources` 三表联查，这是旧的清洗管线产物。实际数据已迁移到 `lixiaoyun_api_clean_companies` 表（按 pid 去重聚合，keyword_master_ids 数组直接内嵌），需要重写 API 适配新表结构。

## What Changes

### 新增

- **列表端点** `GET /collection/lixiaoyun-clean-companies`
  - 数据库表：`lixiaoyun_api_clean_companies`
  - 筛选条件参考同行公司原始 API（`/raw/lixiaoyun/companies`）风格，新增 `industry_tag` 精确筛选
  - 搜索词通过 `keyword_master_ids`（uuid 数组）关联 `keyword_master` 表聚合返回
  - 排序：`created_at DESC`

- **详情端点** `GET /collection/lixiaoyun-clean-companies/{company_id}`
  - 返回字段 ≈ 列表 + 更多工商详情
  - 搜索词聚合逻辑同列表

### 不包含

- 不含联系人端点
- 不修改现有 `peer_companies` 相关 API（保持向后兼容，由前端切换调用）
- 不修改前端（本 change 仅后端）

## 端点规格

### 列表 `GET /collection/lixiaoyun-clean-companies`

**筛选参数**（参考同行公司原始 API）：

| 参数 | 类型 | 说明 |
|---|---|---|
| `page` | int | 页码，默认 1 |
| `page_size` | int | 每页条数，默认 20 |
| `keyword` | str | 企业名/英文名/官网/pid 模糊搜索 |
| `keyword_filter` | str | 搜索词筛选，模糊匹配 keyword_master.keyword |
| `industry_tag` | str | **新增**，标签精确匹配 `industry_tags` 字段 |
| `found_date_start` | str | 成立日期起（esdate 毫秒时间戳比较） |
| `found_date_end` | str | 成立日期止 |
| `reg_capital` | str | 注册资本区间：lt100 / 100_500 / 500_2000 / 2000_1e / gt1e |
| `employee_scale` | str | 人员规模区间：lt10 / 10_50 / 50_200 / 200_1000 / gt1000 |
| `has_name_en` | bool | 是否有英文名 |
| `has_domain` | bool | 是否有官网 |

**返回字段**：

```json
{
  "id": "bigint as string",
  "pid": "text",
  "entname": "text",
  "entname_eng": "text",
  "esdate": "date (from 毫秒时间戳转换)",
  "reg_cap": "text",
  "official_website": "text",
  "regccap": "text",
  "scale": "text",
  "annual_turnover": "text",
  "legalperson": "text",
  "geo_address": "text",
  "dom": "text",
  "industry_tag": "text (来自 industry_tags 列)",
  "keyword_master": [
    {
      "keyword_master_id": "uuid as string",
      "keyword": "text",
      "keyword_normalized": "text"
    }
  ],
  "created_at": "ISO datetime"
}
```

排序：`created_at DESC, id DESC`

### 详情 `GET /collection/lixiaoyun-clean-companies/{company_id}`

**返回字段**：列表全部字段 + 以下补充：

```json
{
  "...列表全部字段",
  "uncid": "text",
  "enttype": "text",
  "enttype_code": "text",
  "entstatus": "text",
  "entstatus_code": "integer",
  "regno": "text",
  "organizational_code": "text",
  "opfrom": "bigint",
  "opto": "bigint",
  "regorg": "text",
  "apprdate": "bigint",
  "revokedate": "bigint",
  "province": "integer",
  "city": "integer",
  "district": "integer",
  "reg_province": "integer",
  "reg_city": "integer",
  "reg_district": "integer",
  "oploc": "text",
  "industryphy": "text",
  "industryphy_desc": "text",
  "opscope": "text",
  "secindustry": "jsonb",
  "secindustry_desc": "jsonb",
  "industry_l3": "text",
  "industry_l3_desc": "text",
  "industry_l4": "text",
  "industry_l4_desc": "text",
  "historyname_list": "jsonb",
  "legalperson_desc": "text",
  "location_code": "text",
  "updated_at": "ISO datetime"
}
```

## 关键实现细节

### keyword_master 聚合

```sql
-- 列表中通过 CTE 聚合
WITH filtered AS (
    SELECT c.* FROM lixiaoyun_api_clean_companies c
    WHERE ... ORDER BY c.created_at DESC, c.id DESC
    LIMIT :limit OFFSET :offset
),
keyword_agg AS (
    SELECT
        f.id AS company_id,
        jsonb_agg(
            jsonb_build_object(
                'keyword_master_id', km.id::text,
                'keyword', km.keyword,
                'keyword_normalized', km.keyword_normalized
            )
            ORDER BY km.keyword_normalized
        ) AS keyword_master
    FROM filtered f
    JOIN keyword_master km ON km.id = ANY(f.keyword_master_ids)
    GROUP BY f.id
)
SELECT f.*, COALESCE(ka.keyword_master, '[]'::jsonb) AS keyword_master
FROM filtered f
LEFT JOIN keyword_agg ka ON ka.company_id = f.id
```

### keyword_filter 筛选

```sql
EXISTS (
    SELECT 1 FROM keyword_master km
    WHERE km.id = ANY(c.keyword_master_ids)
      AND (km.keyword ILIKE '%' || :keyword_filter || '%'
           OR km.keyword_normalized ILIKE '%' || :keyword_filter || '%')
)
```

### industry_tag 筛选

```sql
c.industry_tags = :industry_tag
```

### 注册资本 / 人员规模解析

提取为共享常量 `REG_CAP_CASE_EXPR` 和 `EMPLOYEE_SCALE_CASE_EXPR`（定义在 `admin_collection_service.py` 顶部），供同行公司原始 API 和本 API 共用，消除 CASE 表达式的重复。

## 涉及文件

| 文件 | 变更 |
|---|---|
| `backend/app/api/admin/collection.py` | 新增 2 个路由 |
| `backend/app/services/admin_collection_service.py` | 提取 CASE 共享常量 + 新增 list / detail / filter 方法 |

## 工程审查决策记录

| ID | 决策 | 理由 |
|---|---|---|
| R1-D1 | 路由使用 PlatformAuthContext 认证（非 get_pool） | 与文件中 18 个路由一致，避免绕过认证 |
| R1-D2 | 注册资本/人员规模 CASE 表达式提取为共享函数 | 消除 list_raw_companies + list_v3_raw_companies 间重复的 ~30 行 SQL 片段 |
| R1-D3 | T1 重构加回归测试 | 确保 CASE 提取不破坏现有 raw API 行为 |
| R1-D4 | has_name_en / has_domain 补充 False 路径 | 与 lixiaoyun raw API 行为一致，前端可筛选"无英文名" |
| R1-D5 | page/page_size 加 Query() 边界校验 | 与 V3 raw 路由规范一致：Query(ge=1, le=100) |
| R0-D5a | keyword_agg CTE 的 jsonb_agg 加 `ORDER BY km.keyword_normalized` | 保证前端搜索词排序稳定、可预测 |
| R0-D5b | keyword_filter EXISTS 同时匹配 `km.keyword` 和 `km.keyword_normalized` | 避免用户用 normalized 形式搜索时无结果 |

## GSTACK REVIEW REPORT

**Skill**: plan-eng-review (FULL_REVIEW + Outside Voice)
**Branch**: claude/epic-johnson-c1f722
**Date**: 2026-05-16
**Status**: CLEAN — 所有发现已解决

### 审查总结

| 审查维度 | 发现数 | 关键发现 |
|---|---|---|
| 架构 | 1 | D1: 路由认证模式必须使用 PlatformAuthContext，非 get_pool |
| 代码质量 | 1 | D2: T1 目标方法描述不准确，`_peer_filter_parts()` 用 regexp_replace 不参与提取 |
| 测试 | 1 | D3: T1 CASE 提取需要回归测试覆盖 list_raw_companies + list_v3_raw_companies |
| 性能 | 0 | CTE 先分页再 JOIN keyword_master，keyword_master_ids 有 GIN 索引，无瓶颈 |
| 外部声音 (Codex) | 2 | D4: has_name_en/has_domain 缺 False 路径；D5: page/page_size 缺 Query() 约束 |

### 决策清单

- **D1** ✅ 修正路由为 PlatformAuthContext — 已更新 T6
- **D2** ✅ 修正 T1 描述为 list_raw_companies + list_v3_raw_companies — 已更新 T1
- **D3** ✅ T7 新增回归测试项 8-9 — 已更新 tasks.md
- **D4** ✅ T2 补充 has_name_en/has_domain False 路径 — 已更新 T2
- **D5** ✅ T6 加 Query(ge=1, le=100) 约束 — 已更新 T6

### 实施就绪度

- proposal.md: ✅ 完整
- tasks.md: ✅ 7 个任务，含回归测试
- 阻塞项: 无
- 建议: 按 T1 → T5 → T2 → T3 → T4 → T6 → T7 顺序实施
