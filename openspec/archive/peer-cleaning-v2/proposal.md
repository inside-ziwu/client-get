## Why

codex worktree 里的同行公司清洗系统（`peer_company_cleaning_service.py`）有三个缺陷：
1. 字段合并用 COALESCE 保留首次非空值，但正确逻辑应该是「空则补全，不空则取最新采集数据」
2. 同一公司在不同关键词下可能一条有 domain 一条没有，导致 website_host 和 source_id 两个 identity 分裂为两条 peer 记录
3. 只做了公司级去重，没有联系人清洗层——`contact_count` 只是聚合数字，无法展示去重后的联系人列表

同时前端 `peers-cleaned` 页面的 API 端点（`/collection/peer-companies`）未合并到主分支，线上无表无数据。

## What Changes

- 修正清洗规则：公司字段 + 联系人字段，空则补全，非空取最新（替换 COALESCE 策略）
- 修复 identity 分裂：`derive_identity` 返回 source_id 前先查 `peer_company_sources` 是否同 source_id 已关联 peer，有则复用
- 新增联系人清洗：创建 `peer_company_contacts` 表，按 email 去重存储，关联到 peer_company
- API 对齐：移除 `/collection/peer-companies/health`，新增 `/collection/peer-companies/{id}/contacts`
- 合并 worktree 代码到主分支，执行 migration
- 前端接入清洗 API，正确展示数据

## Capabilities

### New Capabilities

- `peer-contact-cleaning`：同行公司联系人清洗层，按 email 去重后存储到 `peer_company_contacts`

### Modified Capabilities

- `admin-peer-company-cleaning`：修正清洗规则（最新覆盖 vs COALESCE）、修复 identity 分裂、移除 health 端点、新增联系人端点、前端接入

## Non-Goals

- 不改 lixiaoyun_raw_companies / lixiaoyun_raw_contacts 原始表结构
- 不改采集 worker 逻辑
- 不做跨数据源（tendata）的清洗
- 不做 Tendata stage 2 对接（后续任务）

## Impact

| 模块 | 影响 |
|---|---|
| `backend/app/services/peer_company_cleaning_service.py` | 清洗规则重写 |
| `backend/app/services/peer_company_backfill_service.py` | 适配新规则 |
| `backend/app/services/admin_collection_service.py` | 新增联系人端点、移除 health |
| `backend/app/api/admin/collection.py` | 路由变更 |
| `backend/alembic/versions/` | 新增 migration（peer_company_contacts 表） |
| `frontend/packages/shared-api/` | 类型 + API 方法更新 |
| `frontend/apps/admin/.../peers-cleaned/page.tsx` | 接入清洗 API |

依赖顺序：migration → 后端服务 → 后端路由 → 前端 API → 前端页面
