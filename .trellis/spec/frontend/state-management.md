# 状态管理与数据获取

> 事实来源：`packages/shared-api/src/query-keys.ts`、`client.ts`、`packages/shared-hooks/src/*`、`apps/tenant/src/app/(dashboard)/industry-news/page.tsx`。

## 三类状态

| 状态 | 方案 | 位置 |
|---|---|---|
| 服务端数据 | React Query（`@tanstack/react-query`） | 页面 / 组件内 `useQuery` / `useMutation` |
| 认证 | Zustand `useAuthStore`（persist → localStorage `auth-storage`） | `@shared/hooks` |
| 局部 UI | `useState` | 组件内 |

不引入其他全局 store；业务数据不放 Zustand。

## React Query 约定

- **queryKey 用 `queryKeys` 工厂**（`@shared/api`）：`queryKeys.industryNews.list(filters)` / `.filters()` / `.all()`，tenant 侧 key 自动带 `tid`（`['tenant', <tid>, 'industryNews', 'list', filters]`），切换租户不会串缓存。存量页面还有字面量 key（如 `['tenant', 'companies', 'list', …]`，T-17 收敛未做）——**新代码一律用工厂**，改到旧页面时顺手换。
- `queryFn` 直接调 `tenantApi.<feature>.list(...)`，返回 `.data.data`（`ApiResponse` 解包在页面做）。
- mutation 成功后 `queryClient.invalidateQueries({ queryKey: queryKeys.<feature>.all() })`，不手改缓存。已确认的例外：行业动态「点击标题置已读」不 invalidate 列表，用页面本地 `clickedIds` 显示已读态（失败时回滚并 toast），让开着「只看未读」时行不会在点击瞬间消失——这是页面状态，不是手改缓存。
- 翻页 / 筛选刷新期间保留旧行与分页上下文，表格用 `TableState` 显示"更新中…"——不要在 refetch 时清空列表。
- admin SSR：`createPrefetchPage` 的 key 必须与客户端 key 完全相同。

## 认证与权限

- `useAuthStore`：`token`、`payload`（`jwtDecode<JWTPayload>`）、`hasHydrated`、`mustChangePwd`、`setToken` / `logout` / `isExpired()`；页面守卫等 `hasHydrated` 为 true 后再判断，避免首屏误跳登录。
- 刷新令牌流程全部在 `client.ts` 拦截器里，页面不要自己处理 401。
- `usePermission()`：页面级（`settings.*` 仅 admin）与操作级（`company.create`、`plan.execute` 等 admin / operator）权限映射在 `usePermission.ts` 的 `PERMISSIONS` 表；前端只做展示控制，**后端 `require_tenant_roles` 才是真正的门**。

## 分页

- 游标分页用 `useCursorPagination`；页码分页在页面里 `page / pageSize` state + `Pagination` 组件。
- 列表请求参数与 `PaginationParams` / 各 `*Filters` 类型（`shared-types/api.ts`）对齐。

## 常见错误

- 用字面量 key 且漏掉 tenant scope，换租户后看到上一个租户的数据。
- mutation 后 `setState` 手动更新列表而不 invalidate，与服务端漂移。
- 在 `@shared/ui` 组件里调用 React Query 或路由（组件契约禁止，见 component-guidelines.md）。
