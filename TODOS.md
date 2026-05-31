# TODOS

## Review

（Eng Review v3 D7：原有 2 项 + Codex 新增 1 项，全部纳入当前 change scope，见 Design D12/D13/D14）

## Backlog

- **搭建前端测试基础设施**：tenant 前端（`frontend/apps/tenant/`）目前没有任何测试框架（无 vitest/jest/playwright）。随着前端复杂度增长（登录跳转、RequireAuth 保护、表单交互等），缺乏自动化测试会成为回归风险。建议安装 vitest + testing-library，优先覆盖 auth 流程和路由保护逻辑。（来源：fix-second-admin-onboarding-loop 工程审查）

- **收件人筛选扩展 contact_status NOT IN 包含 'invalid'**：发送节流与可靠性计划（R7）会将永久失败的联系人标记为 `contact_status='invalid'`，但 `tenant_messaging_service.py:2296` 的收件人筛选查询只过滤 `NOT IN ('unsubscribed', 'bounced')`。不扩展意味着未来 plan 会继续选中 invalid 联系人并重复失败，浪费配额和 API 调用。修改一行 SQL 即可：`NOT IN ('unsubscribed', 'bounced', 'invalid')`。（来源：sending-throttle-reliability 工程审查 D9，Codex outside voice 也独立发现此问题）

- **Webhook 回填定时任务**：EngageLab 在高并发发送时存在 webhook 回调丢失（5/29 发送 672 封，约 60% 的 delivered/bounced 回调未到达）。现已改为逐封节流发送，问题应不再出现。若再次出现 sent 状态滞留，将 `backend/scripts/backfill_email_status.py` 改造为每日定时任务，自动扫描前一天滞留的 sent 邮件并通过 EngageLab API 回填真实状态。（来源：2026-05-30 生产数据排查）

- **接通 OpenAPI 自动类型生成**：前端 `shared-types` 当前是手写的 TypeScript 类型定义（models.ts、api.ts、auth.ts 等），与后端 FastAPI 的 Pydantic schema 没有自动同步机制。任何后端字段变更都需要手动同步前端类型，容易遗漏导致运行时错误。建议用 `openapi-typescript` 从 FastAPI 自动导出的 OpenAPI spec 生成前端类型，替代手写的 `@shared/types`。（来源：技术栈统一辩论，Claude + Codex 共识）

- **提升后端测试覆盖率**：当前 137 个测试函数覆盖 230 个 API 端点（覆盖率 < 60%），426 处裸 SQL 调用缺乏回归保障。优先补充覆盖：多租户 RLS 隔离、JWT 认证刷新流程、sending worker 邮件发送逻辑、关键 service 层的 SQL 查询正确性。（来源：技术栈统一辩论，Codex 代码统计）

- **后端团队管理 API 保护**：`TenantTeamService` 的 `update_user` 和 `delete_user` 缺少两项保护：(1) 最后一个 admin 保护 — 可以把最后一个 admin 降级/禁用/删除，导致租户被永久锁定（无人能访问团队管理页面）；(2) 自操作拦截 — 后端不阻止 `user_id === actor_user_id` 的自删/自禁用/自降级操作（前端通过按钮隐藏防护，但 API 层可绕过）。建议在 `backend/app/services/tenant_team_service.py` 的 `update_user` 和 `delete_user` 中增加检查。（来源：team-management-crud-completion 工程审查 Codex outside voice，代码验证 confidence 10/10）

## Completed
