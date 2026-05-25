---
title: "fix: 仪表盘 email-stats 数据源从 EngageLab API 切回本地 emails 表"
status: active
created: 2026-05-25
origin: openspec/changes/fix-dashboard-email-stats-datasource/
---

## Problem Frame

仪表盘 `email_stats_by_date_range` 调用 EngageLab Stats API（`/v1/stats_day`），返回的是整个 EngageLab 账户级汇总数据。用户只有 83 封邮件，但仪表盘显示 106（包含其他租户邮件）。此外百分比以 delivered 为分母，与业务预期（sent 为分母）不一致。缓存 key 也不含 tenant_id，跨租户共享。

需切回本地 `emails` 表聚合查询，恢复原设计 D1/D4 方案。

---

## Scope Boundaries

**In scope:**
- 重写 `email_stats_by_date_range` 为本地 SQL 聚合
- 清理 EngageLab Stats 相关死代码（`get_stats_day`、`_stats_cache`、`engagelab_stats_base_url`）
- 重写测试

**Out of scope:**
- WebhookService 修改
- emails 表结构变更
- 前端改动（API 响应格式不变）
- EngageLab 邮件发送功能

---

## Key Technical Decisions

**数据源**：本地 `emails` 表 SQL 聚合。RLS 天然保证租户隔离，`conn` 参数已正确传入但当前未使用。（see origin: openspec/changes/fix-dashboard-email-stats-datasource/design.md D1）

**百分比计算**：后端自算，以 sent 为分母，sent=0 时返回 0。（see origin: design.md D3）

**SQL 映射**：沿用原设计 D4 的 FILTER 聚合方案，参考同文件 `email_stats` 方法（L744-764）的编码风格。

**无缓存**：删除 `_stats_cache`。本地查询走 RLS 索引（`idx_emails_tenant_created`），毫秒级响应，无需缓存。

---

## Existing Patterns

- `tenant_query_service.py:744-764` — `email_stats` 方法：同表 `COUNT(*) FILTER (WHERE ...)` 聚合，`conn.execute(text(...))` + `result.mappings().one()`
- SQL 参数使用 `:param_name` 占位，禁止 `::type` 语法（用 `CAST(:param AS uuid)`）— learnings: asyncpg 命名参数限制
- 路由层 `core.py:23-33` — 日期参数解析和 service 调用模式

---

## Implementation Units

### U1. 测试先行：重写服务层测试（RED）

**Goal:** 为新的本地 DB 聚合逻辑编写测试，替换现有 EngageLab mock 测试

**Requirements:** summary 13 个字段正确聚合；daily 按日期分组返回 sent/delivered/opens；百分比以 sent 为分母自算

**Dependencies:** 无

**Files:**
- `backend/tests/test_engagelab_stats.py`（重写 → 可重命名为 `test_dashboard_email_stats.py`）

**Approach:**
- 删除所有 EngageLab 相关 mock 辅助函数（`_mock_client`、`_make_settings`、mock 数据常量）
- 删除 `TestStatsBaseUrlConfig`（U1 配置层）和 `TestGetStatsDay`（U2 集成层）整个类
- 重写 `TestEmailStatsByDateRange`：mock `conn.execute` 返回 `MappingResult`，构造两次调用（汇总 + 每日明细）的返回值
- 删除缓存相关测试（`test_cache_hit`、`test_cache_expired`）和 `_clear_cache` fixture

**Execution note:** TDD — 先写测试，此时运行全部 FAIL

**Test scenarios:**
- 正常数据：传入含多种 status 的邮件行，验证 targets/sent/delivered/invalid_email/soft_bounce 各 FILTER 计数正确
- 百分比计算：sent=10, delivered=8, total_opens=5, opens=3 → delivered_percent=80.0, total_open_percent=50.0, open_percent=30.0
- billing 等于 sent：验证 billing 字段值 == sent 字段值
- 空数据：无邮件记录时 summary 全 0、百分比全 0、daily 为空数组
- sent=0 时百分比为 0：避免除零错误
- 每日明细：多天数据按 DATE(created_at) 分组，按日期升序返回
- 日期范围过滤：只统计 start_date 到 end_date 范围内的邮件
- 租户隔离：验证方法传入的 tenant_id 参数被正确用于 SQL 查询条件，不同租户只能看到自己的数据

**Verification:** 测试全部 FAIL（因实现未改）

---

### U2. 实现：重写 email_stats_by_date_range（GREEN）

**Goal:** 用本地 SQL 聚合替换 EngageLab API 调用，让 U1 的测试通过

**Requirements:** 汇总 SQL 按 D2 映射，百分比按 D3 计算，每日明细按 D4 聚合

**Dependencies:** U1

**Files:**
- `backend/app/services/tenant_query_service.py`（重写 L766-836 `email_stats_by_date_range` 方法）

