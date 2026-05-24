# TODOS

## Review

（Eng Review v3 D7：原有 2 项 + Codex 新增 1 项，全部纳入当前 change scope，见 Design D12/D13/D14）

## Backlog

- **搭建前端测试基础设施**：tenant 前端（`frontend/apps/tenant/`）目前没有任何测试框架（无 vitest/jest/playwright）。随着前端复杂度增长（登录跳转、RequireAuth 保护、表单交互等），缺乏自动化测试会成为回归风险。建议安装 vitest + testing-library，优先覆盖 auth 流程和路由保护逻辑。（来源：fix-second-admin-onboarding-loop 工程审查）

- **后端团队管理 API 保护**：`TenantTeamService` 的 `update_user` 和 `delete_user` 缺少两项保护：(1) 最后一个 admin 保护 — 可以把最后一个 admin 降级/禁用/删除，导致租户被永久锁定（无人能访问团队管理页面）；(2) 自操作拦截 — 后端不阻止 `user_id === actor_user_id` 的自删/自禁用/自降级操作（前端通过按钮隐藏防护，但 API 层可绕过）。建议在 `backend/app/services/tenant_team_service.py` 的 `update_user` 和 `delete_user` 中增加检查。（来源：team-management-crud-completion 工程审查 Codex outside voice，代码验证 confidence 10/10）

## Completed
