# 后台 worker 工程模式

> 事实来源：`app/workers/sending.py`（全仓工程质量最高模块）、`reconciliation.py`、`wmt_lineage_repair.py`、`scripts/run_sending_worker.py`、`app/main.py` lifespan；2026-07-02 配额事故（档案：`docs/solutions/integration-issues/engagelab-quota-exhaustion-cascade.md`）。

## 两种运行形态

| 形态 | 现役例子 | 适用 |
|---|---|---|
| 独立进程常驻循环 | `scripts/run_sending_worker.py`：`while True: worker.run_once(engine)`，每轮约 5 秒，每 120 轮（约 10 分钟）跑一次对账；`--once` 单轮用于验证 | 高频、需要外部 I/O 节流、需要独立扩缩容 |
| API 进程 lifespan 内循环 | `run_wmt_lineage_repair_loop(engine, interval_seconds, stop_event)`：`asyncio.create_task`，`WMT_LINEAGE_REPAIR_ENABLED` 开关（默认 true）、300 秒 / 轮，`stop_event` 优雅退出；`run_industry_news_fetch_loop`（`workers/industry_news_fetch.py`）：`INDUSTRY_NEWS_FETCH_ENABLED` 开关（默认 false）、每天北京 08:00 一轮、整轮单事务 + 事务锁 + 每源 savepoint、不做启动补跑，错过的轮次由管理端「立即抓取」（`trigger_fetch`，后台任务去重）补 | 低频、轻量、不想多一个容器 |

新增后台任务默认选 lifespan 循环 + 环境变量开关（默认关，验证后在目标实例打开）。生产两个实例共库，**开关与锁都要按实例设计**。

## 必备模式

1. **`run_once(engine) -> dict`**：一轮就是一个可单独调用、可测试的函数，返回统计字典；循环只负责 sleep 与异常兜底（`except Exception: logger.exception(...)` 后继续下一轮，不让进程死掉）。
2. **实例级 advisory lock**：`SELECT pg_try_advisory_xact_lock(CAST(:key AS bigint) + pg_catalog.hashtext(:instance_id))`，拿不到锁就返回 `{"skipped": True, "reason": "lock_busy"}`（`wmt_lineage_repair.py`）。**事务级锁只覆盖持锁事务**：`wmt_lineage_repair` 只有关系修复阶段在锁内，补评阶段用独立事务、不在锁内。要整轮互斥，就把整轮放进同一事务，并用 `conn.begin_nested()` savepoint 隔离单条失败；不要把事务锁和"每条独立提交"组合——锁在持锁事务结束时即释放。仓库没有会话级锁（`pg_advisory_lock`）先例，不要为单个功能引入。
3. **可注入的时间与随机**：构造函数接受 `clock` / `sleep` / `random_between` / `log_sink`（`SendingWorker.__init__`），测试里推进虚拟时钟，不用 freezegun。
4. **结构化事件日志**：`self._log({"event": "quota_circuit_closed", ...})` 这类带 `event` 键的 JSON，线上按字段检索（见 logging-guidelines.md）。
5. **逐项隔离失败**：批处理里单条失败不回滚整轮（客户池修复：关系事务提交后再逐条补评，单条失败只记日志）。
6. **幂等**：本地键 `enrollment_id:step_id` 只映射到 EngageLab `request_id`（最长 128，约 1 小时去重）；超长则省略该字段，不截断、不改名发送 `idempotency_key`。跨日防重由 `email_send_locks` 承担。`mark_email_sent` 只接受已持有回执的 `accepted_pending`，或调用方已带 message id 的 `locked`（内部回调）。0 行即重复或状态不符。`recover_stale_locks` 每个进程启动回收一次。运行中另有节流的 `release_unsent_locks`（默认 60 秒一次，阈值 30 分钟），只释放有 `quota_usage_date`、尚未 `dispatch_started_at`、没有回执的新 `locked`，并按原占用日退额度。旧锁、`dispatching`、`uncertain`、`accepted_pending` 不在这条路径里重发。

## 发送 worker 的可靠性机制（改动前必读）

