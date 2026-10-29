# 日志约定

> 事实来源：`app/core/logging.py`、`app/core/request_context.py`、`app/workers/sending.py::_log`、Sealos 日志面板取证经验（2026-07）。

## 格式与接入

- `configure_logging(debug)` 在 API lifespan 和 `scripts/run_sending_worker.py` 里把 root logger 设为 JSON 输出到 stdout：`timestamp / level / logger / message / request_id / exception`。
- 模块内 `logger = logging.getLogger(__name__)`；请求内日志自动带 `request_id`（来自 `RequestContextMiddleware`）。
- worker 事件用结构化字典，`event` 是检索键。发送链路当前事件包括 `send_accepted`、`send_finalize_failed`、`send_outcome_uncertain`、`send_rejected`、`quota_circuit_open`、`quota_circuit_closed`、`quota_defer_failed`、`quota_defer_fallback_failed`。
- 发送日志白名单：`event`、`instance_id`、`tenant_id`、`domain_id`、`email_id`、`phase`、`http_status`、`provider_code`、`error_class`、`decision`、`resume_at`、`message_id_length`，以及轮次统计用的 `count` / `enrollment_ids` / `isolated_count` / `sleep_seconds` / `domain_ids` / `paused_until` / `elapsed_ms` / `finalized_count` / `attempt`。不记原始 message id、SQL、凭证、`str(exception)`、收件邮箱。`EngageLabSendError` 的文本是 `engagelab_{outcome}:{http_status}:{provider_code}`。轮次 `print` 走 `sanitize_round_result`。
- 级别：`info` 记状态推进与轮次统计；`warning` 记可恢复的异常情况（锁被占、跳过）；`exception` / `error` 记失败并保留堆栈；`debug` 仅本地。

## 记什么 / 不记什么

记：状态迁移、外部调用的状态码与错误分类、跳过原因、每轮统计（处理数 / 成功 / 失败 / defer）。

**不记**（AGENTS.md §1 红线）：API key、密码、JWT、数据库连接串（展示时打码 `:****@`）、webhook 原文、客户联系人邮箱 / 姓名原文。需要标识用 id；需要展示密钥用 `_mask_secret` 之类只留前后几位。

## 线上取证（Sealos VictoriaLogs）

1. 纯 JSON 日志被拆成字段存储，`_msg` 只剩占位符——**关键词搜索无效**，用 JSON 模式按字段过滤（如 `event=send_failed`），或直接按时间窗导出。
2. 导出固定取"时间范围起点"开始的前 N 行（默认 100）：起点要精确落在目标事件密集段，必要时调大数量。
3. 面板时间选择器不保证是 UTC。2026-10 这次取证显示为 America/Los_Angeles：北京时间 10 月 27 日 09:00 对应 UTC 10 月 27 日 01:00、洛杉矶 10 月 26 日 18:00。先确认选择器时区，再换算窗口。
