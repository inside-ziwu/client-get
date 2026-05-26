---
title: "feat: 公司列表和详情新增来源同行字段"
status: completed
origin: openspec/changes/add-source-competitor-field/
created: 2026-05-26
depth: lightweight
execution_posture: tdd
---

# feat: 公司列表和详情新增来源同行字段

## 问题框架

tenant 端公司列表和详情页缺少"来源同行"信息。每家公司是通过某个同行厂商在外贸通反推获得的，该信息存储在 `waimaotong_raw_companies.source_competitor`，覆盖率 99.96%，但当前查询未 JOIN 这张表，前端无法展示。

## 范围边界

**包含**：后端列表/详情查询加 LEFT JOIN、API 响应加字段、前端列表加列、详情加字段
**不包含**：数据冗余、数据库迁移、按来源同行筛选/搜索

## 关键技术决策

- **LEFT JOIN 取值**：两表极小（raw 3k / clean 2k），JOIN 性能可忽略；冗余方案需迁移+回填+同步，不值得 (see origin: openspec/changes/add-source-competitor-field/design.md)
- **关联字段**：`waimaotong_raw_companies.sys_company_id = waimaotong_clean_companies.sys_company_id`，经验证为唯一有效关联（real_id 和 company_id 匹配数为 0）

## 实施单元

### U1. 后端列表查询加 source_competitor

**目标**：`companies_page()` SQL 加 LEFT JOIN，响应加 `source_competitor` 字段

**需求**：列表 API 返回 source_competitor（string | null）

**依赖**：无

**文件**：
- `backend/app/services/tenant_query_service.py`
- `backend/tests/test_source_competitor.py`（新建）

**方案**：
- SQL 的 FROM 子句在 `JOIN tenant_companies tc` 之后追加 `LEFT JOIN waimaotong_raw_companies wr_raw ON wr_raw.sys_company_id = wc.sys_company_id`
- SELECT 追加 `wr_raw.source_competitor`
- 响应字典追加 `"source_competitor": row["source_competitor"]`

**模式参考**：现有 `companies_page()` 方法第 320-400 行的 SELECT / JOIN / 响应字典结构

**执行提示**：先写测试，验证 mock 的 SQL 结果中 `source_competitor` 字段正确透传到响应字典

**测试场景**：
- 正常情况：raw 有 source_competitor 值时，响应中该字段返回对应字符串
- 空值情况：raw 匹配但 source_competitor 为 null 时，响应中该字段返回 null
- 未匹配情况：clean 公司无对应 raw 记录时（LEFT JOIN），响应中该字段返回 null

**验证**：测试通过；本地启动后端调用 `/t/{slug}/api/v1/companies` 确认响应包含 `source_competitor`

---

### U2. 后端详情查询加 source_competitor

**目标**：`v3_company_detail()` SQL 加 LEFT JOIN，响应加 `source_competitor` 字段

**需求**：详情 API 返回 source_competitor（string | null）

**依赖**：U1（复用测试模式）

**文件**：
- `backend/app/services/tenant_query_service.py`
- `backend/tests/test_source_competitor.py`

**方案**：
- 与 U1 相同的 JOIN 子句，追加到 `v3_company_detail()` 的 FROM 之后（第 451-454 行区域）
- SELECT 追加 `wr_raw.source_competitor`
- 响应字典追加 `"source_competitor": row["source_competitor"]`

**执行提示**：先写测试再改实现

**测试场景**：
- 正常情况：详情响应包含 source_competitor 字符串
- 空值情况：source_competitor 为 null 时返回 null

**验证**：测试通过；本地调用详情 API 确认字段存在

---

### U3. 前端类型 + 列表页加列

**目标**：Company 类型加字段，列表表格加"来源同行"列

**需求**：列表页展示来源同行

**依赖**：U1

**文件**：
- `frontend/packages/shared-api/src/tenant/companies.ts`
- `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`

**方案**：
- Company 接口追加 `source_competitor?: string`
- 表头数组插入 `'来源同行'`（建议放在"评分"之后或"细分行业"之后）
- tbody 对应位置加 `<td>{dash(row.source_competitor)}</td>`
- 更新 colSpan（当前 13 → 14）

**模式参考**：现有列表页第 320-400 行的表头数组和 tbody 渲染

**测试期望**：无 — 纯 UI 展示变更，`pnpm build` 类型检查通过即可

**验证**：`pnpm build` 无类型错误；用户手动验收列表页新增列

---

### U4. 前端详情页加字段

**目标**：公司详情页"基本信息"区域新增"来源同行"展示

**需求**：详情页展示来源同行

**依赖**：U3（复用类型定义）

**文件**：
- `frontend/apps/tenant/src/components/company-detail.tsx`

**方案**：
- 在"基本信息"section 的 `grid grid-cols-2` 中追加 `<InfoRow label="来源同行" value={c.source_competitor} />`

**模式参考**：现有 InfoRow 使用模式（第 96-109 行）

**测试期望**：无 — 纯 UI 展示变更

**验证**：`pnpm build` 无类型错误；用户手动验收详情页新增字段

## 延迟到后续

- 按来源同行筛选/搜索
- `waimaotong_raw_companies.sys_company_id` 索引（数据量极小，暂不需要）
- 处理未来一个 clean 对应多条 raw 的去重逻辑

## GSTACK REVIEW REPORT

**日期**：2026-05-26
**审阅人**：gstack /plan-eng-review
**计划深度**：lightweight
**执行姿态**：tdd

### 审阅结论：✅ PASS — 可直接实施

### 各维度评估

| 维度 | 结果 | 说明 |
|------|------|------|
| 架构 | ✅ 0 issues | LEFT JOIN 方案合理，数据量极小，与现有 JOIN 模式一致 |
| 代码质量 | ✅ 0 issues | 5 个文件，0 个新类/抽象，纯字段透传 |
| 测试覆盖 | ✅ 0 gaps | 5 个后端场景覆盖正常/null/未匹配，前端类型检查 |
| 性能 | ✅ 0 issues | 3k 行表 LEFT JOIN，分页+LIMIT 约束，微秒级 |

### 已存在的代码

- `waimaotong_raw_companies` 表已在 `admin_collection_service.py` 和 `wmt_lineage.py` 中广泛使用
- `source_competitor` 字段已在 admin 端采集 API 和 lineage worker 中引用
- `tenant_query_service.py` 第 537 行已有 `LEFT JOIN tenant_contacts` 模式可参考
- `InfoRow` 组件、`dash()` 辅助函数已存在

### 不在范围内

- 按来源同行筛选/搜索
- 数据冗余/迁移
- `sys_company_id` 索引
- 一对多去重逻辑

### 失败模式

1. **raw 表无匹配**（0.04%）→ LEFT JOIN 返回 null，前端 `dash()` 处理为 `—`，无影响
2. **未来一对多**→ JOIN 产生重复行 → 已在"延迟到后续"记录，当前数据为一对一

### 实施任务

| 顺序 | 单元 | 预估 | 文件 |
|------|------|------|------|
| 1 | U1 后端列表 | 3-5 min | `tenant_query_service.py`, `test_source_competitor.py` |
| 2 | U2 后端详情 | 2-3 min | 同上 |
| 3 | U3 前端类型+列表 | 3-5 min | `companies.ts`, `page.tsx` |
| 4 | U4 前端详情 | 2-3 min | `company-detail.tsx` |

### Worktree 并行化

不适用 — 4 个单元顺序依赖，总计 10-16 min，无需并行。
