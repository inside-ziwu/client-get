## Why

客户对原项目（sysdev-ft-marketing）的管理后台首页非常满意，当前 tenant 端首页过于简单（仅 4 个统计卡片 + 客户漏斗 + AI 状态），无法满足日常运营监控需求。需要 1:1 复刻原项目首页的邮件发送统计、追踪统计、趋势图、计划概览、LLM 余额和每日配额等完整仪表盘能力。

## What Changes

- **新增**：日期范围选择器（今天/昨天/近7天/近30天 + 自定义日期）
- **新增**：发送统计模块 — 6 个指标卡片（目标数、已发送、已送达+送达率、无效邮箱、软退信、计费数）
- **新增**：追踪统计模块 — 6 个指标卡片（打开次数+打开次数率、打开次数率、独立打开数、独立打开率、举报垃圾邮件、退订）
- **新增**：发送趋势图 — 堆叠柱状图（已发送、已送达、打开 三条 category）
- **新增**：计划概览模块 — 计划选择器 + 统计指标
- **新增**：LLM 余额 + 每日发送配额并排卡片
- **新增**：后端 4 个 Dashboard API（email-stats、plan-overview、daily-quota、llm-balance）
- **移除**：现有首页的客户漏斗和 AI 状态模块（被新模块替代）
- **新增**：前端引入 recharts 图表库

### 关键设计决策

原项目通过调用 EngageLab 外部 API (`stats_day`) 获取发送/追踪统计。当前项目已通过 webhook 实时记录所有邮件事件到 `emails` 表（`open_count`、`soft_bounce`、`invalid_email`、`report_spam`、`unsubscribed` 字段完备），因此直接从本地 DB 查询，不调外部 API，数据更准确且延迟更低。

## Non-Goals

- 不修改现有 EngageLab webhook 处理逻辑
- 不修改 emails 表结构（已有字段完全满足需求）
- 不新增数据库迁移（所有统计基于现有表的聚合查询）
- 不修改 admin 端首页
- 不引入新的外部 API 调用（email-stats 使用本地 DB，不调 EngageLab stats_day）

## Capabilities

### New Capabilities

- `dashboard-email-stats`: 邮件发送统计与追踪统计能力 — 支持按日期范围查询汇总和每日明细
- `dashboard-plan-overview`: 计划维度概览统计 — 按计划聚合关键词、公司、联系人、邮件等指标
- `dashboard-quota-balance`: 每日发送配额和 LLM 余额查询能力

### Modified Capabilities

（无现有 spec 的需求级变更）

## Impact

| 影响范围 | 变更内容 |
|---------|---------|
| 后端路由 | `backend/app/api/tenant/core.py` — 新增 4 个 dashboard 端点 |
| 后端服务 | `backend/app/services/tenant_query_service.py` — 新增 email_stats_by_date_range、plan_overview、daily_quota、llm_balance 方法 |
| 前端首页 | `frontend/apps/tenant/src/app/(dashboard)/page.tsx` — 完全重写 |
| 前端 API 层 | `frontend/packages/shared-api/src/tenant/dashboard.ts` — 新增 4 个 API 方法 |
| 前端类型 | `frontend/packages/shared-types/src/api.ts` — 新增响应类型定义 |
| 前端依赖 | `frontend/apps/tenant/package.json` — 新增 recharts |
| 数据库 | 无变更（所有统计基于 emails、sending_plans、tenant_companies 等现有表的聚合查询） |

### 依赖顺序

1. 后端 API（无前端依赖）
2. 前端类型 + API 层（依赖后端 API 定义）
3. 前端页面（依赖前端 API 层 + recharts）
