## Why

Tenant 端设置页面当前存在加载失败问题，影响租户管理员进入关键词、评分、OpenRouter、团队等配置入口。该问题会阻断租户完成基础配置，也会让已有设置能力在实际使用中不可达。

## What Changes

- 修复 Tenant 设置模块加载失败的根因，确保设置根入口与菜单下各子页面可正常进入。
- 为设置页增加必要的加载、空态与错误态处理，避免单个接口失败导致整个设置页面不可用。
- 补齐与设置页加载链路匹配的验证，覆盖路由渲染、关键接口调用与失败回退。
- 不改变现有设置项的业务语义、权限边界或配置保存规则。

## Capabilities

### New Capabilities

- `tenant-settings-page-availability`: 约束 Tenant 设置根入口及各子页面在正常与失败条件下的可访问性、加载态和错误态。

### Modified Capabilities

无。

## Impact

- 前端：`frontend/apps/tenant/src/layouts/TenantLayout.tsx`、`frontend/apps/tenant/src/router.tsx`、`frontend/apps/tenant/src/pages/Settings/*` 及相关 hooks/API 调用。
- 共享前端包：可能涉及 `frontend/packages/shared-api`、`frontend/packages/shared-hooks` 中设置页依赖的 API client、query key 或权限判断。
- 后端：仅当加载失败根因来自设置相关 API 响应不兼容时，才最小范围调整 `backend/app/api/tenant/*` 或对应 schema/service。
- 验证：Tenant 前端类型检查/构建、相关单元测试或页面级 smoke 测试；若触及后端 API，同步运行后端对应测试。
