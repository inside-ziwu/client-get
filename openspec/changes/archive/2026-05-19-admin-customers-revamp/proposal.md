## Why

Admin 端 `/collection/customers` 页面当前查询 `clean_companies` 表，仅展示 7 列基础字段和 4 字段简陋详情。线上数据库已存在 `waimaotong_clean_companies`（70 列，含 AI 分析字段预留）和 `waimaotong_clean_contacts`（6335 条），但 admin 后端没有查询这两张表的 API，前端也没有对应的展示能力。

外部仓库 [sysdev-ft-marketing](https://github.com/aoqi-ai/sysdev-ft-marketing) 已有完整的公司列表 + 详情页实现（React + Ant Design），需要将其交互模式一比一复刻到 admin 端，数据源切换为 `waimaotong_clean_companies`。

## What Changes

### 后端

- **新增** 3 个 admin API 端点查询 `waimaotong_clean_companies` / `waimaotong_clean_contacts`：
  - `GET /collection/wmt-clean-companies` — 列表 + 筛选 + 分页
  - `GET /collection/wmt-clean-companies/{id}` — 公司详情
  - `GET /collection/wmt-clean-companies/{id}/contacts` — 公司联系人
- **新增** `admin_collection_service.py` 中对应的 3 个查询方法
- 旧的 `GET /collection/clean-companies` 端点和 `list_clean_companies` 方法 **保留不动**

### 前端

- **改造** `/collection/customers/client-page.tsx`：
  - **删除** 健康卡片（`cleanup-health` API 调用及 4 个统计卡片）
  - **替换** 数据源：`adminApi.collection.listCleanCompanies` → 新 API
  - **扩展** 筛选区：公司名/域名搜索、国家、行业、员工规模、成立年份范围、有联系人开关
  - **扩展** 表格列至 ~14 列（基础字段 + AI 预留列）
  - **重写** 详情 Sheet：多分组展示（基本信息 / AI 评估 / 贸易数据 / 联系人表格 / 数据来源）
- **新增** `shared-api` 中对应的 API 调用方法和类型定义
- 侧边栏路由和菜单 **不变**（复用现有 `/collection/customers` 路径）

## Capabilities

### New Capabilities

- `wmt-clean-list`: 外贸通清洗公司列表展示——多维筛选、分页、表格列配置（含 AI 字段预留）
- `wmt-clean-detail`: 外贸通清洗公司详情——多分组 Sheet 展示 + 联系人表格

### Modified Capabilities

（无现有 spec 需要修改）

## Impact

| 影响范围 | 说明 |
|---------|------|
| 前端修改 | `frontend/apps/admin/src/app/(dashboard)/collection/customers/client-page.tsx`（重写） |
| 前端新增 | `frontend/packages/shared-api/src/admin/collection.ts`（新增 3 个 API 方法 + 类型） |
| 后端修改 | `backend/app/api/admin/collection.py`（新增 3 个路由） |
| 后端修改 | `backend/app/services/admin_collection_service.py`（新增 3 个查询方法） |
| 数据库 | **无迁移**——`waimaotong_clean_companies` 和 `waimaotong_clean_contacts` 已存在于线上 |
| 现有 API | `GET /collection/clean-companies` 保留不动，不影响其他消费方 |

## Non-Goals

- 不删除 `clean_companies` / `clean_contacts` 表及其 API
- 不新增 Alembic 迁移（表已存在）
- 不运行 AI Flow（AI 字段当前为空，页面预留展示位，数据填充由独立流程完成）
- 不改动侧边栏路由结构（继续使用 `/collection/customers` 路径）
- 不修改 tenant 端的公司展示逻辑
- 不处理 `admin-waimaotong-display` change（外贸通原始数据页面，独立 change）
