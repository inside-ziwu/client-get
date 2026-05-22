# TODOS

## Review

（Eng Review v3 D7：原有 2 项 + Codex 新增 1 项，全部纳入当前 change scope，见 Design D12/D13/D14）

## Backlog

- **搭建前端测试基础设施**：tenant 前端（`frontend/apps/tenant/`）目前没有任何测试框架（无 vitest/jest/playwright）。随着前端复杂度增长（登录跳转、RequireAuth 保护、表单交互等），缺乏自动化测试会成为回归风险。建议安装 vitest + testing-library，优先覆盖 auth 流程和路由保护逻辑。（来源：fix-second-admin-onboarding-loop 工程审查）

## Completed
