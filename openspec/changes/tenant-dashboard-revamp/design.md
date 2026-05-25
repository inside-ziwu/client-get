## Context

当前 tenant 端首页仅展示 4 个简单统计卡片（公司总数、优选客户、活跃计划、本月发送）+ 客户漏斗 + AI 状态，缺乏邮件发送/追踪的可视化监控能力。原项目（sysdev-ft-marketing）的管理后台首页提供了完整的邮件运营仪表盘，客户非常满意，需要 1:1 复刻到当前项目。

**现有基础**：
- `emails` 表已有完整追踪字段：`open_count`、`first_opened_at`、`soft_bounce`、`invalid_email`、`report_spam`、`unsubscribed`
- EngageLab webhook 已实时更新这些字段
- `tenant_messaging_service.py` 已有 `email_stats` 方法（全量统计，不支持日期范围）
- `tenant_ai_provider_service.py` 已有 OpenRouter 余额查询能力
- 前端已有 `StatCard` 组件和 dashboard API 模块

## Goals / Non-Goals

**Goals:**
- 1:1 复刻原项目首页的 6 个模块：日期选择器、发送统计、追踪统计、趋势图、计划概览、LLM余额+每日配额
- 所有统计数据从本地 `emails` 表查询（不调 EngageLab 外部 API）
- 保持现有代码架构风格一致

**Non-Goals:**
- 不修改 `emails` 表结构
- 不新增数据库迁移
- 不修改 EngageLab webhook 处理逻辑
- 不修改 admin 端

## Decisions

### D1: 数据源 — 本地 DB vs EngageLab API

**选择**：本地 `emails` 表聚合查询

**理由**：
- 当前项目已通过 webhook 实时同步所有邮件事件到 `emails` 表
- 本地查询延迟低、无外部依赖、支持租户隔离（RLS）
- 原项目调 EngageLab API 是因为它没有本地存储这些事件数据

**备选方案**：调用 EngageLab `stats_day` API — 需要额外处理 API 凭证管理，且无法按租户隔离（EngageLab 是全局账户）

### D2: 图表库 — recharts

**选择**：recharts

**理由**：
- 项目前端是 Next.js + React，recharts 是 React 生态最流行的图表库
- 支持 SSR 友好的 `ResponsiveContainer`
- 轻量级，API 简洁
- 原项目用 `@ant-design/charts`，但当前项目不用 Ant Design 体系

**备选方案**：@ant-design/charts — 会引入 Ant Design 依赖链，与 shadcn/ui 风格冲突

### D3: API 拆分策略

**选择**：4 个独立端点，各自独立获取

| 端点 | 数据源 | 刷新时机 |
|------|--------|---------|
| `GET /dashboard/email-stats` | emails 表 | 日期范围变化 |
| `GET /dashboard/plan-overview` | 多表联查 | 计划选择变化 |
| `GET /dashboard/daily-quota` | emails 表 | 页面加载 |
| `GET /dashboard/llm-balance` | OpenRouter API | 页面加载 |

**理由**：各模块数据源不同、刷新时机不同，独立端点便于前端按需请求和缓存管理。

### D4: email-stats 字段映射

基于 `emails` 表现有字段的聚合映射：

| 统计指标 | SQL 表达式 |
|---------|-----------|
| targets | `COUNT(*)` — 日期范围内所有邮件记录 |
| sent | `COUNT(*) FILTER (WHERE status NOT IN ('draft', 'pending', 'queued'))` |
| delivered | `COUNT(*) FILTER (WHERE status IN ('delivered', 'opened', 'clicked', 'replied'))` |
| invalid_email | `COUNT(*) FILTER (WHERE invalid_email = true)` |
| soft_bounce | `COUNT(*) FILTER (WHERE soft_bounce = true)` |
| billing | 等同 sent |
| total_opens | `COALESCE(SUM(open_count), 0)` |
| opens（独立打开） | `COUNT(*) FILTER (WHERE first_opened_at IS NOT NULL)` |
| report_spam | `COUNT(*) FILTER (WHERE report_spam = true)` |
| unsubscribe | `COUNT(*) FILTER (WHERE unsubscribed = true)` |

日期过滤条件：`WHERE tenant_id = :tenant_id AND created_at >= :start_date AND created_at < :end_date + 1 day`

每日明细使用 `GROUP BY DATE(created_at)` 聚合。

### D5: plan-overview 数据范围

当前项目的数据模型与原项目不同，做合理映射：

| 原项目指标 | 当前项目对应 |
|-----------|------------|
| keyword_count | `SELECT COUNT(*) FROM tenant_keywords WHERE tenant_id = :tid` |
| companies_collected | `SELECT COUNT(*) FROM tenant_companies WHERE tenant_id = :tid` |
| companies_cleaned（已评分） | `WHERE score IS NOT NULL` |
| contacts_total | `SELECT COUNT(*) FROM tenant_contacts WHERE tenant_id = :tid` |
| drafts（草稿数） | `SELECT COUNT(*) FROM emails WHERE plan_id = :pid AND status = 'draft'` |
| sent（已发送） | `SELECT COUNT(*) FROM emails WHERE plan_id = :pid AND status NOT IN ('draft','pending','queued')` |

当 `plan_id` 未指定时，返回租户级汇总。

### D6: daily-quota 实现

**选择**：从 `domain_warmup_status` 表获取该租户所有域名的 `daily_limit` 之和，已用量从 `emails` 表统计今日已发送数。

**理由**：当前项目按域名做发信暖域，每个域名有独立 daily_limit，汇总即为租户级每日配额。

### D7: 前端首页布局

