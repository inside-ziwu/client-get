---
title: "feat: Admin 端新增外贸通数据展示页面"
status: active
type: feat
origin: openspec/changes/admin-waimaotong-display/
created: 2026-05-19
depth: standard
tags: [admin, waimaotong, collection, frontend, backend, migration]
---

# feat: Admin 端新增外贸通数据展示页面

## 问题框架

外贸通（waimaotong）是当前主要数据源，但 Admin 端缺少对应的数据展示页面。线上 `waimaotong_raw_companies` 表已有 33 列（18 列由线上直接添加，未在 Alembic 迁移中），`waimaotong_raw_contacts` 有 21 列（5 列线上直接添加）。现有 V3 API 的 waimaotong SQL 只覆盖旧的 15 列，导致查询返回大量 NULL。同时腾道（tendata）已废弃，需移除其页面。

## 范围

**包含：**
- Alembic 迁移补齐 18+5 列
- schema.sql 同步到线上 33+21 列
- 后端 service 层重写 waimaotong 的 list/debug/contacts 三个 SQL 查询
- API 路由层新增 3 个筛选参数
- 前端 shared-api 新增 V3 绑定（type + 3 个函数）
- 新建 `/collection/waimaotong` 页面（列表 + 筛选 + 详情 Sheet + 联系人）
- 删除 `/collection/tendata` 页面，更新侧边栏

**不包含：**
- 不动 lixiaoyun 相关代码
- 不展示 detail_raw_data / raw_data / mobile / whatsapp
- 不删 tendata 数据库表
- 不重写采集管道

## 关键设计决策

| 决策 | 选项 | 理由 | 来源 |
|------|------|------|------|
| D1: 复用 V3 API 架构 | 重写 waimaotong SQL 分支，不新建端点 | 端点路径、分页、权限已就绪 | (see origin: design.md D1) |
| D2: 前端参照 peers 页面结构 | 列表 + 筛选 + Sheet 详情 | 交互模式一致，降低认知成本 | (see origin: design.md D2) |
| D3: 国家字段用 text | `country`（英文全称），不用 `country_iso3` | 100% 填充，iso3 已被 0043 迁移删除 | (see origin: design.md D3) |
| D4: debug 响应用 dict(row) | 不再硬编码 payload 键 | 参照 lixiaoyun 实现，避免 KeyError | (see origin: tasks.md 2.5) |
| D5: 只用 company_name | 不做 COALESCE(company_name, name) 回退 | 信任数据管道 | (see origin: eng-review D5) |
| D6: 稳定排序 | ORDER BY created_at DESC, id DESC | 避免分页重复/遗漏 | (see origin: eng-review D6) |

## 实施单元

### IU-1: 数据库迁移同步

**目标：** 让 Alembic 迁移追平线上状态，补齐 18+5 列。

**文件：**
- `backend/alembic/versions/20260519_0044_sync_waimaotong_columns.py`（新建）
- `backend/03_database/schema.sql`（修改）

**实施要点：**
- 新建 revision 0044，使用 `ADD COLUMN IF NOT EXISTS` 补齐 waimaotong_raw_companies 18 列和 waimaotong_raw_contacts 5 列
- upgrade 必须是幂等的（线上已有这些列，跑迁移不报错）
- downgrade 使用 `DROP COLUMN IF EXISTS`
- schema.sql 中 waimaotong_raw_companies 定义同步到 33 列，waimaotong_raw_contacts 同步到 21 列

**参照模式：**
- `backend/alembic/versions/20260518_0043_drop_pipeline_columns.py` — 最近的迁移文件，参照命名和结构
- 列定义参照 design.md 中"线上真实表结构"章节

**依赖：** 无

**测试场景：**
1. 迁移脚本对已有列的表跑 upgrade 不报错（幂等验证）
2. downgrade 后 upgrade 可重复执行
3. schema.sql 中列定义与 design.md 一致

---

### IU-2: 后端 Service 层重写

**目标：** 重写 `admin_collection_service.py` 中 waimaotong 的 3 个 SQL 查询分支。

**文件：**
- `backend/app/services/admin_collection_service.py`（修改）

**实施要点：**

**2a — list_v3_raw_companies() 的 waimaotong SELECT 分支（约 L1277-1292）**
```
替换现有 NULL placeholder SELECT 为 design.md 中的 19 字段 SELECT。
ORDER BY c.created_at DESC, c.id DESC LIMIT :limit OFFSET :offset
```

