# Proposal · v3-data-foundation

> **范围修订（2026-05-08）**：本 change 只承载 V3 数据基础层真源，不再承载 cleanup_service、worker base、Sealos 部署、AI 回填、同行重构等实现范围。
> **审查状态（2026-05-08）**：Spec Review Passed / Ready for Implementation。该状态仅表示规格审查通过，不表示 migration / API / 前端实现已完成。

## Why

V3 需要先把“数据怎么存、关键词怎么归一、采集 run/task 怎么关联、前后端 API 怎么对齐”定成单一真源，否则后续 collection、tenant companies、email、scoring 会继续围绕旧表和旧字段发散。

本 change 解决 4 个问题：

1. **12 张核心数据表需要定稿**：关键词、励销云 raw、腾道 raw、clean 客户、租户视图层必须统一口径。
2. **旧采集关键词表不能继续当真源**：`collection_keywords / collection_task_keywords` 只作为迁移输入或兼容桥，不再驱动 V3 API / worker / 前端状态。
3. **collection_runs 需要数据层落点**：跨天采集、每日上限、停止/完成状态不能继续塞进单次 `collection_tasks`。
4. **API contract 需要与 schema 对齐**：先明确列表、详情、关键词、run/task、raw/clean 查询接口的字段来源和过滤条件。

## What Changes

### 引入 / 确认

- 12 张 V3 数据基础表：
  - `keyword_master`
  - `tenant_keyword`
  - `lixiaoyun_raw_companies`
  - `lixiaoyun_raw_contacts`
  - `tendata_raw_companies`
  - `tendata_raw_contacts`
  - `clean_companies`
  - `clean_contacts`
  - `clean_company_sources`
  - `clean_company_keywords`
  - `tenant_companies`
  - `tenant_contacts`
- 采集运行基础模型：
  - 新增 `collection_runs`
  - 调整 `collection_tasks` 增加 `run_id` 与单次执行上下文字段
- 10 个客户筛选条件的字段映射与索引策略
- 管理端 / 租户端 API contract 初稿
- 旧 `collection_keywords / collection_task_keywords` 的废弃与迁移规则

### 移除出本 change 范围

- cleanup_service 实现与 raw → clean 业务逻辑
- worker base class
- Sealos / Docker 部署
- OpenRouter AI 回填与“首次采集者付费”
- `competitor_companies` 同行重构
- `admin_collection_service` 具体查询改造
- 邮件投递、评分、群组、邮件计划业务实现

## Non-Goals

- ❌ 不实现 UC-11 fan-out worker（归 `v3-collection-pushback`）
- ❌ 不实现 cleanup_service（建议另开 `v3-cleanup-pipeline` 或并入 collection 实施 change）
- ❌ 不部署 worker / Sealos
- ❌ 不实现 AI 回填
- ❌ 不改同行 legacy / competitor 业务模型
- ❌ 不实现租户群组、邮件计划、评分调分历史

## Impact

| 维度 | 影响 |
|---|---|
| 数据库 | 是，新增/调整数据基础表与索引 |
| 后端 API | 是，定义 contract，但不在本 change 实现完整业务 |
| 前端 | 间接影响，前端按 API contract 对齐字段 |
| Worker | 只定义 run/task 数据模型，不实现 worker |
| 下游 change | `v3-collection-pushback`、tenant companies、cleanup、scoring、email 均依赖本 change |

## Scope Boundary

| 内容 | 本 change 是否包含 | 备注 |
|---|---:|---|
| 12 张 schema 表 | ✅ | 数据基础层真源 |
| `collection_runs` / `collection_tasks.run_id` | ✅ | 从 pushback 迁入 |
| API contract | ✅ | 字段与筛选口径 |
| 10 个筛选索引 | ✅ | 国家/行业/成立时间/注册资金/产品/规模/来源/金额/次数/联系人 |
| cleanup_service | ❌ | 另开实现 change |
| worker base / Sealos | ❌ | 另开部署/运行时 change |
| AI 回填 | ❌ | 另开 enrichment change |
| competitor 同行重构 | ❌ | 另开 competitor change |