保持与原项目一致的视觉结构，使用 Tailwind CSS + shadcn/ui 组件实现：

```
┌─────────────────────────────────────────────┐
│ 仪表盘标题 + 日期范围选择器                      │
├───────┬───────┬───────┬───────┬───────┬───────┤
│目标数  │已发送  │已送达  │无效邮箱│软退信  │计费数 │  发送统计
├───────┼───────┼───────┼───────┼───────┼───────┤
│打开次数│打开率  │独立打开│独立打开│举报垃圾│退订   │  追踪统计
│       │       │数     │率     │邮件   │      │
├───────────────────────────────────────────────┤
│ 趋势图（堆叠柱状图）                             │
├──────────────────────┬────────────────────────┤
│ 计划概览              │ LLM余额 + 每日配额       │
└──────────────────────┴────────────────────────┘
```

### D8: 统计卡片视觉层级（设计审查 D2）

**选择**：保持原项目等宽平铺风格，仅用颜色区分指标类型

**理由**：客户明确表示满意原项目风格，1:1 复刻零风险。视觉优化可作为后续迭代。

**卡片颜色映射**（复用原项目彩色数字风格）：

| 发送统计 | 颜色 | 追踪统计 | 颜色 |
|---------|------|---------|------|
| 目标数 | 蓝 text-blue-600 | 打开次数 | 蓝 text-blue-600 |
| 已发送 | 蓝 text-blue-600 | 打开次数率 | 绿 text-green-600 |
| 已送达(%) | 绿 text-green-600 | 独立打开数 | 蓝 text-blue-600 |
| 无效邮箱 | 橙 text-orange-500 | 独立打开率 | 绿 text-green-600 |
| 软退信 | 紫 text-purple-600 | 举报垃圾邮件 | 红 text-red-600 |
| 计费数 | 蓝 text-blue-600 | 退订 | 红 text-red-600 |

### D9: 交互状态覆盖（设计审查 D3）

每个 UI 模块的 4 种状态定义：

| 功能 | 加载中 | 空数据 | 错误 | 成功 |
|------|--------|--------|------|------|
| 发送统计 | 6 卡片骨架屏（Skeleton） | 全部显示 0 + 灰色文字 | 卡片区显示"加载失败"+ 重试按钮 | 正常数值 + 彩色文字 |
| 追踪统计 | 同上 | 同上 | 同上 | 同上 |
| 趋势图 | 300px 灰色矩形骨架 | 空状态文字"暂无发送数据" | "加载失败，点击重试" | 堆叠柱状图 |
| 计划概览 | 骨架屏 | "暂无计划，去创建" + 跳转按钮 | "加载失败"+ 重试 | 指标卡片 + 选择器 |
| 每日配额 | 骨架屏 | "未配置域名" | "查询失败"+ 重试 | 进度条 + 数值 |
| LLM 余额 | 骨架屏 | "未配置 OpenRouter" | "查询失败" | 金额 + 状态徽章 |
| 日期选择器 | 无（本地状态） | 无 | 无 | 按钮高亮 + 日期显示 |

### D10: 日期切换刷新策略（设计审查 D6）

**选择**：保留旧数据 + 顶部 loading 条

**实现**：React Query 的 `placeholderData: keepPreviousData`，切换日期时旧数据保留并半透明显示，新数据到达后替换。顶部显示细长 loading 进度条（类似 NProgress）。

**理由**：零闪烁体验，一行配置。避免每次切换都显示骨架屏导致的视觉割裂。

### D11: 响应式断点（设计审查 D5）

| 视口 | 统计卡片列数 | 趋势图 | 底部卡片 |
|------|------------|--------|---------|
| 桌面 ≥1280px | 6 列 (`xl:grid-cols-6`) | 满宽 | 2 列 (`lg:grid-cols-2`) |
| 平板 ≥768px | 3 列 (`md:grid-cols-3`) | 满宽 | 1 列 |
| 手机 <768px | 2 列 (`grid-cols-2`) | 满宽（ResponsiveContainer 自适应） | 1 列 |

### D12: 现有组件复用（设计审查 Pass 5）

- `StatCard`（shared-ui）：复用现有组件，通过 `className` 传入颜色 class 控制数值颜色，不传 `icon` 匹配原项目风格
- `Card` / `CardHeader` / `CardTitle` / `CardContent`：趋势图、计划概览、配额余额的容器
- `Progress`（shared-ui）：每日配额进度条
- `Badge`（shared-ui）：LLM 余额状态标签
- `queryKeys` helper（shared-api）：所有 React Query queryKey 必须使用 `queryKeys.dashboard.*` 格式

### D13: DESIGN.md 缺失

项目无 DESIGN.md。本次变更以原项目截图为视觉参考，使用 shadcn/ui + Tailwind CSS 现有设计系统实现。建议后续创建项目级 DESIGN.md 记录设计规范。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| emails 表数据量大时聚合查询慢 | emails 表已按 created_at 分区，日期范围查询可利用分区裁剪；首次加载可限定近 30 天 |
| OpenRouter 余额查询可能超时 | 复用现有 `TenantAiProviderService` 的缓存机制（60s TTL） |
| recharts 新依赖增加包体积 | recharts 支持 tree-shaking，仅引入 BarChart 相关组件 |
| plan-overview 字段映射与原项目不完全一致 | 原项目有 AB 评级等概念，当前项目用 score；映射为语义等价即可 |

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 0 | — | — |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | CLEAN (FULL) | score: 5/10 → 8/10, 6 decisions |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **UNRESOLVED:** 0
- **VERDICT:** Design review CLEARED. eng review required.
