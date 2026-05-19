## 1. 后端 — 列表 API 字段补充 + 双 ID

- [x] 1.1 `TenantQueryService.companies_page` SELECT 新增 `tc.id AS tc_id`（D7：前端操作 API 依赖 tc.id）
- [x] 1.2 SELECT 补充 `wc.sub_industry`、`wc.phone`、`wc.trade_amount_3y_usd`、`wc.trade_count`、`wc.description`、`wc.data_source_tags`、`wc.company_size`
- [x] 1.3 返回字典新增 `tc_id` 和上述字段 key，保持现有字段不变
- [x] 1.4 验证：`curl` 调用列表 API 确认 `tc_id` 和新字段存在

## 2. 后端 — 详情 API 扁平化 + 字段补充

- [x] 2.1 `TenantQueryService.v3_company_detail` 响应扁平化（D1）：将 `tenant_state.note`、`tenant_state.tags`、`tenant_state.score` 提升到根级别
- [x] 2.2 SELECT 补充 AI 评估字段：`score_details`、`company_type_analysis`、`email_priority`、`sales_approach`、`match_reasons`、`potential_needs`、`recommended_products`、`risk_factors`、`main_business`、`trade_summary`、`phone`、`company_size`
- [x] 2.3 返回字典新增 `score_adjustment`（从 `tc.score_adjustment` 读取）
- [x] 2.4 验证：`curl` 调用详情 API 确认扁平化响应和新字段正确

## 3. 后端 — filters API 扩展（4 条独立查询）

- [x] 3.1 `TenantOpsService.companies_filters` 拆为 4 条独立查询（D2）：原 countries/statuses + 新增 sub_industries、product_tags（unnest）、grades
- [x] 3.2 验证：`curl` 调用 filters API 确认 5 个 options 字段返回正确

## 4. 后端 — grade 筛选参数 + PATCH score_adjustment

- [x] 4.1 `GET /companies` 路由新增 `grade` query param（D9），`companies_page` WHERE 加入 grade 过滤
- [x] 4.2 `TenantOpsService.update_prospect` 增加 `score_adjustment` 字段处理，校验范围 -20 ~ +20，超范围返回 422
- [x] 4.3 UPDATE SQL 加入 `score_adjustment = COALESCE(:score_adjustment, score_adjustment)`
- [x] 4.4 验证：`curl` 测试 grade 筛选、score_adjustment 更新和范围校验

## 5. 前端 — 共享类型更新

- [x] 5.1 `Company` 接口删除幽灵字段（D3）：`score_adjusted_at`、`score_adjusted_by`、`score_adjust_reason`、`is_precise_customer`
- [x] 5.2 `Company` 接口新增字段：`tc_id`（D7）、`sub_industry`、`phone`、`trade_amount_3y_usd`、`trade_count`、`description`、`data_source_tags`、`company_size`、`score_details`、`company_type_analysis`、`email_priority`、`sales_approach`、`match_reasons`、`potential_needs`、`recommended_products`、`risk_factors`、`main_business`、`trade_summary`、`score_adjustment`
- [x] 5.3 `CompanyListFilters` 更新为 page-based（D4）：`cursor`/`limit` → `page`/`page_size`，新增 `grade`、范围筛选参数
- [x] 5.4 前端操作 API 调用全部使用 `tc_id`（D7）：blacklist、group batch-add、PATCH prospect
- [x] 5.5 `pnpm build` 确认类型无报错

## 7. 前端 — 筛选面板

- [x] 7.1 `companies/page.tsx` 新增筛选状态管理（搜索词、国家、细分行业、关键词、评级、进口额范围、进口次数范围、联系人范围、成立年范围）
- [x] 7.2 渲染筛选面板 UI：行 1（5 个控件）+ 行 2（4 个范围输入）+ 行 3（查询/重置按钮）
- [x] 7.3 filters query 接入：下拉选项从 `GET /companies/filters` 动态加载
- [x] 7.4 点击"查询"触发列表刷新并回到第 1 页，点击"重置"清空所有筛选
- [x] 7.5 浏览器验证：筛选面板展示正确，筛选参数正确传递到 API

## 8. 前端 — 表格 + 多选 + 分页

- [x] 8.1 表格列按 spec 渲染：checkbox | 公司名+域名 | 国家 | 细分行业 | 关键词 tags | 评级 tag | 总分 | 操作按钮
- [x] 8.2 实现 checkbox 多选逻辑（行选、全选、半选状态）
- [x] 8.3 实现批量操作栏（选中时浮出：已选 N 家 + 加入群组 + 取消选择）
- [x] 8.4 实现页码分页组件（总条数 + 每页条数选择 + 上一页/下一页 + 页码跳转）
- [x] 8.5 浏览器验证：表格列正确、多选交互正常、分页翻页正常

## 9. 前端 — 详情 Drawer

