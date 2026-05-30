## Context

实现依据为 `docs/plans/2026-05-30-001-feat-sending-throttle-reliability-plan.md`。该计划已明确边界、技术决策、实现单元和审查修正项；本 change 是实施权威载体。

## Decisions

- 每轮发送前从 `sending_plans` 查询 running plan 的 distinct `domain_id`，以便新增/停止 plan 在下一轮生效。
- Worker 维护内存 `domain_clocks`，域名冷却状态随进程重启重置。
- 所有域名冷却时，Worker sleep 到最早到期时间，但不超过 `idle_poll_seconds`，避免长时间错过新 running plan。
- 临时错误按固定数组 `[15m, 1h, 4h]` 设置重试时间，第 4 次失败后 enrollment 进入 `failed`。
- 401/403 属于配置问题，按临时错误处理，不更新 contact_status。
- 422 视为无效邮箱，永久失败并将 contact_status 更新为 `invalid`；硬退信类错误可通过 `error_category='bounce'` 更新为 `bounced`。
- `mark_email_failed` 原子回收 reserved quota；`recover_stale_locks` 也回收对应 domain 当日 reserved quota。
- EngageLab 幂等键支持未完全确认：请求体中仅在 payload 提供 `idempotency_key` 时追加该字段，保持向后兼容。

## Risks

- 如果 provider 在 DB 回写前已发送成功但本地崩溃，重启后仍可能重发；幂等键降低该风险，但最终取决于 provider 支持程度。
- stale lock 超时 30 分钟远大于正常 HTTP timeout，可接受极慢请求与恢复并发写回的低概率竞态。
