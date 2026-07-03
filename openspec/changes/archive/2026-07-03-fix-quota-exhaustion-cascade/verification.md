# Verification Log

## 2026-07-03 Neon dev smoke

Command:

```bash
cd backend && uv run python ../openspec/changes/fix-quota-exhaustion-cascade/smoke_quota_exhaustion_cascade.py
```

Result:

```text
smoke stats: ok
smoke window: ok
smoke defer loop: ok
smoke all: ok (rolled back)
```

Notes:

- Connected to `CLIENTGET_DEV_DATABASE_URL` only.
- Created temporary tenant/domain/plan/enrollment/email rows inside one transaction.
- Verified dashboard sent/billing scope, Beijing quota window, and quota defer/reclaim loop against real PostgreSQL semantics.
- Transaction was rolled back; no sample data persisted.

## 2026-07-03 completion gates

Commands:

```bash
cd backend && uv run ruff check
cd backend && uv run pytest -q
cd backend && uv run python ../openspec/changes/fix-quota-exhaustion-cascade/smoke_quota_exhaustion_cascade.py
openspec status --change fix-quota-exhaustion-cascade
```

Results:

```text
uv run ruff check
All checks passed!

uv run pytest -q
277 passed, 7 warnings

smoke_quota_exhaustion_cascade.py
smoke stats: ok
smoke window: ok
smoke defer loop: ok
smoke all: ok (rolled back)

openspec status --change fix-quota-exhaustion-cascade
All artifacts complete!
```

## verification-before-completion 对照

- 原始需求：配额错误不能被 4xx 永久失败吞掉，应按余额不足/充值/30877 等信号识别为 quota；429 保持限流重试并在短窗重复时升级。
  已实现：`_classify_provider_error` 接收 provider 错误正文，覆盖 quota 关键词、30877、429、未知 4xx 临时化与 422 永久 invalid；测试覆盖分类与 429 三次升级。
- 原始需求：quota 命中后应熔断域名到次日北京时间 00:00，跳过熔断域名且不阻塞其他域名，恢复后继续；同 enrollment 连续 defer 达上限后走临时失败链。
  已实现：`SendingWorker` 维护 `domain_quota_paused`、rate-limit hit 窗口与 enrollment defer 计数，记录 `quota_circuit_open/closed`，领取前过滤熔断域名；worker 测试覆盖熔断、跳过、跨天恢复、重启丢失内存态后重开、defer 上限降级。
- 原始需求：quota defer 不应消耗发送 attempt，不应留下 queued 邮件或占用锁/预留配额。
  已实现：`defer_email_for_quota` 校验未发送邮件后删除 email、释放锁、回退 `domain_daily_usage.reserved_count`，推迟 enrollment 且保持 active/attempt 不变；service 单测和 Neon smoke 覆盖真实删除、释放与重新 claim。
- 原始需求：domain_daily_usage 与今日 quota 统计按北京自然日归属。
  已实现：新增北京日 helper，claim/reserve/release/daily_quota 均由 Python 端注入北京日边界，避免 SQL 时区表达式差异；单测与 Neon smoke 覆盖 16:00Z 边界。
- 原始需求：仪表盘“已发送”口径剔除 failed，targets/billing/百分比公式保持不漂移。
  已实现：`email_stats_by_date_range`、`plan_overview`、`daily_quota` 的 sent 过滤统一排除 failed；测试覆盖 summary、daily、计划级与租户级 overview、daily quota。

未实现：部署第 7 组未执行，按计划需要用户显式触发 GitHub Actions 构建与 Sealos 更新。