**Approach:**
- 汇总查询：单条 SQL 使用 `COUNT(*) FILTER (WHERE ...)` 聚合所有指标，日期过滤 `created_at >= :start_date AND created_at < :end_date + interval '1 day'`
- 百分比：Python 侧计算 `round(x / sent * 100, 2) if sent > 0 else 0`
- billing = sent
- 每日明细：第二条 SQL，`GROUP BY DATE(created_at) ORDER BY date`
- `conn` 和 `tenant_id` 参数正式使用
- 方法签名不变，返回格式 `{"summary": {...}, "daily": [...]}` 不变

**Patterns to follow:** 同文件 `email_stats` 方法（L744-764）的 `conn.execute(text(...))` + `result.mappings()` 模式

**Test scenarios:** U1 的测试全部通过

**Verification:** `pytest backend/tests/test_dashboard_email_stats.py` 全绿

---

### U3. 清理：删除 EngageLab Stats 死代码

**Goal:** 移除不再使用的 Stats API 相关代码和配置

**Dependencies:** U2

**Files:**
- `backend/app/services/tenant_query_service.py`（删除 `_stats_cache`、`_CACHE_TTL`、`import time`、`EngageLabClient`/`EngageLabSendError` 导入）
- `backend/app/integrations/engagelab.py`（删除 `get_stats_day` 方法）
- `backend/app/core/config.py`（删除 `engagelab_stats_base_url` 配置项）

**Approach:**
- 逐个文件清理，每删一处确认无其他引用
- `engagelab_stats_base_url` 仅被 `get_stats_day` 使用，确认后删除
- 保留 `EngageLabClient` 类和 `send_email` 方法（发送功能不受影响）

**Test expectation:** none — 纯删除死代码

**Verification:** `pytest backend/tests/` 全绿；`grep -rn "get_stats_day\|_stats_cache\|engagelab_stats_base_url" backend/app/` 无结果

---

### U4. 路由层端到端测试

**Goal:** 验证完整 HTTP 请求链路正确

**Dependencies:** U2, U3

**Files:**
- `backend/tests/test_dashboard_email_stats.py`（追加 `TestDashboardEmailStatsRoute` 类）

**Approach:**
- 重写 `TestDashboardEmailStatsRoute`：mock `conn.execute` 而非 `EngageLabClient`
- 使用 `httpx.ASGITransport` + `httpx.AsyncClient` 发真实 HTTP 请求
- 验证 `/t/{slug}/api/v1/dashboard/email-stats` 返回 200 + 正确的 summary/daily 结构

**Test scenarios:**
- 带日期参数请求：返回 200，body.data 包含 summary 和 daily
- 不带日期参数：默认近 30 天，返回 200
- summary 字段完整性：13 个字段全部存在且类型正确

**Verification:** `pytest backend/tests/test_dashboard_email_stats.py` 全绿

---

## System-Wide Impact

| 影响面 | 说明 |
|--------|------|
| 租户仪表盘数据 | 从全局数据变为租户隔离数据，数值会变（这是修复） |
| EngageLab 集成 | 仅删除 Stats API 调用，发送功能不受影响 |
| 前端 | 无变更（响应格式不变） |
| 数据库 | 无迁移，利用已有索引 |

---

## Deferred Implementation Notes

- webhook 追踪字段准确性需实施后人工对比验证（本地数据 vs EngageLab 控制台）
- 如果 emails 表数据量增长导致查询变慢，后续可加物化视图优化

---

## GSTACK REVIEW REPORT

**Reviewed:** 2026-05-25
**Reviewer:** /plan-eng-review
**Verdict:** PASS — 可直接进入实施

### Architecture Review — 0 issues

- `email_stats`（L744-764）与 `email_stats_by_date_range`（L766-836）服务不同前端页面（邮件监控 vs 仪表盘首页），字段集不同，保持独立方法正确
- 数据源从 EngageLab Stats API 切回本地 emails 表，RLS 天然保证租户隔离
- API 响应格式不变，前端零改动

### Code Quality Review — 0 issues

- SQL 聚合模式与同文件 `email_stats` 方法一致（`COUNT(*) FILTER` + `conn.execute(text(...))`）
- asyncpg 命名参数限制已在计划中明确（`CAST(:param AS uuid)` 而非 `::type`）
- 死代码清理范围明确（`get_stats_day`、`_stats_cache`、`engagelab_stats_base_url`）

### Test Review — 1 gap found, resolved

- **D2 决策**：U1 测试场景缺少租户隔离验证 → 已补充「租户隔离：验证 tenant_id 参数被正确用于 SQL 查询条件」
- 7 + 1 = 8 个测试场景覆盖：正常数据、百分比计算、billing=sent、空数据、除零保护、每日明细、日期范围过滤、租户隔离

### Performance Review — 0 issues

- 本地查询走 `idx_emails_tenant_created` 索引，毫秒级响应
- 删除 `_stats_cache` 合理（本地索引查询无需缓存层）
- 数据量增长风险已在 Deferred Notes 中标注（物化视图备选）