**2b — list_v3_raw_companies() 的 waimaotong WHERE 分支（约 L1180-1242）**
```
新建独立 waimaotong 分支（当前与 tendata 共享），不引用已删除列
（country_iso3, trade_amount_3y_usd, trade_count, raw_payload）。
新增 8 个筛选条件，详见 design.md WHERE 筛选表。
```

**2c — list_v3_raw_company_contacts() 新增 waimaotong 分支**
```
在 sql_by_provider 字典中新增 "waimaotong" 键，
查询 13 列（不含 mobile/whatsapp），WHERE raw_company_id = :raw_company_id
ORDER BY created_at ASC, id ASC
```

**2d — get_v3_raw_company_debug() 重写 waimaotong 分支（约 L860-921）**
```
替换当前全 NULL 查询为 design.md 中 24 字段 SELECT（排除 detail_raw_data/raw_data）。
响应改为 dict(row) 模式，不再硬编码 payload 键。
```

**2e — list_raw_companies() 的 waimaotong 分支（V1, 约 L637-642）**
```
可选：更新 SELECT 字段（company_name, country 等），
使 V1 也能返回有意义数据，作为 fallback。
优先级最低，V3 页面完成后可跳过。
```

**参照模式：**
- `lixiaoyun` 分支的 SELECT/WHERE 实现 — 同文件中即有完整范例
- `lixiaoyun` 的 debug 查询使用 `dict(row)` 模式 — 参照其 response 构建方式
- `employee_size` 区间筛选复用现有 `NULLIF(substring(...from '(\d+)'))::int` 正则模式

**依赖：** IU-1（迁移补齐列后 SQL 才能查到数据）

**测试场景：**
1. list：返回 19 个字段，无 NULL placeholder
2. list + q 筛选：company_name ILIKE 和 domain ILIKE 模糊搜索
3. list + country 筛选：精确匹配 country 文本
4. list + source_keyword 筛选：精确匹配
5. list + source_competitor 筛选：ILIKE 模糊搜索
6. list + year_min/year_max 筛选：founded_year 范围过滤
7. list + employee_size 筛选：正则提取数字做区间比较
8. list + has_contacts 筛选：布尔过滤
9. list 分页：ORDER BY created_at DESC, id DESC 保证稳定排序
10. contacts：返回 13 列，按 raw_company_id 过滤
11. contacts：公司无联系人时返回空列表
12. debug：返回 24 字段 dict，不含 detail_raw_data/raw_data
13. debug：不存在的 id 返回 404 或 None

**测试文件：** `backend/tests/test_admin_collection_waimaotong_v3.py`（新建）

---

### IU-3: 后端 API 路由层

**目标：** V3 端点新增 3 个查询参数，透传到 service 层。

**文件：**
- `backend/app/api/admin/collection.py`（修改）

**实施要点：**
- `list_v3_raw_companies` 端点函数签名新增：
  - `source_keyword: str | None = Query(None)`
  - `source_competitor: str | None = Query(None)`
  - `has_contacts: bool | None = Query(None)`
- 这三个参数透传给 `AdminCollectionService.list_v3_raw_companies()` 调用
- service 函数签名也需同步新增这三个参数

**参照模式：**
- 同文件中已有 `country`, `industry`, `year_min`, `year_max` 等参数的声明方式 — 保持一致

**依赖：** IU-2（service 层接收参数后才有意义）

**测试场景：**
1. GET /raw/waimaotong/companies?source_keyword=电路 → 参数正确透传到 service
2. GET /raw/waimaotong/companies?has_contacts=true → 布尔参数正确解析和透传
3. GET /raw/waimaotong/companies?source_competitor=xxx → 文本参数正确透传

**测试文件：** `backend/tests/test_admin_collection_waimaotong_v3.py`（与 IU-2 共用）

---

### IU-4: 前端 shared-api 更新

**目标：** 新增 waimaotong V3 API 绑定，供新页面调用。

**文件：**
- `frontend/packages/shared-api/src/admin/collection.ts`（修改）

**实施要点：**

**4a — 新增 WaimaotongRawCompanyRow 接口**
```typescript
interface WaimaotongRawCompanyRow {
  id: string;
  company_name: string | null;
  country: string | null;
  domain: string | null;
  industry: string | null;
  employee_size: string | null;
  founded_year: string | null;
  full_address: string | null;
  source_keyword: string | null;
  source_competitor: string | null;
  source_type: string | null;
  contacts_count: number | null;
  email_count: number | null;
  has_detail: boolean | null;
  has_contacts: boolean | null;
  id_verified: boolean | null;
  website: string | null;
  api_company_id: string | null;
  created_at: string;
}
```

