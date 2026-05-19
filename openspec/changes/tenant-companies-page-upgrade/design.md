## Context

Tenant 公司列表页在迁移 `20260519_0045` 后已切到 `waimaotong_clean_companies` 数据源，但 UI 仍停留在 MVP 状态（~70 行）。admin 端的 `CustomerArchivePage`（`collection/customers/client-page.tsx`）已实现了 wmt 数据的完整展示，可作为参考。

当前后端 `TenantQueryService.companies_page` 和 `v3_company_detail` 的 SQL 已查 wmt 表，但返回字典中缺少多个 wmt 字段。`TenantOpsService.companies_filters` 仅返回 3 个 options。前端 `Company` 类型与后端响应存在字段名不一致。

## Goals / Non-Goals

**Goals:**
- 后端 API 响应字段与 wmt 表对齐，让前端能获取 AI 评估、贸易数据等完整信息
- 前端公司列表页按 mock 设计全面升级：筛选、表格、分页、详情、群组、拉黑
- 保持与现有 API 参数的向后兼容

**Non-Goals:**
- 不引入"精准客户"状态概念
- 不做移动端适配
- 不修改 admin 端代码
- 不新增 API 路由（复用现有路由，仅扩展响应和请求字段）

## Decisions

### D1: 后端字段扩展策略 — 直接扩展现有 service 方法

在 `companies_page` 和 `v3_company_detail` 的 SQL SELECT 中补充缺失字段，在返回字典中新增对应 key。不新建 API 路由。

**理由**: 路由层参数不变（用户确认），只需 service 层的 SQL 和映射逻辑调整。新建路由会增加维护成本。

### D2: score_adjustment 存储 — tenant_companies 表新增列

在 `tenant_companies` 表新增 `score_adjustment smallint DEFAULT 0`，取值范围 -20 ~ +20。通过 `PATCH /prospects/{id}` 更新。

**替代方案**: 存到独立的 score_adjustments 表 → 过度设计，单列即可。

### D3: filters API options 扩展 — DISTINCT 查询

`companies_filters` 新增 3 个 DISTINCT 查询：
- `sub_industries`: `SELECT DISTINCT sub_industry FROM waimaotong_clean_companies wc JOIN tenant_companies tc ...`
- `product_tags`: `SELECT DISTINCT unnest(product_tags) FROM waimaotong_clean_companies wc JOIN tenant_companies tc ...`
- `grades`: `SELECT DISTINCT grade FROM waimaotong_clean_companies wc JOIN tenant_companies tc ...`

**理由**: 数据量在租户级别有限，DISTINCT 查询性能可接受。无需缓存或预计算。

### D4: 前端页面架构 — 单文件 + 局部组件抽取

主页面 `companies/page.tsx` 保持单文件，将 Drawer、GroupModal、BlacklistModal 抽取为同目录下的独立组件文件。

```
companies/
  page.tsx              # 主页面（筛选 + 表格 + 分页 + 状态管理）
  company-detail.tsx    # 详情 Drawer
  group-modal.tsx       # 加入群组 Modal
  blacklist-modal.tsx   # 拉黑确认 Modal
```

**理由**: 页面逻辑量大（~500+ 行），全塞一个文件可读性差。但也不需要过度组件化，同目录平铺即可。

### D5: 分页模式 — 页码分页

使用 `page` + `page_size` 参数（后端已支持），弃用 cursor 分页。前端分页 UI 参考 admin 的 `CustomerArchivePage` 实现模式（上一页/下一页/跳页/每页条数选择）。

### D6: 详情 Drawer 编辑模式 — 读写切换

默认只读态，点击"编辑"按钮进入编辑态（标签/备注/评分调整）。保存时调用 `PATCH /prospects/{id}`，成功后退出编辑态并刷新数据。

**理由**: 与 mock 设计一致。避免误操作。

### D7: 前端类型对齐 — 更新 shared-api Company 接口

更新 `frontend/packages/shared-api/src/tenant/companies.ts` 的 `Company` 接口，字段名与后端响应 key 保持一致（如 `country_iso3` 而非 `country`，`score` 而非 `total_score`）。同步更新 `CompanyListFilters`。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| filters DISTINCT 查询在大租户下可能变慢 | 租户级数据量有限（通常 < 10k 公司），DISTINCT 性能可接受；若未来出现瓶颈可加缓存 |
| wmt 表 AI 字段（score_details 等）可能为 NULL | 前端统一用 dash('-') 处理空值，参考 admin 的 `dash()` 函数 |
| score_adjustment 列迁移 | 仅 ADD COLUMN + DEFAULT，无锁表风险 |
| 页面代码量大 | 通过组件拆分控制单文件复杂度 |

## Migration Plan

1. **Alembic 迁移**: `ALTER TABLE tenant_companies ADD COLUMN score_adjustment smallint DEFAULT 0`
2. **后端 service 更新**: 扩展 SQL 和返回字典（向后兼容，只新增字段不删除）
3. **前端类型更新**: 更新 `Company` 接口
4. **前端页面重写**: 替换 `companies/page.tsx`，新增组件文件
5. **部署**: 先部署后端（含迁移），再部署前端

回滚策略: 前端回退到旧版 page.tsx 即可，后端新增字段不影响旧前端。
