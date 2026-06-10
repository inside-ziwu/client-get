# 设计

## 1. 共享模块 `backend/app/services/collection_source.py`

collection_type 业务口径的单一真源（工程审查 3A）。导出：

```python
KEYWORD_COLLECTION_TAG = "外贸通关键词采集"
# SQL 片段常量（jsonb 包含表达式，admin/tenant/worker 拼 SQL 时引用）
KEYWORD_TAG_JSONB = """'["外贸通关键词采集"]'::jsonb"""

def compute_collection_type(data_source_tags) -> str:
    """包含采集标签 → 'keyword'；NULL/空数组/不包含 → 'reverse'。"""
```

说明：SQL 条件仍以字符串片段形式出现在各处 SQL 中（Codex #9 已接受「共享常量 + 各处 SQL 表达式」的现实），但标签字面量和判定口径只此一处。

- `admin_collection_service.py` 删除本地 `_keyword_tag_jsonb` 与行内判定，改引用本模块。
- admin 现有 `test_wmt_clean_filter.py` 中 collection_type 计算类测试迁移到共享模块测试上（SQL 过滤断言保留在原文件）。

## 2. 行业 fan-out（`wmt_lineage_repair.py`）

新增常量与 SQL，与现有 `_SQL_FAN_OUT_ACTIVE_KEYWORDS` 并列，在 `run_wmt_lineage_repair_on_connection` 中于 `_SQL_DELETE_STALE_RELATIONS` 之前执行：

```python
# 批次标签 → 行业 的硬编码规则（D3 YAGNI 取舍，第二行业出现时迁移到配置，见 TODOS）
# 新租户行业写法若不在别名表内会静默漏推，新增行业别名需同步登记此处
_PCB_INDUSTRY_ALIASES = ["pcb", "电路板"]  # 全小写，比对时 lower(trim())
```

```sql
INSERT INTO tenant_companies (tenant_id, clean_company_id, business_status, data_status)
SELECT DISTINCT
  t.id, wc.id, 'new',
  CASE
    WHEN COALESCE(wc.contacts_count, 0) = 0 THEN 'missing_contacts'
    WHEN (wc.domain IS NULL AND wc.industry IS NULL AND wc.product_tags IS NULL)
      THEN 'insufficient_data'
    ELSE 'ready'
  END
FROM tenants t
JOIN waimaotong_clean_companies wc
  ON wc.data_source_tags @> '["外贸通关键词采集"]'::jsonb
WHERE t.status = 'active'
  AND lower(trim(t.industry)) = ANY(:industry_aliases)
ON CONFLICT (tenant_id, clean_company_id) DO UPDATE
SET data_status = EXCLUDED.data_status,
    updated_at = now()
WHERE tenant_companies.data_status IS DISTINCT FROM EXCLUDED.data_status
```

要点：
- data_status CASE 与现有关键词 fan-out 完全一致
- 不含 visibility_status（与现有约定一致，见 test_lineage_repair_no_visibility.py）
- 模块 docstring 的三步流程描述同步更新为四步
- stats 字典新增 `industry_fan_out` 计数

```
自愈循环（每 interval 一轮）
  1. normalize keyword_master_ids
  2. 血缘回填（clean path → raw fallback）        ← 精准反推链路
  3. 关键词 fan-out（tenant_keyword 订阅匹配）     ← 精准反推链路
  4. 行业 fan-out（批次标签 → PCB 租户）【新增】   ← 关键词采集链路
  5. 清理 stale 关系
```

## 3. tenant_query_service 修复与扩展

### 3.1 存量 jsonb bug 修复（1A + 10A，生产库实锤两列均为 jsonb）

| 行 | 现状（错误） | 改为 |
|----|--------------|------|
| :248 | `wc.data_source_tags && ARRAY[:source_type]::text[]` | `wc.data_source_tags @> jsonb_build_array(:source_type)` |
| :251 | `wc.data_source_tags && :sources` | `EXISTS (SELECT 1 FROM jsonb_array_elements_text(wc.data_source_tags) s WHERE s = ANY(:sources))` |
| :636 | 同 :251 | 同上 |
| :231 | `wc.product_tags && :product_tags` | `EXISTS (SELECT 1 FROM jsonb_array_elements_text(wc.product_tags) p WHERE p = ANY(:product_tags))` |

实施时全文件 grep ` && ` 确认无第五处。

### 3.2 collection_type

- `companies_page`：新增 `collection_type: str | None` 参数。`keyword` → `data_source_tags @>` jsonb 包含；`reverse` → `(IS NULL OR NOT @>)`；行输出新增 `"collection_type": compute_collection_type(row["data_source_tags"])`
- `v3_company_detail`：返回 dict 新增 `collection_type`（同口径）
- `ops.py` 路由新增 `collection_type: str | None = None` 透传

## 4. alembic 迁移：GIN 索引（8A）

```python
op.execute(
    "CREATE INDEX IF NOT EXISTS idx_wmt_clean_data_source_tags_gin "
    "ON waimaotong_clean_companies USING gin (data_source_tags jsonb_path_ops)"
)
```

注意：data_source_tags 列由外部采集程序创建、不在 alembic 体系内，迁移需容忍列已存在的前提（生产/开发库均已有该列；若新环境无此列，迁移用 `IF EXISTS` 防御或先建列——以实施时实际情况为准，fail fast 报清楚）。

## 5. 前端（tenant）

- `shared-api/src/tenant/companies.ts`：列表行与详情类型新增 `collection_type: 'keyword' | 'reverse'`；列表参数新增 `collection_type?: string`
- `company-filters.tsx`：`FilterValues`/`EMPTY_FILTERS`/`buildParams` 新增 collection_type；筛选选项前端硬编码（不限/关键词采集/精准反推），不依赖 companies_filters 接口
- `companies/page.tsx`：新增「采集类型」列（`keyword → 关键词采集，reverse → 精准反推`），列头数组与空态 colSpan 同步更新
- `company-detail.tsx`：详情展示采集类型（同口径映射）

## 6. 测试（全部 pytest，SQL 字符串断言约定，4A）

- `test_collection_source.py`（新）：判定函数 keyword/含多标签/None/空数组/不含 → 口径正确；SQL 片段常量内容
- `test_lineage_repair_industry_fanout.py`（新）：SQL 含 jsonb 包含、`lower(trim`、`= ANY`、`status = 'active'`、CASE 三分支、ON CONFLICT、无 visibility_status；执行顺序在 delete_stale 之前；别名常量全小写
- `test_tenant_companies_filter.py`（新）：collection_type=keyword/reverse/None 三分支 WHERE 断言；**[CRITICAL 回归]** source_type/sources/product_tags 修复后 SQL 不含 `&& ARRAY`、不含 `&& :`；行输出含 collection_type
- ops.py 参数透传断言

## 7. 验证（T8，手动）

dev 库跑一轮 `run_wmt_lineage_repair_once` → 校验 PCB/电路板租户 tenant_companies 含全部关键词采集公司、重跑幂等、data_status 分级正确；启动前后端手动 QA（测试计划见 `~/.gstack/projects/inside-ziwu-client-get/lay-main-eng-review-test-plan-20260609-210303.md`）。