- 发送间隔固定 3 秒；按域名轮转（`_select_due_domain`）。
- 外发与本地回写分开：`begin_dispatch` 把 `locked` 提交为 `dispatching` 之后才 POST。拿到完整 id 后 `record_provider_acceptance` 写入 `accepted_pending`；回执重试 1/5/30 秒，接单时间只取第一次，不在重试时重算。三次都失败则留下 `dispatching`，不调用 `mark_email_failed`、不释放额度、不增加 attempt、不计限流。`mark_email_sent` 失败保持 `accepted_pending`。`sent_at`、`last_step_sent_at` 和 `next_step_due_at` 用锁上的 `provider_accepted_at`；`updated_at` 用恢复当时。下一次发送仍走当前工作窗口。每轮先 `isolate_timed_out_dispatches`，再按节流回收未外发新锁，然后最多本地恢复 20 条到期的 `accepted_pending`（`finalize_not_before` 未到的跳过；失败把该条推迟 60 秒）。只 finalize，不 `send_email`。然后才领取新邮件。
- 超时、断连、2xx 无 id、外发后的未知异常：`dispatching` → `uncertain`，不自动重发，不把联系人标 invalid。
- 错误分类在 `classify_send_error`（`app/integrations/engagelab.py`）。已核实配额只有 HTTP 4xx 且（code `30877`，或正文含 `balance is not enough` / `recharge soon` / `余额不足`）。`30801` / `30893` 是请求参数错误。裸 422 不是永久 invalid。`RECIPIENT_PERMANENT_CODES` 与 `RECIPIENT_POLICY_CODES` 在有发送接口出处前保持为空。SQL 异常文本不参与配额或限流判断。
- **配额熔断**：同域名连续 3 次已核实配额错误 → `domain_quota_paused` 到北京时间次日零点（`_next_beijing_midnight`），期间该域名邮件 **defer 而非 fail**（`_defer_for_quota`，单 enrollment 最多 3 次）；全部域名暂停时记 `all_domains_quota_paused` 事件后空转等待。本地回写失败不计入这 3 次。释放额度使用锁上的 `quota_usage_date`，跨过北京零点也不改记到失败日。
- **限流熔断**：10 分钟窗口内 3 次 429 或明确频控文案 → 按 quota 处理（`_record_rate_limit_hit`）。
- 领取 SQL 排除 `locked` / `sent` / `dispatching` / `accepted_pending` / `uncertain`，避免被占住的报名占满候选窗口。不要同时跑旧版和新版 sending worker。
- 对账 worker 主动查 EngageLab `GET /v1/email_status`（每批 20 个 id）补齐 webhook 丢失的状态。对账仍只处理已经 `sent` 且有 provider id 的行。

2026-07-02 的教训：没有熔断时额度耗尽会把 13,950 封排队邮件逐封打成 failed 并终止序列，仪表盘还把 failed 计入发送数。任何改动不得削弱 defer / 熔断语义；统计口径排除 failed（见 domain-rules.md）。

## 外部集成（`app/integrations/`）

- 客户端只做 HTTP 与错误对象化（`EngageLabSendError(status_code)`、`OpenRouterError(status_code, payload)`），不做业务决策；构造函数接受 `transport` 便于测试注入 `httpx.MockTransport`。
- EngageLab 分数据中心，凭证只在所属数据中心端点有效（新加坡 `https://email.api.engagelab.cc` / 土耳其 `https://emailapi-tr.engagelab.com`）；持续 401 `code 30000` 先跨数据中心探测，不要反复轮换 key。
- 凭证来自 `Settings`（`.env.local`），不得硬编码或写入日志。

## 新增后台任务检查清单

- [ ] `run_once` 可单独调用并返回统计
- [ ] 按实例过滤数据 + 实例级 advisory lock
- [ ] 环境变量开关（默认关）+ 间隔可配
- [ ] 单条失败不影响整轮；异常 `logger.exception` 带定位键
- [ ] 幂等可重跑
- [ ] 单测注入 clock / 替身 service；涉及 SQL 语义的在 Neon 开发库断言
