## Why

腾道（Tendata）数据源已废弃，Admin 端 `/collection/tendata` 页面不再有用。外贸通（Waimaotong）是当前主要数据源，但 Admin 端没有对应的展示页面。

现有 V3 API 对 waimaotong 的支持严重不完整：
- `list_v3_raw_companies()` 的 SELECT 只映射了旧的 15 列，线上实际 33 列中 18 个新字段完全未映射
- `list_v3_raw_company_contacts()` 不支持 waimaotong，直接返回空列表
- `get_v3_raw_company_debug()` 对 waimaotong 全部返回 NULL
- WHERE 中仍引用已删除的列（`country_iso3`、`trade_amount_3y_usd` 等），传参会导致 SQL 错误

## What Changes

### 前端

- **删除** `/collection/tendata` 页面（`frontend/apps/admin/src/app/(dashboard)/collection/tendata/`）
- **新增** `/collection/waimaotong` 页面
  - 列表页 11 列：公司名 | 国家 | 域名 | 行业 | 员工规模 | 成立日期 | 注册地址 | 采集关键词 | 来源同行 | 联系人数 | 入库时间
  - 筛选项 8 个：公司名(文本搜索) | 国家(下拉) | 采集关键词(下拉) | 来源同行(文本搜索) | 成立日期(年份范围) | 员工规模(区间选择) | 行业(文本搜索) | 有联系人?(布尔开关)
  - 详情 Sheet：基本信息 + 采集信息 + 联系人表格
- **侧边栏导航更新**（腾道 → 外贸通）

### 后端

- 重写 `admin_collection_service.py` 中 waimaotong 的 SQL 查询，映射线上真实 33 列
- 补充 `list_v3_raw_company_contacts()` 对 waimaotong 的支持
- 修复 `get_v3_raw_company_debug()` 对 waimaotong 的查询
- 新增筛选条件：country(text) | source_keyword | source_competitor | founded_year 范围 | employee_size 区间 | has_contacts
- 清理 tendata 相关筛选逻辑中与 waimaotong 共享分支的错误引用

### 数据库

- 补齐迁移文件：将线上直接添加的 18+5 列同步到 Alembic 迁移
- 同步 `schema.sql` 到线上真实状态

## Impact

| 影响范围 | 说明 |
|---------|------|
| 前端删除 | `frontend/apps/admin/src/app/(dashboard)/collection/tendata/`（page.tsx + client-page.tsx） |
| 前端新增 | `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/`（page.tsx + client-page.tsx） |
| 前端修改 | 侧边栏导航配置、`packages/shared-api/src/admin/collection.ts` |
| 后端修改 | `backend/app/services/admin_collection_service.py`（3 个方法重写）、`backend/app/api/admin/collection.py`（筛选参数） |
| 数据库 | 新增 Alembic revision 同步线上新列；更新 schema.sql |
| Admin API | 数据查看端点响应格式变化（新增 18 个字段） |

## Non-Goals

- 不动 lixiaoyun 相关代码和页面
- 不展示 `detail_raw_data` / `raw_data`（采集产物原始文本）
- 不展示联系人的 `mobile` / `whatsapp`（0% 填充）
- 不删除 `tendata_raw_companies` / `tendata_raw_contacts` 表（单独 change）
- 不重写采集管道
