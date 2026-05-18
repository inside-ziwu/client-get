## Why

当前采集→清洗→评分管道（collection → cleanup → scoring）计划全面重写，现阶段不再使用。这些代码引用了 `waimaotong_raw_companies` 和 `waimaotong_raw_contacts` 表上 20 个 CG 原生设计列，阻碍了数据库 schema 清理。删除管道代码后才能继续删除这些列，使数据库回归干净状态。

## What Changes

- **BREAKING**：删除采集/清洗/评分管道的全部代码（service、worker、集成层、路由、schema、测试、启动脚本）
- **BREAKING**：修改 `internal_ops_service.py`，移除对 collection_service 和 scoring_service 的依赖
- **BREAKING**：修改 `api/internal/ops.py`，移除 3 个 scoring 端点
- **BREAKING**：修改 `integrations/collection/router.py` → 实际整目录删除
- **BREAKING**：修改 `api/internal/router.py`，移除 collection 路由注册
- 保留 `admin_collection_service.py`（管理后台数据查看），但需修改其 SQL 以适配后续列删除
- 删除后，再物理删除 `waimaotong_raw_companies` 剩余 20 个 CG 原生列和 `waimaotong_raw_contacts` 剩余 5 个兼容列

## Non-Goals

- 不重写管道（后期独立 change）
- 不删除 `admin_collection_service.py`（保留管理端数据查看能力）
- 不删除 raw/clean/tenant 表本身（只删列）
- 不影响租户端查询（tenant_query_service 不受影响）
- 不影响邮件发送链路

## Capabilities

### New Capabilities

- `remove-pipeline-code`: 删除采集/清洗/评分管道的全部代码文件和 import 链
- `drop-pipeline-columns`: 删除两张 raw 表上不再被引用的 CG 原生列

### Modified Capabilities

（无现有 spec 受影响）

## Impact

| 影响范围 | 说明 |
|---------|------|
| 删除文件 | 约 25 个文件（4 service + 1 scheduler_service + 4 worker + 1 集成目录 + 2 API/schema + 5 脚本 + 8 测试） |
| 修改文件 | 约 5 个文件（internal/router.py, internal/ops.py, internal_ops_service.py, admin/router.py, admin_collection_service.py） |
| 数据库 | Alembic revision 删除 raw_companies 20 列 + raw_contacts 5 列兼容列 |
| Internal API | `/internal/api/v1/collection/*` 端点消失；scoring 3 个端点消失 |
| Admin API | 采集触发/停止/重置端点消失（随 admin/collection.py 路由移除）；数据查看端点保留 |
| Worker 进程 | collection、collection_scheduler、cleanup、scoring 4 个 Worker 不再存在 |
| 前端 | 租户端不受影响；管理端采集触发按钮失效（后端已无对应端点） |
