# 修复第二个管理员登录后新手引导死循环

## 问题

第二个管理员每次登录后都被跳转到新手引导页（`/onboarding`），无法进入工作台。

## 根因

`login/page.tsx:44` 将 `must_change_pwd` 和 `needs_onboarding` 混在同一个 `||` 条件中，统一跳转到 `/onboarding`：

```javascript
router.replace(me.must_change_pwd || me.needs_onboarding ? '/onboarding' : '/');
```

第二个管理员由 tenant_team_service 创建时 `must_change_pwd` 默认为 `true`，而 `/onboarding` 页面不处理改密码，也不清除 `must_change_pwd` 标记，导致每次登录都重复进入引导页。

## 两个标记的语义

- `must_change_pwd`：**用户级**强制动作，由系统在创建用户时设置，改密码后自动清除
- `needs_onboarding`：**租户级**引导状态，首个 admin 完成向导后清除
- 冲突时优先级：`must_change_pwd` > `needs_onboarding` > 正常进入

## 方案

1. **拆分登录跳转逻辑**：按优先级判断——先 `must_change_pwd` 跳改密码页，再 `needs_onboarding` 跳引导页，都不满足则进首页
2. **新建 `/force-change-password` 页面**：强制改密码的独立页面，调用已有的 `tenantApi.auth.changePassword` API
3. **`useAuthStore` 加 `mustChangePwd` 字段**：登录时从 `/auth/me` 响应写入，改密码成功后清除，logout 时一并清除
4. **RequireAuth 加防绕过检查**：如果 `mustChangePwd=true`，重定向到 `/force-change-password`
5. **`/force-change-password` 反向保护**：非 `mustChangePwd` 用户直接访问应跳走
6. **改密成功后的下一跳**：如果 `needs_onboarding=true` 则跳 `/onboarding`，否则进首页

## 影响范围

- `frontend/apps/tenant/src/app/login/page.tsx`（修改跳转逻辑）
- `frontend/apps/tenant/src/app/force-change-password/page.tsx`（新增）
- `frontend/packages/shared-hooks/src/useAuth.ts`（加 `mustChangePwd` 字段 + logout 清除）
- `frontend/apps/tenant/src/app/(dashboard)/layout.tsx`（RequireAuth 加检查）
- 后端：无需改动

## 不做的事

- 不改 `needs_onboarding` 的 tenant 级别语义——首个 admin 完成后即 false，本身逻辑无误
- 不改后端 API
- 不改 JWT payload 结构
- 不搭建前端测试基础设施（作为独立 TODO 跟踪）