- [x] 9.1 创建 `companies/company-detail.tsx` 组件，660px 宽度
- [x] 9.2 基本信息区域：2 列 grid（网站、国家、细分行业、成立年、关键词 | 评级、总分、评分调整、进口额、进口次数）
- [x] 9.3 AI 评估区域：评分明细进度条、细分行业、公司类型分析、产品标签、匹配原因、潜在需求等（参考 admin CustomerArchivePage）
- [x] 9.4 贸易数据区域：贸易额、次数、摘要
- [x] 9.5 标签区域：只读态 tag 展示 + 编辑态增删
- [x] 9.6 备注区域：只读态文本 + 编辑态 textarea
- [x] 9.7 评分调整：只读态数值展示 + 编辑态 number input（-20 ~ +20）
- [x] 9.8 联系人表：调用 contacts API 加载，表格渲染（姓名、职位、部门、邮箱、邮箱状态、电话）
- [x] 9.9 编辑模式切换：编辑/保存/取消按钮逻辑，保存调 PATCH API
- [x] 9.10 浏览器验证：Drawer 打开关闭正常、各区域展示正确、编辑保存正常

## 10. 前端 — 群组 Modal

- [x] 10.1 创建 `companies/group-modal.tsx` 组件
- [x] 10.2 接入 `GET /groups` 加载群组列表，radio 单选
- [x] 10.3 确认后调用 `POST /groups/{id}/members/batch-add`，支持单条和批量 company IDs
- [x] 10.4 成功后关闭 Modal、刷新列表、清除选中状态
- [x] 10.5 浏览器验证：单条加入、批量加入、无群组提示

## 11. 前端 — 拉黑 Modal

- [x] 11.1 创建 `companies/blacklist-modal.tsx` 组件
- [x] 11.2 确认拉黑后调用 `POST /companies/{id}/blacklist`
- [x] 11.3 成功后关闭 Modal、刷新列表
- [x] 11.4 浏览器验证：拉黑确认、取消、列表刷新

## 12. 集成验证

- [x] 12.1 `pnpm build` 全量构建无报错
- [x] 12.2 端到端流程验收：筛选 → 列表 → 多选 → 加入群组 → 详情查看 → 编辑保存 → 拉黑 → 分页翻页
- [x] 12.3 空数据边界验收：无公司、无联系人、无群组、字段全 NULL 时 UI 不崩溃

---

## GSTACK REVIEW REPORT

**Reviewer**: plan-eng-review | **Date**: 2026-05-19 | **Branch**: main | **Commit**: 7338ab3

### 决策记录

| ID | 决策 | 理由 | 影响范围 |
|----|------|------|----------|
| D1 | 详情 API 扁平化响应 | 减少前端解构层级，与列表 API 风格一致 | `v3_company_detail` 返回结构 |
| D2 | filters 拆为 4 条独立查询 | 避免单条复杂查询的维护和性能风险 | `companies_filters` |
| D3 | 删除 Company 接口幽灵字段 | `score_adjusted_at`/`score_adjusted_by`/`score_adjust_reason`/`is_precise_customer` 后端不返回 | `shared-api` 类型 |
| D4 | CompanyListFilters 改 page-based | 设计文档 D6 已确定 page-based 分页 | `shared-api` 类型 |
| D5 | 仅 pytest 测 score_adjustment 校验 | 其他变更为 SELECT 扩展，curl 验证足够 | 测试策略 |
| D6 | 运行 Outside Voice (Codex) | 交叉验证发现 3 个致命/高危问题 | 审查流程 |
| D7 | 列表 API 返回双 ID (id + tc_id) | 列表返回 wc.id，操作 API 需要 tc.id，不返回会导致全部操作 404 | **致命** — `companies_page` |
| D8 | 删除迁移任务 1.1/1.2 | 迁移 `20260507_0025` 已创建 score_adjustment 列，重复执行会报错 | tasks.md 清理 |
| D9 | 后端加 grade query param | 前端筛选面板有评级筛选，但路由无此参数，筛选会静默失效 | `GET /companies` 路由 |

### Outside Voice 发现

1. **ID 语义混淆**（致命）：`companies_page` 返回 `wc.id` 作为 `id`，但 blacklist/group/PATCH 全部使用 `tc.id`。前端如用列表 `id` 调用操作 API 必定 404 → D7 修复
2. **grade 参数缺失**（高危）：前端类型定义有 `grade` 筛选，后端路由无此 param → D9 修复
3. **迁移重复**（中危）：tasks.md 1.1 要创建已存在的列 → D8 删除

### 实施优先级

| 优先级 | 任务 | 阻塞关系 |
|--------|------|----------|
| P1 | 1.x 列表 API + tc_id | 前端表格、所有操作依赖 |
| P1 | 2.x 详情 API 扁平化 | 前端 Drawer 依赖 |
| P1 | 4.1 grade 参数 | 前端筛选依赖 |
| P2 | 3.x filters 拆查询 | 前端下拉选项依赖 |
| P2 | 5.x 前端类型更新 | 前端全部组件依赖 |
| P2 | 4.2-4.4 score_adjustment | 编辑模式依赖 |

### 风险与缓解

- **ID 混用风险**：前端 `tc_id` 命名必须在所有操作调用中统一使用，代码审查重点关注
- **扁平化兼容**：确认无其他消费方依赖 `tenant_state` 嵌套结构（仅 tenant 前端使用）
- **无并行化空间**：后端→前端类型→前端组件为严格串行依赖链
