## 1. 重写后端 email_stats_by_date_range

- [ ] 1.1 重写 `tenant_query_service.py` 的 `email_stats_by_date_range` 方法：用本地 `emails` 表 SQL 聚合替换 EngageLab API 调用，实现汇总查询（D2 SQL 映射）
- [ ] 1.2 在同一方法中实现每日明细查询（D4 SQL），返回 daily 数组
- [ ] 1.3 百分比字段由后端自算（D3：delivered_percent / total_open_percent / open_percent，以 sent 为分母，sent=0 时返回 0）

## 2. 清理 EngageLab Stats 相关代码

- [ ] 2.1 删除 `engagelab.py` 中的 `get_stats_day()` 方法
- [ ] 2.2 删除 `tenant_query_service.py` 中的 `_stats_cache` 全局缓存及相关 import（`time` 等）
- [ ] 2.3 删除 `engagelab.py` 中 `engagelab_stats_base_url` 的引用（如仅被 stats 使用）

## 3. 验证

- [ ] 3.1 本地启动后端，调用 `/dashboard/email-stats` 接口，确认返回格式与之前一致
- [ ] 3.2 对比本地数据与 EngageLab 控制台数据，确认 webhook 追踪字段准确性
