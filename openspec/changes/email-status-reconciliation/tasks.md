## 1. Service 层

- [ ] 1.1 创建 `backend/app/services/email_reconciliation_service.py`，从 `backfill_email_status.py` 提取核心逻辑：查询 stuck 邮件 → 调 EngageLab API → 更新 emails/enrollments/contacts/companies
- [ ] 1.2 service 方法签名：`reconcile_once(conn, client) -> dict`，返回统计结果（delivered/bounced_soft/bounced_invalid/sending/not_found/skipped）

## 2. Worker

- [ ] 2.1 创建 `backend/app/workers/reconciliation.py`，实现 `ReconciliationWorker.run_once(engine)`，调用 service 后休眠 10 分钟
- [ ] 2.2 创建 `backend/scripts/run_reconciliation_worker.py`，参考 `run_sending_worker.py` 模式

## 3. 验证

- [ ] 3.1 本地连接生产库执行 `python -m scripts.run_reconciliation_worker --once`，确认能正确查询并输出（不写库的 dry-run 或无待对账邮件时空转）
- [ ] 3.2 确认 worker 正常结束无报错

## 4. 部署

- [ ] 4.1 更新 `backend/scripts/push-backend.sh` 或 Dockerfile，确保对账 worker 脚本包含在镜像中
- [ ] 4.2 在 Sealos 控制台新增或复用容器进程，启动 `python -m scripts.run_reconciliation_worker`
