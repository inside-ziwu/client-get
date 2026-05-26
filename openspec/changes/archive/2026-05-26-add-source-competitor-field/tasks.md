## 1. 后端：查询 SQL 增加 source_competitor

- [ ] 1.1 `tenant_query_service.py` 列表查询（`companies_page`）：SQL 加 LEFT JOIN `waimaotong_raw_companies wr_raw ON wr_raw.sys_company_id = wc.sys_company_id`，SELECT 加 `wr_raw.source_competitor`，响应字典加 `"source_competitor": row["source_competitor"]`
- [ ] 1.2 `tenant_query_service.py` 详情查询：同样加 LEFT JOIN 和字段
- [ ] 1.3 本地启动后端，调用列表和详情 API 验证 `source_competitor` 字段正常返回

## 2. 前端：类型定义和 API 适配

- [ ] 2.1 `frontend/packages/shared-api/src/tenant/companies.ts` 的 Company 接口加 `source_competitor?: string`

## 3. 前端：列表页加列

- [ ] 3.1 `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx` 表格列定义加"来源同行"列，展示 `source_competitor`

## 4. 前端：详情页加字段

- [ ] 4.1 公司详情页组件加"来源同行"字段展示

## 5. 验证

- [ ] 5.1 前端 `pnpm build` 通过，无类型错误
- [ ] 5.2 用户手动验收：列表页和详情页均展示来源同行
