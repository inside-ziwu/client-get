## ADDED Requirements

### Requirement: 系统 SHALL 删除采集/清洗/评分管道的全部代码文件

删除以下文件后，FastAPI 主进程 MUST 正常启动，无 ImportError。

删除清单：
- Service: `collection_service.py`, `cleanup_service.py`, `scoring_service.py`, `collection_scheduler_service.py`
- Integration: `integrations/collection/` 整个目录
- Worker: `workers/collection.py`, `workers/collection_scheduler.py`, `workers/cleanup.py`, `workers/scoring.py`
- API: `api/internal/collection.py`, `schemas/internal_collection.py`
- Scripts: `scripts/run_collection_worker.py`, `scripts/run_collection_scheduler_worker.py`, `scripts/run_collection_scheduler.py`, `scripts/run_cleanup_worker.py`, `scripts/run_scoring_worker.py`
- Tests: 所有直接 import 被删模块的测试文件

#### Scenario: 删除后 FastAPI 正常启动

- **GIVEN** 上述文件已删除，import 链已修复
- **WHEN** 执行 `python -c "from app.main import create_app; create_app()"`
- **THEN** 无 ImportError，应用创建成功

#### Scenario: 删除后无悬空 import

- **GIVEN** 上述文件已删除
- **WHEN** 在 `backend/app/` 中 grep 被删模块名
- **THEN** 无任何残留 import 引用

### Requirement: 系统 SHALL 修改 import 链中的依赖文件

以下文件 MUST 移除对被删模块的引用：
- `api/internal/router.py`：移除 collection_router 注册
- `api/internal/ops.py`：移除 3 个 scoring 端点
- `services/internal_ops_service.py`：移除 collection_service、scoring_service 的 import 和相关方法
- `integrations/collection/router.py`：随目录删除

#### Scenario: internal_ops_service 保留非管道功能

- **GIVEN** internal_ops_service.py 已修改
- **WHEN** 检查其公开方法
- **THEN** `list_collection_credentials`、`batch_upsert_competitors`、`claim_due_emails`、`mark_email_sent`、`mark_email_failed`、`reserve_domain_quota`、`publish_article` 等方法 MUST 保留

#### Scenario: admin 数据查看端点保留

- **GIVEN** 管道代码已删除
- **WHEN** 访问管理端数据查看 API
- **THEN** raw 数据浏览、clean 公司列表等端点 MUST 正常响应
