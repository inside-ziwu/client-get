# Slice C4/C5/C6 — tenant-companies 私有操作 + 10项筛选 + 评分模板

状态：**✅ 本地 alembic upgrade 验证通过，已签字**

创建日期：2026-05-07

---

## 目标

实现 v3-tenant-companies 轨道三个子功能：

| 轨道 | 任务编号 | 说明 |
|------|----------|------|
| C4 | T-TC-08~54 | 私有操作 4 件套：人工调分 + 备注 + 标签 + 编辑态 |
| C5 | T-TC-60~74 | 公司列表 10 项筛选 |
| C6 | T-TC-80~112 | 评分模板 industry 字段 + 租户权重自定义 |

---

## 变更范围

### 数据库迁移

- [x] `backend/alembic/versions/20260507_0025_tenant_companies_private_fields.py`
  - `tenant_companies` 新增：`score_adjustment int CHECK ±20`、`score_adjusted_at`、`score_adjusted_by uuid→users`、`score_adjust_reason text`
  - 创建稀疏索引 `idx_tenant_companies_score_adjustment WHERE score_adjustment != 0`
  - downgrade：DROP 4 列 + 索引

- [x] `backend/alembic/versions/20260507_0026_scoring_templates_industry.py`
  - `scoring_templates` 新增：`industry text NOT NULL DEFAULT 'PCB'`
  - downgrade：DROP COLUMN

- [x] `backend/alembic/versions/20260507_0027_tenant_scoring_weights.py`
  - 新建 `tenant_scoring_weights(id, tenant_id, template_id, dimension, weight, created_at, updated_at)`
  - UNIQUE(tenant_id, template_id, dimension)
  - 启用 RLS（tenant select/write policies）
  - downgrade：DROP TABLE

### 后端服务

- [x] `backend/app/services/tenant_ops_service.py`
  - `update_prospect`：支持 `score_adjustment`（范围 ±20 校验）+ 写 `score_adjusted_at/by/reason`
  - `get_company`：SELECT 新增 4 个调分字段，返回值包含 `score_adjustment/score_adjusted_at/score_adjusted_by/score_adjust_reason`

- [x] `backend/app/services/tenant_query_service.py`
  - `companies()`：支持 C5 10 项筛选参数（keyword/grade/countries/sub_industries/product_tags/sources/contact_count_range/founded_year_from/founded_year_to/employee_scales/min_score/max_score/limit/cursor）
  - 动态构建 WHERE 子句，多选字段用数组参数 + `&&` 操作符

- [x] `backend/app/services/tenant_scoring_weights_service.py`（新建）
  - `list_weights(conn, tenant_id, template_id?)`：查询租户权重列表
  - `upsert_weights(conn, tenant_id, payload)`：批量 upsert（ON CONFLICT DO UPDATE）

- [x] `backend/app/services/scoring_service.py`
  - 新增 `score_to_grade(score: int) -> str` 静态方法（固定档位：≥90→S，≥70→A，≥50→B，≥30→C，其余→D）
  - `persist_score_result`：读取 `score_adjustment`，计算 `final_score = clamp(total_score + score_adjustment, 0, 100)`，以 final_score 重新映射等级

### 后端 API

- [x] `backend/app/api/tenant/ops.py`
  - `GET /companies`：新增 14 个 Query 参数支持 C5 筛选
  - 新增 `GET /scoring-weights`：按 template_id 查询权重
  - 新增 `PUT /scoring-weights`：批量 upsert 权重

### 前端

- [x] `frontend/packages/shared-api/src/tenant/companies.ts`
  - `Company` interface 扩展：`score_adjustment/score_adjusted_at/score_adjusted_by/score_adjust_reason/employee_scale/contacts_count/product_tags`
  - 新增 `CompanyListFilters` 接口（14 个筛选字段）

- [x] `frontend/apps/tenant/src/pages/Companies/index.tsx`
  - C5 筛选栏：国家/行业/产品标签/来源（Select 多选 OR）+ 联系人数量（Radio.Group 档位）+ 成立年份范围 + 规模多选 + 分数区间 + 关键词/评级
  - 已选筛选 Chip 展示 + 清空按钮（筛选变化联动分页重置）
  - C4 Drawer 编辑态：`score_adjustment` InputNumber ±20 + `score_adjust_reason` textarea + `notes` textarea + `tags` Select tags
  - 展示态/编辑态切换（Drawer extra 按钮区域）
  - 调用 `tenantApi.prospects.update()` 提交

- [x] `backend/03_database/schema.sql`
  - `tenant_companies` 表新增 4 个调分字段（已标注 0025 来源）
  - `scoring_templates` 新增 `industry` 字段（已标注 0026 来源）
  - 新增 `tenant_scoring_weights` 完整表定义（已标注 0027 来源）

---

## 设计决策

### score_adjustment 不存 company_scores，直接存 tenant_companies？
调分是租户私有的"主观覆盖"，不应污染 company_scores（评分历史）。final_score = total_score + score_adjustment 在 scoring worker 写回 tenant_companies 时计算，不修改 company_scores。

### C5 产品标签和来源用 `&&` 数组操作符？
clean_companies.product_tags / sources 是 PostgreSQL text[]，`&&` 表示"有任意一个匹配"（OR 语义），符合多选 OR 需求，无需 unnest。

### tenant_scoring_weights 的 weight 含义？
替换维度的默认权重（来自 scoring_templates.dimensions[*].weight），scoring worker 后续读取 tenant_scoring_weights 时覆盖模板默认值，本次实现存储层和 API，worker 集成可在后续 slice 完成。

---

## 验收标准

```bash
# 迁移验证
cd backend
uv run alembic upgrade 20260507_0027
# 期望：
# Running upgrade 20260507_0017 -> 20260507_0025 ...
# Running upgrade 20260507_0025 -> 20260507_0026 ...
# Running upgrade 20260507_0026 -> 20260507_0027 ...
```

---

## 签字

- [x] 本地 alembic upgrade 验证通过（lay 2026-05-07）
  - migration 0025：tenant_companies 4 列 + 稀疏索引 ✅
  - migration 0026：scoring_templates.industry 列 ✅
  - migration 0027：tenant_scoring_weights 表 + RLS ✅
  - 链路：0017 → 0025 → 0026 → 0027（另一分支 0029 保持独立 head）✅
- [ ] Sealos 生产部署（lay）
