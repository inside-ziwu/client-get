## 1. 重写后端 email_stats_by_date_range

- [x] 1.1 重写 `tenant_query_service.py` 的 `email_stats_by_date_range` 方法：用本地 `emails` 表 SQL 聚合替换 EngageLab API 调用，实现汇总查询（D2 SQL 映射）（提交 79dba50）
- [x] 1.2 在同一方法中实现每日明细查询（D4 SQL），返回 daily 数组
- [x] 1.3 百分比字段由后端自算（D3 修订版：delivered_percent 以 sent 为分母；total_open_percent / open_percent 以 delivered 为分母，见 544820f 口径变更；分母为 0 时返回 0）

## 2. 清理 EngageLab Stats 相关代码

- [x] 2.1 删除 `engagelab.py` 中的 `get_stats_day()` 方法（2026-07-02 grep 核实无残留）
- [x] 2.2 删除 `tenant_query_service.py` 中的 `_stats_cache` 全局缓存及相关 import（2026-07-02 grep 核实无残留）
- [x] 2.3 删除 `engagelab.py` 中 `engagelab_stats_base_url` 的引用（2026-07-02 grep 核实无残留）

## 3. 验证

- [x] 3.1 本地启动后端，调用 `/dashboard/email-stats` 接口，确认返回格式与之前一致（路由层端到端测试 a874cdd 覆盖 13 字段完整性；功能已上线生产运行）
- [x] 3.2 对比本地数据与 EngageLab 控制台数据，确认 webhook 追踪字段准确性（近期生产统计无异常反馈，用户 2026-07-02 确认视为通过）

## 4. 测试对齐（2026-07-02 补录）

- [x] 4.1 `test_dashboard_email_stats.py::test_percentage_calculation` 期望值对齐 544820f 口径（total_open_percent/open_percent 以 delivered 为分母），全量 pytest 不再需要 --ignore 该文件
- [x] 4.2 新增 `test_delivered_zero_no_division_error`：delivered=0 且 sent>0 时打开率返回 0