**4b — 新增 listWaimaotongRawCompanies() 函数**
```
参数：page, page_size, q, country, source_keyword, source_competitor,
      industry, size, year_min, year_max, has_contacts
调用：GET /api/v1/raw/waimaotong/companies
返回：PaginatedResponse<WaimaotongRawCompanyRow>
```

**4c — 新增 getWaimaotongRawCompanyDebug() 函数**
```
参数：rawCompanyId: string
调用：GET /api/v1/raw/waimaotong/companies/{id}/debug
返回：ApiResponse<Record<string, unknown>>（dict 格式，不固定键）
```

**4d — 新增 listWaimaotongRawCompanyContacts() 函数**
```
参数：rawCompanyId: string
调用：GET /api/v1/raw/waimaotong/companies/{id}/contacts
返回：PaginatedResponse<WaimaotongRawContactRow>
需同时定义 WaimaotongRawContactRow 接口
```

**参照模式：**
- `listLixiaoyunRawCompanies` / `getLixiaoyunRawCompanyDebug` 的函数签名和调用方式 — 同文件
- `LixiaoyunRawCompanyRow` 的类型定义风格

**依赖：** IU-3（API 端点就绪后绑定才有意义）

**测试场景：**
1. TypeScript 编译通过，无类型错误
2. 函数签名与 API 端点参数一致

---

### IU-5: 前端页面

**目标：** 新建外贸通数据展示页面，删除腾道页面，更新导航。

**文件：**
- `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/page.tsx`（新建）
- `frontend/apps/admin/src/app/(dashboard)/collection/waimaotong/client-page.tsx`（新建）
- `frontend/apps/admin/src/app/(dashboard)/collection/tendata/`（删除整个目录）
- `frontend/apps/admin/src/components/layout/sidebar.tsx`（修改）

**实施要点：**

**5a — page.tsx（SSR 预加载）**
- 参照 tendata/page.tsx 结构
- 预加载 waimaotong V3 companies 列表

**5b — client-page.tsx（WaimaotongArchivePage）**

列表页 11 列：
| 列 | 字段 | 说明 |
|---|---|---|
| 公司名 | company_name | |
| 国家 | country | |
| 域名 | domain | 纯域名 |
| 行业 | industry | |
| 员工规模 | employee_size | |
| 成立日期 | founded_year | 仅年份 |
| 注册地址 | full_address | 当前 0% 填充 |
| 采集关键词 | source_keyword | |
| 来源同行 | source_competitor | |
| 联系人数 | contacts_count | |
| 入库时间 | created_at | |

筛选区 8 项：
| 筛选项 | 类型 | 控件 |
|---|---|---|
| 公司名 | 文本 | Input |
| 国家 | 下拉 | Select (27 值) |
| 采集关键词 | 下拉 | Select |
| 来源同行 | 文本 | Input |
| 成立日期 | 年份范围 | 两个 Input (min/max) |
| 员工规模 | 区间 | Select (tiny/small/medium/large) |
| 行业 | 文本 | Input |
| 有联系人？ | 布尔 | Checkbox |

详情 Sheet：
- 基本信息区（10 字段）：company_name, country, website（可点击链接）, industry, phone, employee_size, founded_year, description, full_address, products（tag 列表）
- 采集信息区（5 字段）：source_keyword, source_competitor, source_type, id_verified, api_company_id
- 联系人表格（8 列）：name, position, department, email, email_status, phone, linkedin, source
- 联系人为空时展示空状态提示

**5c — 删除 tendata 目录**
- 删除 `frontend/apps/admin/src/app/(dashboard)/collection/tendata/page.tsx`
- 删除 `frontend/apps/admin/src/app/(dashboard)/collection/tendata/client-page.tsx`

**5d — 侧边栏更新**
- `sidebar.tsx` 约 L37：`{ href: '/collection/tendata', label: '腾道数据', icon: Server }` → `{ href: '/collection/waimaotong', label: '外贸通', icon: Server }`

**参照模式：**
- `peers/client-page.tsx`（464 行）— 最完整的参照：有 V3 API 绑定、筛选区、detail Sheet、分页
  - 状态管理：filters + appliedFilters + page + pageSize + selected
  - 查询：useQuery with queryKey 包含 page/pageSize/appliedFilters
  - detail Sheet：getLixiaoyunRawCompanyDebug 查询 + Sheet 组件 + DescriptionGrid
  - 分页：PAGE_SIZE_OPTIONS + jumpPage + maxPage 计算
