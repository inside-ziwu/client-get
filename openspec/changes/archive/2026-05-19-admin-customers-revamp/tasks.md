## 1. 后端 Service 层

- [ ] 1.1 在 `backend/app/services/admin_collection_service.py` 中新增 `list_wmt_clean_companies` 方法：SELECT 基础+AI 字段，支持 q/country/industry/size/year_min/year_max/has_contacts/grade 筛选，分页+排序（created_at DESC）
- [ ] 1.2 在 `backend/app/services/admin_collection_service.py` 中新增 `get_wmt_clean_company` 方法：SELECT 全量字段（含 JSONB：score_details/match_reasons/potential_needs/recommended_products/risk_factors/main_business/trade_summary 等），按 id 查询，不存在抛 404
- [ ] 1.3 在 `backend/app/services/admin_collection_service.py` 中新增 `list_wmt_clean_company_contacts` 方法：通过 subquery 获取 sys_company_id，查询 `waimaotong_clean_contacts`，按 created_at ASC 排序

## 2. 后端 API 路由

- [ ] 2.1 在 `backend/app/api/admin/collection.py` 中新增 `GET /collection/wmt-clean-companies` 路由，接收筛选参数，调用 service 层 `list_wmt_clean_companies`，返回 `paginated_response`
- [ ] 2.2 在 `backend/app/api/admin/collection.py` 中新增 `GET /collection/wmt-clean-companies/{company_id}` 路由，调用 `get_wmt_clean_company`，返回 `success_response`
- [ ] 2.3 在 `backend/app/api/admin/collection.py` 中新增 `GET /collection/wmt-clean-companies/{company_id}/contacts` 路由，调用 `list_wmt_clean_company_contacts`，返回 `paginated_response`

## 3. 前端 shared-api 层

- [ ] 3.1 在 `frontend/packages/shared-api/src/admin/collection.ts` 中新增 `WmtCleanCompanyRow` 类型定义（列表字段，AI 字段均为 `| null`）
- [ ] 3.2 在同文件新增 `WmtCleanCompanyDetail` 类型定义（详情全量字段，含 JSONB 类型）
- [ ] 3.3 在同文件新增 `WmtCleanContactRow` 类型定义
- [ ] 3.4 在 `collectionApi` 中新增 3 个方法：`listWmtCleanCompanies`、`getWmtCleanCompany`、`listWmtCleanCompanyContacts`
- [ ] 3.5 在 `frontend/packages/shared-api/src/index.ts` 中导出新类型

## 4. 前端页面改造

- [ ] 4.1 改造 `frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx`：删除健康卡片（healthQuery + 4 个 Card）、删除 `CleanCompanyRow` 内联类型、删除 `RangeField` 组件（后续在筛选区内联重写）
- [ ] 4.2 实现筛选区：公司名/域名搜索框、国家输入、行业输入、员工规模下拉（tiny/small/medium/large）、成立年份范围（min/max）、有联系人 Checkbox、查询/重置按钮
- [ ] 4.3 实现表格：13 列（公司名可点击、评级 Badge 颜色编码、AI 字段 null 显示 `-`），水平滚动，min-width 适配
- [ ] 4.4 实现分页控件：总条数、上一页/下一页、当前页/总页、每页条数选择（20/50/100）
- [ ] 4.5 实现详情 Sheet：分组 1 基本信息（始终显示）、分组 2 AI 评估（条件显示）、分组 3 贸易数据（条件显示）、分组 4 联系人表格（独立 API 加载）、分组 5 数据来源元数据
- [ ] 4.6 更新页面标题和描述文案（从"客户采集归档"改为"外贸通客户数据"或其他合适名称）

## 5. 验证

- [ ] 5.1 后端启动验证：`cd backend && python -m app.main`，访问 `/docs` 确认 3 个新端点存在，手动调用列表/详情/联系人端点返回正确数据
- [ ] 5.2 前端构建验证：`cd frontend && pnpm build --filter admin`，确保无 TypeScript 编译错误
- [ ] 5.3 前端运行验证：启动 admin dev server，访问 `/collection/customers` 页面，验证列表加载、筛选、分页、详情 Sheet、联系人表格均正常
- [ ] 5.4 边界验证：AI 字段为 null 时表格显示 `-`、详情 Sheet 不显示 AI 分组和贸易分组；空数据时表格显示空状态
