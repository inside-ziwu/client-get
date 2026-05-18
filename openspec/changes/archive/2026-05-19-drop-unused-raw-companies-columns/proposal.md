## Why

`waimaotong_raw_companies` 表有 66 列，其中 13 列（后加的新业务扩展列）在整个后端代码中零引用；`waimaotong_raw_contacts` 表有 29 列，其中 8 列（后加的新业务扩展列）同样零引用——没有写入、没有查询、没有过滤。这些列是预留设计但从未启用，增加了表的认知负担和维护成本。趁当前无代码依赖，尽早物理删除。

## What Changes

- **BREAKING**：物理删除 `waimaotong_raw_companies` 表上 13 个未使用列：
  - `country_name` (text)
  - `country_code` (text)
  - `logo` (text)
  - `origin` (text)
  - `social_medias` (jsonb)
  - `tags` (text[])
  - `revenue` (text)
  - `founded_date` (text)
  - `legal_name` (text)
  - `company_type` (text)
  - `sic_codes` (jsonb)
  - `naics_codes` (jsonb)
  - `website_url` (text)
- **BREAKING**：物理删除 `waimaotong_raw_contacts` 表上 8 个未使用列：
  - `job_title` (text)
  - `country` (text)
  - `region` (text)
  - `score` (integer)
  - `emails` (text[])
  - `linkedin_url` (text)
  - `twitter_url` (text)
  - `facebook_url` (text)

## Non-Goals

- 不删除原生设计列（0035 迁移的列），这些有大量业务代码引用
- 不删除兼容原项目的列，这些承载历史数据迁移
- 不做表结构重构或重命名，仅做列裁剪
- 不涉及前端、worker 的变更

## Capabilities

### New Capabilities

- `drop-unused-columns`: 通过 Alembic 迁移物理删除 waimaotong_raw_companies 表 13 列 + waimaotong_raw_contacts 表 8 列（共 21 列未使用列）

### Modified Capabilities

（无，这些列无代码引用，删除不影响任何现有能力）

## Impact

| 影响范围 | 说明 |
|---------|------|
| 数据库 | `waimaotong_raw_companies` 减 13 列（66→53）；`waimaotong_raw_contacts` 减 8 列（29→21）；单个 Alembic revision |
| 迁移策略 | 单个 Alembic revision，upgrade 删 21 列 + downgrade 加回 21 列（含类型和默认值） |
| 后端代码 | 无影响（21 列在 `backend/` Python 代码中零引用，已通过全量 grep 验证；INSERT SQL 不涉及这些列） |
| 前端 | 无影响 |
| Worker | 无影响 |
| 线上数据 | 这 21 列如有数据将被永久丢弃；需在执行前确认线上这些列是否有非空数据 |
