## Context

仪表盘 `email_stats_by_date_range`（`tenant_query_service.py:766`）当前调用 EngageLab Stats API（`/v1/stats_day`），返回账户级全局数据，无租户隔离。用户只有 83 封邮件但看到 106。

本地 `emails` 表已有完整追踪字段（`open_count`、`first_opened_at`、`soft_bounce`、`invalid_email`、`report_spam`、`unsubscribed`），由 `WebhookService` 通过 EngageLab webhook 实时写入。原设计 D1/D4 即选择本地查询，后因追踪数据疑似不准改为 API，但引入了更严重的问题。

## Goals / Non-Goals

**Goals:**
- 恢复本地 `emails` 表聚合查询，保证租户隔离
- 百分比字段由后端自算（sent 为分母）
- API 响应格式完全不变，前端零改动

**Non-Goals:**
- 不修改 webhook 处理逻辑
- 不修改 `emails` 表结构
- 不修改前端组件

## Decisions

### D1: 数据源切回本地 emails 表

**选择**：本地 `emails` 表 SQL 聚合（恢复原设计）

**理由**：
- EngageLab Stats API 是账户级，无法按租户拆分
- 本地表有 RLS 保护，天然租户隔离
- webhook 回写逻辑代码正确（已审查 `WebhookService`），追踪字段完整

### D2: 汇总查询 SQL（沿用原 D4 映射）

单条 SQL 完成所有汇总指标计算：

| 统计指标 | SQL 表达式 |
|---------|-----------|
| targets | `COUNT(*)` |
| sent | `COUNT(*) FILTER (WHERE status NOT IN ('draft', 'pending', 'queued'))` |
| delivered | `COUNT(*) FILTER (WHERE status IN ('delivered', 'opened', 'clicked', 'replied'))` |
| invalid_email | `COUNT(*) FILTER (WHERE invalid_email = true)` |
| soft_bounce | `COUNT(*) FILTER (WHERE soft_bounce = true)` |
| billing | 等同 sent |
| total_opens | `COALESCE(SUM(open_count), 0)` |
| opens | `COUNT(*) FILTER (WHERE first_opened_at IS NOT NULL)` |
| report_spam | `COUNT(*) FILTER (WHERE report_spam = true)` |
| unsubscribe | `COUNT(*) FILTER (WHERE unsubscribed = true)` |

日期过滤：`WHERE tenant_id = :tenant_id AND created_at >= :start_date AND created_at < :end_date + interval '1 day'`

### D3: 百分比计算

后端自行计算，以 sent 为分母（避免除零）：
- `delivered_percent` = delivered / sent * 100（保留两位小数）
- `total_open_percent` = total_opens / sent * 100
- `open_percent` = opens / sent * 100

sent = 0 时，所有百分比返回 0。

### D4: 每日明细查询

`GROUP BY DATE(created_at)` 聚合，每日统计 sent / delivered / opens 三个维度：

```sql
SELECT DATE(created_at) AS date,
       COUNT(*) FILTER (WHERE status NOT IN ('draft','pending','queued')) AS sent,
       COUNT(*) FILTER (WHERE status IN ('delivered','opened','clicked','replied')) AS delivered,
       COUNT(*) FILTER (WHERE first_opened_at IS NOT NULL) AS opens
FROM emails
WHERE tenant_id = :tenant_id
  AND created_at >= :start_date
  AND created_at < :end_date + interval '1 day'
GROUP BY DATE(created_at)
ORDER BY date
```

无数据日期不填充零值行（趋势图前端已处理空数据）。

### D5: 移除 EngageLab Stats 相关代码

- 删除 `EngageLabClient.get_stats_day()` 方法
- 删除 `tenant_query_service.py` 中的 `_stats_cache` 全局缓存
- 保留 `EngageLabClient.send_email()`（发送功能不受影响）

### D6: 数据验证

实施后需人工对比验证：
- 查询本地 `emails` 表特定日期范围的聚合结果
- 与 EngageLab 控制台数据交叉比对
- 确认 webhook 追踪字段的准确性

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| webhook 追踪数据之前疑似不准确 | 代码审查 WebhookService 逻辑正确；实施后人工对比验证 |
| emails 表数据量增长后查询变慢 | `created_at` 已有索引，日期范围查询性能可控；后续可加物化视图 |
| 删除 `get_stats_day` 后无法回退 | 代码在 git 历史中，如需可恢复 |
