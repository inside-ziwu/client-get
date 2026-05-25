## 1. 后端：邮件统计 API

- [x] 1.1 在 `tenant_query_service.py` 新增 `email_stats_by_date_range(conn, tenant_id, start_date, end_date)` 方法 — 返回 summary（targets/sent/delivered/delivered_percent/invalid_email/soft_bounce/billing/total_opens/total_open_percent/opens/open_percent/report_spam/unsubscribe）+ daily 数组（date/sent/delivered/opens），数据源为 emails 表按 tenant_id + created_at 日期范围聚合
- [x] 1.2 在 `backend/app/api/tenant/core.py` 新增路由 `GET /dashboard/email-stats`，接受 start_date/end_date 查询参数（可选，默认近30天），调用 1.1 的方法，使用 `_parse_filter_date` 校验日期格式
- [ ] 1.3 手动验证：启动后端，curl 测试 `GET /t/{slug}/api/v1/dashboard/email-stats` 返回正确 JSON 结构

## 2. 后端：计划概览 API

- [x] 2.1 在 `tenant_query_service.py` 新增 `plan_overview(conn, tenant_id, plan_id=None)` 方法 — 返回 keyword_count、companies_collected、companies_scored、contacts_total、emails_drafted、emails_sent、plans 列表（id + name），数据源为 tenant_keywords + tenant_companies + tenant_contacts + emails + sending_plans 表
- [x] 2.2 在 `backend/app/api/tenant/core.py` 新增路由 `GET /dashboard/plan-overview`，接受可选 plan_id 参数
- [ ] 2.3 手动验证：curl 测试无 plan_id（租户汇总）和有 plan_id（单计划）两种情况

## 3. 后端：每日配额 + LLM 余额 API

- [x] 3.1 在 `tenant_query_service.py` 新增 `daily_quota(conn, tenant_id)` 方法 — 从 domain_warmup_status 表汇总 daily_limit，从 emails 表统计今日已发送数，返回 limit/used/remaining
- [x] 3.2 在 `tenant_query_service.py` 新增 `llm_balance(conn, tenant_id)` 方法 — 复用 `TenantAiProviderService.get_config()` 获取 OpenRouter 余额，返回 is_configured/balance_remaining/usage/limit/balance_status
- [x] 3.3 在 `backend/app/api/tenant/core.py` 新增路由 `GET /dashboard/daily-quota` 和 `GET /dashboard/llm-balance`
- [ ] 3.4 手动验证：curl 测试两个端点返回正确数据

## 4. 前端：类型定义 + API 层 + queryKeys

- [x] 4.1 在 `frontend/packages/shared-types/src/api.ts` 新增类型：`EmailStatsSummary`、`EmailStatsDaily`、`EmailStatsResponse`、`PlanOverviewResponse`、`DailyQuotaResponse`、`LlmBalanceResponse`
- [x] 4.2 在 `frontend/packages/shared-api/src/tenant/dashboard.ts` 新增 4 个 API 方法：`emailStats(params)`、`planOverview(params)`、`dailyQuota()`、`llmBalance()`
- [x] 4.3 在 `frontend/packages/shared-api/src/query-keys.ts` 新增 `dashboard.emailStats(params)`、`dashboard.planOverview(params)`、`dashboard.dailyQuota()`、`dashboard.llmBalance()` queryKey 定义（使用 tenantScope）
- [x] 4.4 验证：`pnpm -F @shared/types type-check` 和 `pnpm -F @shared/api type-check` 通过

## 5. 前端：安装 recharts + 趋势图组件

- [x] 5.1 在 tenant app 安装 recharts：`pnpm -F tenant add recharts`
- [x] 5.2 新建趋势图组件 `frontend/apps/tenant/src/components/pages/dashboard/email-trend-chart.tsx` — 使用 recharts 的 BarChart + Bar（stacked），三个 category：已发送(#1677ff)、已送达(#52c41a)、打开(#fa8c16)，高度 300px，图例顶部，ResponsiveContainer 包裹自适应宽度。空数据时显示"暂无发送数据"文字。

## 6. 前端：首页重写

- [x] 6.1 新建日期范围选择器组件 `frontend/apps/tenant/src/components/pages/dashboard/date-range-picker.tsx` — 4 个快捷预设按钮（今天/昨天/近7天/近30天）+ 日期输入框，默认选中近30天。按钮用 shadcn Button variant="outline"，选中时 variant="default"
- [x] 6.2 新建统计卡片组 `frontend/apps/tenant/src/components/pages/dashboard/stats-section.tsx` — 发送统计（6卡片）+ 追踪统计（6卡片），每组带节标题和图标。复用 StatCard 组件，通过 className 传入彩色文字（见 design.md D8 颜色映射表）。响应式：`grid-cols-2 md:grid-cols-3 xl:grid-cols-6`。加载态：6 个 Skeleton 卡片；错误态：重试按钮
- [x] 6.3 新建计划概览组件 `frontend/apps/tenant/src/components/pages/dashboard/plan-overview.tsx` — 计划选择下拉框 + 6 个统计指标。空状态："暂无计划" + 跳转到创建计划的按钮
- [x] 6.4 新建配额余额组件 `frontend/apps/tenant/src/components/pages/dashboard/quota-balance.tsx` — 每日发送配额（Progress 进度条 + 剩余量，颜色：<80% 绿、80-95% 橙、>95% 红）+ LLM 余额（金额 + Badge 状态），并排两列 `lg:grid-cols-2`。空状态分别为"未配置域名"和"未配置 OpenRouter"
- [x] 6.5 重写 `frontend/apps/tenant/src/app/(dashboard)/page.tsx` — 组装所有模块：页面标题 + 日期选择器 → 发送统计 → 追踪统计 → 趋势图 → 计划概览 + 配额余额。使用 queryKeys helper 管理 React Query queryKey。email-stats 查询启用 `placeholderData: keepPreviousData`（design.md D10），切换日期时保留旧数据 + 顶部 loading 细条
- [x] 6.6 验证：`pnpm -F tenant build` 构建通过

## 7. 集成验证

- [ ] 7.1 启动后端 + 前端 dev server，手动验证首页 6 个模块完整展示
- [ ] 7.2 验证日期切换后发送统计、追踪统计、趋势图均正确刷新（旧数据保留 + loading 条）
- [ ] 7.3 验证计划选择器切换后概览数据正确刷新
- [ ] 7.4 验证无数据时各模块的空状态展示（骨架屏、空提示文字、重试按钮）
- [ ] 7.5 验证响应式：桌面 6 列 → 平板 3 列 → 手机 2 列卡片正确切换
