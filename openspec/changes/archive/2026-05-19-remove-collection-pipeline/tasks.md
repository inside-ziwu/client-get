## 1. 删除管道代码文件

- [x] 1.1 删除 Service 层：`collection_service.py`、`cleanup_service.py`、`scoring_service.py`、`collection_scheduler_service.py`
- [x] 1.2 删除集成目录：`integrations/collection/` 整个目录（waimaotong.py、lixiaoyun.py、tendata.py、base.py、router.py、__init__.py）
- [x] 1.3 删除 Worker：`workers/collection.py`、`workers/collection_scheduler.py`、`workers/cleanup.py`、`workers/scoring.py`
- [x] 1.4 删除 API/Schema：`api/internal/collection.py`、`schemas/internal_collection.py`
- [x] 1.5 删除启动脚本：`scripts/run_collection_worker.py`、`scripts/run_collection_scheduler_worker.py`、`scripts/run_collection_scheduler.py`、`scripts/run_cleanup_worker.py`、`scripts/run_scoring_worker.py`

## 2. 修复 import 链

- [x] 2.1 修改 `api/internal/router.py`：移除 collection_router 注册
- [x] 2.2 修改 `api/internal/ops.py`：移除 3 个 scoring 端点（trigger_scoring、claim_scoring_jobs、submit_scoring_result）
- [x] 2.3 修改 `services/internal_ops_service.py`：移除 collection_service、scoring_service 的 import 和相关方法，保留邮件/凭证/竞对等方法

## 3. 删除相关测试文件

- [x] 3.1 查找并删除所有直接 import 被删模块的测试文件（12 个文件）

## 4. 验证 FastAPI 启动

- [x] 4.1 执行 `python -c "from app.main import create_app; create_app()"`，确认无 ImportError ✓
- [x] 4.2 在 `backend/app/` 中 grep 被删模块名，确认无悬空 import ✓

## 5. 修改 admin_collection_service.py 的 SQL

- [x] 5.1 分析 `admin_collection_service.py` 中引用即将删除的 20+5 列的 SQL 语句（4 处）
- [x] 5.2 修改 `list_v3_raw_companies()` 等函数，替换被删列为 NULL 占位（4 处修改）

## 6. 线上数据确认

- [x] 6.1 查询线上 `waimaotong_raw_companies` 20 列的非空行数（最多 1137 行非空）
- [x] 6.2 查询线上 `waimaotong_raw_contacts` 5 列的非空行数（4 列 9530 行非空）
- [x] 6.3 导出备份至 `~/.clientget/db-backups/drop-pipeline-columns-backup-20260518/`（1.9M + 1.0M）

## 7. Alembic 迁移

- [x] 7.1 创建 Alembic revision `20260518_0043`（down_revision: 20260518_0042）
- [x] 7.2 编写 upgrade 函数：DROP COLUMN IF EXISTS × 25
- [x] 7.3 编写 downgrade 函数：ADD COLUMN IF NOT EXISTS × 25（含正确类型）

## 8. 线上部署与验证

- [x] 8.1 线上执行迁移 SQL（事务内，含 alembic_version 更新）✓
- [x] 8.2 确认 raw_companies 从 53 列减到 33 列 ✓
- [x] 8.3 确认 raw_contacts 从 21 列减到 16 列 ✓
- [ ] 8.4 验证管理端数据查看端点正常响应
