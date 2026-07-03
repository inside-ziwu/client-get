---
title: 全 mock 测试库下 SQL 语义的验证约定（Neon 冒烟 + Python 端日期传参）
date: 2026-07-03
category: conventions
module: backend_testing
problem_type: convention
component: testing_framework
severity: high
applies_when:
  - "改动涉及 SQL 口径（FILTER 条件、聚合、窗口边界）或多表联动写路径"
  - "涉及时区/日期窗口的业务逻辑（如 domain_daily_usage 的北京自然日）"
  - "新增依赖真实数据库组合语义的功能（分区表 DELETE、ON CONFLICT 复用等）"
tags: [testing, mock, sql, neon, smoke-test, timezone, beijing-day]
---

# 全 mock 测试库下 SQL 语义的验证约定（Neon 冒烟 + Python 端日期传参）

## Context

本仓库 backend 测试全部为内存 mock（AsyncMock/FakeConn，无真实 Postgres），单测只能断言「SQL 文本包含什么、参数是什么、返回值怎么映射」——**SQL 的真实语义（FILTER 是否加对列、窗口边界是否正确、多语句组合是否闭环）单测证明不了**。2026-07 配额修复中两处问题恰好都藏在这个盲区：仪表盘口径 FILTER 与 defer 四表回路。

## Guidance

1. **SQL 口径/写路径改动必须配一次 Neon 开发库冒烟**：造少量样本数据 → 调用真实 service 方法 → 断言落库结果 → 清理。脚本化断言（非肉眼看输出），执行输出存档进对应 openspec change。先例：`openspec/changes/archive/2026-07-03-fix-quota-exhaustion-cascade/verification-u6-smoke.md`（口径/窗口/defer 回路三组 20 断言）。
2. **时区窗口逻辑把日期计算放 Python 端传参，不写 SQL 端表达式**：`beijing_today(now_utc)`（`app/utils/beijing_time.py`）计算后作 `:usage_date` 参数——mock 单测可直接断言参数值覆盖 16:00Z 边界两侧；SQL 端 `(now() AT TIME ZONE ...)::date` 在 mock 体系下不可测，且 asyncpg 对 `:param::type` 有已知陷阱（见 `docs/solutions/runtime-errors/asyncpg-named-param-cast-syntax-error-20260507.md`）。注意 **compute-once**：每个逻辑操作入口取一次日期贯穿全部语句，禁止同一事务流中多次独立取值（跨零点会把记账分裂到两行）。
3. **时间控制不引入 freezegun**：worker 层注入 `clock` callable（`_Clock.advance()` 推进），service 层显式 `now_utc: datetime | None = None` 参数——沿用 `is_sendable_now` 先例。
4. **对 emails 等 timestamptz 范围查询，边界传带时区 datetime 瞬时而非裸 date**：裸 date 会被会话时区（生产=UTC）提升为 UTC 零点，北京日窗口错位 8 小时——daily_quota 的教训。

## Why This Matters

CI 不跑测试、更没有真实库集成测试，SQL 层回归没有任何自动防线。「文本断言 + 参数断言 + 冒烟兜底」是当前成本最低的组合；跳过冒烟等于让口径/写路径改动裸奔上线（AGENTS.md 也要求真实链路验证或明确记录未验证原因）。

## When to Apply

- 见 frontmatter `applies_when`；反例：纯 Python 逻辑、路由参数、返回值映射类改动无需冒烟

## Examples

冒烟脚本形态（三段式）：伪造样本（复用既有 dev 租户/联系人满足外键与 RLS，owner 角色连接或 `set_current_tenant`）→ 调 service 断言（如 defer 后邮件行删除、锁 released、reserved_count 回退、enrollment attempt 不变）→ 清理（含备份表、伪造行，二次运行验证幂等）。

## Related

- `docs/solutions/runtime-errors/asyncpg-named-param-cast-syntax-error-20260507.md`
- `docs/solutions/integration-issues/engagelab-quota-exhaustion-cascade.md`