- `tendata/client-page.tsx`（259 行）— 结构更简，无 detail Sheet debug 查询，可对照列表和筛选区

**依赖：** IU-4（shared-api 绑定就绪后页面才能调用）

**测试场景：**
1. `/collection/waimaotong` 列表正确加载并展示 11 列
2. 8 项筛选各自生效，可组合使用
3. 分页翻页不重复不遗漏
4. 点击公司行打开详情 Sheet，展示基本信息 + 采集信息
5. 详情 Sheet 联系人表格正确加载 8 列
6. 联系人为空时显示空状态
7. company_name 为 NULL 的旧数据显示 "-" 或空
8. `/collection/tendata` 返回 404
9. 侧边栏显示"外贸通"，无"腾道"
10. `pnpm build --filter admin` 编译通过

---

### IU-6: 验证

**目标：** 确认全栈变更无回归，所有 spec 验收通过。

**文件：**
- `backend/tests/test_admin_collection_waimaotong_v3.py`（IU-2/3 中创建）

**实施要点：**

**6a — 后端启动验证**
```bash
python -c "from app.main import create_app; create_app()"
```

**6b — 前端构建验证**
```bash
cd frontend && pnpm build --filter admin
```

**6c — V3 list 合约测试**
- AsyncMock service 层，验证路由参数透传（source_keyword, source_competitor, has_contacts）
- 验证响应格式包含 19 字段

**6d — V3 debug 合约测试**
- AsyncMock service 层，验证 dict(row) 响应格式，无硬编码 payload 键

**6e — V3 contacts 合约测试**
- AsyncMock service 层，验证联系人列表响应格式

**6f — 手工验收**
- 访问 `/collection/waimaotong`，确认列表加载、筛选、详情 Sheet、联系人展示
- 确认 `/collection/tendata` 路由不可访问

**参照模式：**
- `backend/tests/test_admin_collection_extras.py` — AsyncMock + httpx AsyncClient 模式

**依赖：** IU-1 ~ IU-5 全部完成

## 执行顺序

```
IU-1 (迁移)
  │
  ▼
IU-2 (Service SQL) ──► IU-3 (API 路由)
                            │
                            ▼
                       IU-4 (shared-api)
                            │
                            ▼
                       IU-5 (前端页面)
                            │
                            ▼
                       IU-6 (验证)
```

线性依赖链。IU-2 和 IU-3 可在同一轮完成（都是后端修改）。IU-4 和 IU-5 也可合并为一轮（都是前端修改）。

**建议实施批次：**
1. **批次 A（后端）**：IU-1 → IU-2 + IU-3 → 后端启动验证
2. **批次 B（前端）**：IU-4 + IU-5 → 前端构建验证
3. **批次 C（测试）**：IU-6 合约测试 → 手工验收

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 迁移 0044 与线上列名/类型不完全一致 | upgrade 报错 | 实施前查询 `information_schema.columns` 确认线上真实类型 |
| tendata/waimaotong 共享 WHERE 分支拆分遗漏 | waimaotong 筛选报错 | 拆分后逐条测试 8 个筛选条件 |
| employee_size 格式多样（"10"/"1-20"/"50人"/"Over 400"） | 区间筛选有损 | 复用现有正则，接受有损匹配 |
| lixiaoyun 代码意外受影响 | peers 页面回归 | 只改 waimaotong 分支，lixiaoyun 独立分支不动；回归跑 peers 页面 |
| company_name NULL 的旧数据 | 列表显示空 | 前端 dash() 函数处理 NULL → "-" |

## Spec 验收映射

| Spec | 对应 IU | 验收方式 |
|------|--------|---------|
| WMT-LIST-01 (11 列展示) | IU-2a + IU-5b | 手工 + 构建 |
| WMT-LIST-02 (8 项筛选) | IU-2b + IU-3 + IU-5b | 合约测试 + 手工 |
| WMT-LIST-03 (分页) | IU-2a + IU-5b | 手工 |
| WMT-DETAIL-01 (基本信息) | IU-2d + IU-5b | 手工 |
| WMT-DETAIL-02 (采集信息) | IU-2d + IU-5b | 手工 |
| WMT-DETAIL-03 (联系人表格) | IU-2c + IU-5b | 合约测试 + 手工 |
| WMT-DETAIL-04 (联系人空状态) | IU-5b | 手工 |
| RM-TENDATA-01 (侧边栏) | IU-5d | 手工 |
| RM-TENDATA-02 (路由不可访问) | IU-5c | 手工 |
| RM-TENDATA-03 (分支独立) | IU-2b | 合约测试 |
