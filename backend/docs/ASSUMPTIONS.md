# Assumptions

- 当前只交付 `backend/` 仓内闭环，不包含跨仓前端 Playwright 联调。
- 历史数据迁移只实现脚本骨架、映射说明和 dry-run 报告，不连接真实旧库。
- EngageLab 正式发送 API 细节未在蓝图中给出，因此发送适配器采用可配置 HTTP 出站协议，并统一归一到 `engagelab_message_id`。
- 评分任务采用 `scoring_jobs` 作为最小协调表，不引入消息队列。
- 租户团队管理以 `/team/users*` 兼容别名提供，服务能力仅限当前租户管理员。
