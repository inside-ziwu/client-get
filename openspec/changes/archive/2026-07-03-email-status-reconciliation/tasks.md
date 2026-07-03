## 1. Service 层

- [x] 1.1 已实现 `backend/app/services/email_reconciliation_service.py`（186 行）：查询 stuck 邮件（status='sent' 且超 30 分钟）→ 按 CST send_date 分组调 EngageLab API → 更新 emails/enrollments/contacts/companies，email_events 记 source='reconciliation'
- [x] 1.2 `reconcile_once(conn, client) -> dict` 返回统计（total/delivered/bounced_soft/bounced_invalid/sending/not_found）

## 2. Worker

- [x] 2.1 已实现 `backend/app/workers/reconciliation.py`（`ReconciliationWorker.run_once(engine)` 薄壳）
- [x] 2.2 【实施勘正】未建独立启动脚本——最终形态为**内联集成**：`run_sending_worker.py` 主循环每 120 轮（约 10 分钟）调用一次，异常被捕获记日志不影响发送（见 design 勘正节）

## 3. 验证

- [x] 3.1 【实施勘正】独立 `--once` 验证被内联形态取代：随 2026-07-03 镜像（2026.07.03-r3）在生产 A/B 双实例运行，worker 日志无「对账异常」，发送主循环不受影响
- [x] 3.2 生产实况（2026-07-03）：当前仅 1 封 stuck（2026-06-24 历史遗留，超出 API 可查窗口，按 spec not_found 路径跳过属预期）；近期 webhook 健康（email_events 78,986 条 source='engagelab'），对账补录事件为 0——安全网就位、暂无活可干；真实补账路径待 webhook 丢失场景自然验证

## 4. 部署

- [x] 4.1 无需改动镜像脚本（内联于 sending worker，代码随 backend 镜像自然携带）
- [x] 4.2 【实施勘正】无需 Sealos 新增容器进程——内联形态已随 2026-07-03 部署在 A/B 两实例生效
