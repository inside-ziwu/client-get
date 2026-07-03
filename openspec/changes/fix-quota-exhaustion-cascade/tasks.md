## 1. 日志校准（实施前置）

- [x] 1.1 用户已导出 2026-07-02 19:10–19:30（UTC）全量 stdout 日志（`logs-2026-07-03T02_05_52.488Z.txt`，1000 行失败样本）。实测签名：HTTP 400，`{"code": 30877, "message": "mail failed to send. 552 {'code':-7,'message':'your account balance is not enough,please recharge soon',...}"}`；`send_attempt_count=0` 直接永久失败，与数据库 13,913 封 attempt=0 吻合。注意：文案为「余额不足请充值」，额度可能为预付费型、未证实次日自动重置（重置时点因当晚队列烧空无法从日志观察）
- [x] 1.2 校准结论已写入 design D1：`QUOTA_KEYWORDS` = `balance is not enough` / `recharge soon` / `"code": 30877` + 原兜底词；`QUOTA_STATUS_CODES` 保持为空（实测走 HTTP 400，太泛不可作码级白名单）。实施时按 design D1 落码（task 2.1）

## 2. 错误分类修正（backend/app/workers/sending.py）

- [x] 2.1 `_classify_provider_error` 扩展签名接收 `error_message`，按 design D1 顺序实现：日配额关键词/错误码 → 配额类熔断；429 与限流信号 → 临时重试链；同域名 10 分钟窗口累计 ≥3 次 → 升级熔断（内存计数）
- [x] 2.2 未知 4xx 的默认分类从永久失败改为临时失败；401/403/5xx 临时、422 永久 invalid 维持不变
- [x] 2.3 分类单测：日配额关键词（含中文、大小写）、单次 429 走重试链不熔断、10 分钟内第 3 次升级熔断、未知 4xx 临时、422 永久，五类判定

## 3. 配额错误的邮件处理（backend/app/services/tenant_messaging_service.py）

- [x] 3.1 新增 `defer_email_for_quota(conn, email_id, resume_at)`：**删除**未发出的邮件行（sent_at/engagelab_message_id 均为 NULL 的校验前置）、锁置 `released` 且 `email_id` 置 NULL、释放 `domain_daily_usage.reserved_count`、enrollment `next_step_due_at=resume_at` 且不增加 `send_attempt_count`、状态保持 `active`
- [x] 3.2 连续 defer 上限：worker 内存计数同一 enrollment 连续配额 defer 次数，达 3 次后改走 `mark_email_failed` 临时失败分支（消耗 attempt、走重试链）
- [x] 3.3 `domain_daily_usage` 窗口对齐北京日：日期由 Python 端 helper（`Asia/Shanghai`，可注入 `now_utc`）计算后作 `:usage_date` 参数传入，SQL 端不做时区表达式（依据 design D5 修订：纯 mock 可测性 + asyncpg `::` 转换陷阱）；覆盖 claim 配额门、预留、释放（`_release_reserved_quota`）；`daily_quota` 今日统计（emails.created_at 范围查询）改传北京日零点的带时区 datetime 边界，而非裸 date
- [x] 3.4 service 单测：defer 的删行 + 锁 + 配额 + enrollment 四表联动、attempt 不变；配额窗口跨 16:00Z（北京零点）边界的读写归属

## 4. 熔断机制（backend/app/workers/sending.py）

- [x] 4.1 `SendingWorker` 新增 `domain_quota_paused` 与限流升级计数内存态；发送遇配额类错误时调用 `defer_email_for_quota`（替代 `mark_email_failed`），并将该域名 `paused_until` 置为次日北京时间 00:00（UTC 存储）
- [x] 4.2 `run_once` 领取前过滤熔断中的域名，过期条目清理（被动恢复，空闲轮询秒级）；全部熔断时按 idle 逻辑休眠
- [x] 4.3 结构化日志：触发记 `quota_circuit_open`（domain_id / paused_until / 错误摘要），恢复后首轮记 `quota_circuit_closed`
- [x] 4.4 worker 单测（注入 clock/provider 模拟）：配额错误触发熔断并 defer、熔断期跳过该域名但不影响其他域名、跨天后自动恢复、**重启后熔断态丢失且首封配额错误即重新熔断**、连续 defer 3 次后降级临时失败

## 5. 仪表盘口径（backend/app/services/tenant_query_service.py）

- [x] 5.1 三处「已发送」过滤统一改为 `status NOT IN ('draft','pending','queued','failed')`：`email_stats_by_date_range`（summary 与 daily）、`plan_overview` 的 `emails_sent`（计划级与租户级两处）、`daily_quota` 今日已发送；`targets`/`billing`/百分比公式不动
- [x] 5.2 更新既有测试 `backend/tests/test_dashboard_email_stats.py`：新增含 failed 的用例，断言 targets/sent/billing/delivered_percent 符合新口径；补 plan_overview 与 daily_quota 的口径一致断言

## 6. 验证与收尾

- [x] 6.1 跑后端全量测试（`pytest`）与 lint，全部通过
- [x] 6.2 调用 verification-before-completion，输出「原始需求 → 已实现/未实现」对照（熔断 / 错误分类 / 仪表盘口径 / 配额窗口对齐四项逐条核对 spec 场景）
- [x] 6.3 openspec 校验通过（`openspec status` 全部工件 done），准备走 /opsx:verify → 归档

## 7. 部署（开发验证通过后，用户触发）

- [ ] 7.1 代码推 GitHub，GitHub Actions `workflow_dispatch` 构建 backend 镜像（service: backend）推送 ACR
- [ ] 7.2 Sealos 控制台更新 backend 服务与 sending worker 的镜像 tag（**Instance A 与 Instance B 两套服务都要更新**，避免未修复实例的 worker 在配额耗尽时重演事故行为）。重启后正反两向核对：正向观察 `quota_circuit_open/closed` 日志与仪表盘数值（已发送应剔除 failed）；**反向核对检测漏判**——若出现短窗内连续/批量 4xx `send_failed` 而无对应 `quota_circuit_open`，判定识别规则漏判，立即回读日志补充 `QUOTA_STATUS_CODES`/`QUOTA_KEYWORDS` 并发版
