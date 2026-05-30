## 1. OpenSpec 与分支准备

- [x] 1.1 创建当前功能对应的 OpenSpec change
- [x] 1.2 从 main 创建功能分支 `feat/sending-throttle-reliability`

## 2. Schema 与 provider

- [x] 2.1 新增迁移：`send_attempt_count` 默认 0，`sequence_enrollments.status` 允许 `failed`
- [x] 2.2 `EngageLabSendError` 增加 `status_code`
- [x] 2.3 `send_email` 对 4xx/5xx 异常携带状态码，并透传可选 idempotency key

## 3. Service 层

- [x] 3.1 `claim_due_emails` 增加 `domain_id` 过滤，返回 `domain_id`、`send_strategy`、`enrollment_id`
- [x] 3.2 `claim_due_emails` 内部扩大候选读取，避免 limit=1 时队头阻塞
- [x] 3.3 `mark_email_sent` 推进下一步或完成时重置 `send_attempt_count`
- [x] 3.4 `mark_email_failed` 支持临时/永久错误、递增重试、最终 failed、contact_status 更新和配额回收
- [x] 3.5 新增 `recover_stale_locks`，使用 `make_interval` 参数化并回收配额
- [x] 3.6 收件人筛选排除 `invalid`

## 4. Worker 与脚本

- [x] 4.1 Worker 实现域名发现、claim-one-send-one、域名独立节流和结构化日志
- [x] 4.2 Worker 注入 clock/sleep/random，便于确定性测试
- [x] 4.3 Worker 错误分类：5xx/429/401/403/网络异常为临时，422 为 invalid 永久错误
- [x] 4.4 `run_sending_worker.py` 移除 `--limit` 与固定循环 sleep，增加 `--idle-poll-seconds`

## 5. 测试与验证

- [x] 5.1 新增/更新 EngageLab 集成测试
- [x] 5.2 新增 sending worker/service 单元测试覆盖 AE1-AE5 与审查修正项
- [x] 5.3 运行相关 pytest
- [x] 5.4 运行迁移/语法级验证
