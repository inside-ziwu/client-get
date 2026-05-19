## Why

Tenant 公司列表页缺少手动新增公司的入口。目前用户只能从系统已有的 `waimaotong_clean_companies` 中挑选公司加入群组，无法录入系统中不存在的目标客户。

后端 `POST /api/v1/companies`（`TenantOpsService.create_company`）已具备基础创建能力，但只支持 7 个字段写入 `waimaotong_clean_companies`（company_name, english_name, country_iso3, domain, website, industry, product_tags）。Admin 端展示的 phone、employee_size、founded_year、full_address、description 5 个字段在创建时被忽略。

前端完全没有新增公司的 UI 组件。

## What Changes

**后端 — 扩展 create_company 写入字段（1 处 INSERT）**

`TenantOpsService.create_company` 中 INSERT INTO `waimaotong_clean_companies` 扩展 5 个字段：
- `phone`：公司电话
- `employee_size`：员工规模（文本，如 "1-10", "11-50", "51-200"）
- `founded_year`：成立年份（整数）
- `full_address`：详细地址
- `description`：公司简介

不改数据库 schema——这 5 个字段在 `waimaotong_clean_companies` 表中已存在，只是 create_company 之前没往里写。

**前端 — 公司列表页新增 Drawer 表单**

在 `/companies` 页面顶部工具栏添加「新增公司」按钮，点击后右侧滑出 Drawer，表单分三组：

- 基本信息：公司名称（必填）、英文名称、国家（选择器）、域名、网站、电话、行业、员工规模（选择器）、成立年份、地址、公司简介、产品标签（多选/输入）
- 联系人（可选）：姓名、邮箱、职位，支持添加多条
- 备注：自由文本

提交后调用 `tenantApi.companies.create(payload)`，成功后关闭 Drawer 并刷新列表。

## Decisions

### D1: UI 形式 — 侧边 Drawer

选择 Drawer 而非 Modal 或独立页面。字段较多（12+ 个基本信息字段 + 联系人），Modal 空间不够；独立页面跳转成本高且与列表页断开上下文。Drawer 在列表页旁展开，填完即回，交互最流畅。

### D2: 公司名称为唯一必填字段

与后端去重逻辑一致：`create_company` 以 domain 或 name+country 做 advisory lock 去重。最小化录入门槛，让用户先建公司再逐步补充信息。

### D3: 联系人内嵌表单，非必填

Drawer 中嵌入联系人子表单（姓名+邮箱+职位），支持添加多条。后端 `_ensure_contact_from_payload` 已支持此能力。联系人信息影响 `data_status`（有联系邮箱 → `ready`，无 → `missing_contacts`），但不强制。

### D4: 后端只扩展 INSERT 字段，不改 schema

`waimaotong_clean_companies` 表已有 phone、employee_size、founded_year、full_address、description 列（由数据采集流程写入）。create_company 只是之前没处理这些字段，现在补上即可。无需 migration。

## Non-Goals

- 不改数据库 schema，不加 migration
- 不做公司编辑功能（本次只做新增）
- 不改 admin 端代码
- 不做批量导入
- 不修改 `docs/` 下的任何文件
- 不触碰去重逻辑（advisory lock 策略不变）

## Capabilities

### New Capabilities

- `tenant-add-company-drawer`: 公司列表页新增公司 Drawer 表单（基本信息 + 联系人 + 备注）

### Modified Capabilities

- `tenant-company-create-api`: 后端 create_company 扩展写入 5 个字段（phone, employee_size, founded_year, full_address, description）

## Impact

| 层 | 影响范围 | 说明 |
|----|---------|------|
| 后端 Service | `tenant_ops_service.py` create_company | INSERT 语句扩展 5 个字段 |
| 前端页面 | `tenant/companies/page.tsx` | 添加「新增公司」按钮，引入 Drawer |
| 前端组件 | 新增 `tenant/companies/add-company-drawer.tsx` | Drawer 表单组件 |
| 前端 API | `shared-api/src/tenant/companies.ts` | create 方法 payload 类型补充（可选，当前是 `Record<string, unknown>`） |
