## 1. 数据库迁移同步

- [x] 1.1 创建 Alembic revision，`ADD COLUMN IF NOT EXISTS` 补齐 waimaotong_raw_companies 18 列（company_id, sys_company_id, api_company_id, company_name, country, source_type, source_keyword, source_competitor, id_verified, plan_id, full_address, website, has_detail, has_contacts, email_count, detail_raw_data, raw_data, error_msg）
- [x] 1.2 同一 revision 补齐 waimaotong_raw_contacts 5 列（sys_contact_id, contact_id, sys_company_id, api_company_id, company_id）
- [x] 1.3 更新 `backend/03_database/schema.sql`，waimaotong_raw_companies 和 waimaotong_raw_contacts 定义同步到线上真实 33+21 列

## 2. 后端 Service 层重写

- [x] 2.1 重写 `admin_collection_service.py` 的 `list_raw_companies()` 中 waimaotong 分支 SELECT，返回 company_name, country, domain, industry, employee_size, founded_year, full_address, source_keyword, source_competitor, contacts_count, created_at 等字段
- [x] 2.2 重写 `list_v3_raw_companies()` 中 waimaotong 的 SELECT，映射真实 33 列中需要展示的字段
- [x] 2.3 重写 `list_v3_raw_companies()` 中 waimaotong 的 WHERE 筛选分支，移除对已删除列的引用（country_iso3, trade_amount_3y_usd, trade_count, raw_payload），新增 country, source_keyword, source_competitor, has_contacts 筛选
- [x] 2.4 在 `list_v3_raw_company_contacts()` 的 sql_by_provider 中新增 waimaotong 分支 SQL（查 name, position, department, email, email_status, phone, linkedin, source, confidence, created_at）
- [x] 2.5 重写 `get_v3_raw_company_debug()` 中 waimaotong 分支，返回全部可展示字段（排除 detail_raw_data / raw_data）；响应改为 `dict(row)` 模式（参照 lixiaoyun debug 实现），不再使用硬编码的 payload 键

## 3. 后端 API 路由层

- [x] 3.1 `backend/app/api/admin/collection.py` V3 端点新增查询参数：source_keyword, source_competitor, has_contacts
- [x] 3.2 透传新参数到 service 层 `list_v3_raw_companies()`

## 4. 前端 shared-api 更新

- [x] 4.1 新增 `WaimaotongRawCompanyRow` TypeScript 接口（映射 V3 list 响应字段：id, company_name, country, domain, industry, employee_size, founded_year, full_address, source_keyword, source_competitor, source_type, contacts_count, email_count, has_detail, has_contacts, id_verified, website, api_company_id, created_at）
- [x] 4.2 新增 `listWaimaotongRawCompanies()` 函数，调 `GET /api/v1/raw/waimaotong/companies`，参数含 page, page_size, q, country, source_keyword, source_competitor, industry, size, year_min, year_max, has_contacts（参照 `listLixiaoyunRawCompanies` 模式）
- [x] 4.3 新增 `getWaimaotongRawCompanyDebug()` 函数，调 `GET /api/v1/raw/waimaotong/companies/{id}/debug`（参照 `getLixiaoyunRawCompanyDebug` 模式）
- [x] 4.4 新增 `listWaimaotongRawCompanyContacts()` 函数，调 `GET /api/v1/raw/waimaotong/companies/{id}/contacts`（全新，当前无任何 provider 有此前端绑定）

## 5. 前端页面

- [x] 5.1 删除 `frontend/apps/admin/src/app/(dashboard)/collection/tendata/` 目录（page.tsx + client-page.tsx）
- [x] 5.2 新建 `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/page.tsx`（SSR 预加载）
- [x] 5.3 新建 `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/client-page.tsx`（WaimaotongArchivePage）
  - 列表页 11 列：公司名 | 国家 | 域名 | 行业 | 员工规模 | 成立日期 | 注册地址 | 采集关键词 | 来源同行 | 联系人数 | 入库时间
  - 筛选区 8 项：公司名(文本) | 国家(下拉) | 采集关键词(下拉) | 来源同行(文本) | 成立日期(年份范围) | 员工规模(区间) | 行业(文本) | 有联系人?(开关)
  - 详情 Sheet：基本信息区 + 采集信息区 + 联系人表格（name, position, department, email, email_status, phone, linkedin, source）
- [x] 5.4 侧边栏导航更新：腾道 → 外贸通，路由 `/collection/tendata` → `/collection/waimaotong`

## 6. 验证

- [x] 6.1 后端启动验证：`python -c "from app.main import create_app; create_app()"`
- [x] 6.2 前端构建验证：`cd frontend && pnpm build --filter admin`
- [x] 6.3 新增 V3 waimaotong list 合约测试：验证路由参数透传（source_keyword, source_competitor, has_contacts）和响应格式，复用 `test_admin_collection_extras.py` 的 AsyncMock 模式
- [x] 6.4 新增 V3 waimaotong debug 合约测试：验证 dict(row) 响应格式，无硬编码 payload 键
- [x] 6.5 新增 V3 waimaotong contacts 合约测试：验证联系人列表响应格式
- [x] 6.6 手工验收：访问 `/collection/waimaotong`，确认列表加载、筛选、详情 Sheet、联系人展示正常
- [x] 6.7 确认 `/collection/tendata` 路由已不可访问
