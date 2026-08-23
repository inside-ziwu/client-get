# 类型安全与前后端契约

> 事实来源：`packages/shared-types/src/{api,models,enums,auth}.ts`、`packages/shared-api/src/{admin,tenant}/*.ts`、issue #51。

## 现状

- `shared-types` 全部**手写**，没有 OpenAPI 生成（T-11 明确不做），与后端 Pydantic 模型之间**没有编译期契约**，已出现过漂移（#51）。
- 门禁只有 `pnpm type-check`（各包 `tsc`）；没有 eslint（#50）。

## 规则

- 后端改响应结构 / 新字段 / 枚举取值 → **同一 PR** 改 `shared-types`（`models.ts` 领域模型、`api.ts` 响应壳与筛选参数、`enums.ts`）和 `shared-api` 对应函数的泛型。
- 响应壳固定：`ApiResponse<T> = { data: T }`、`PaginatedResponse<T> = { data: T[]; pagination: { cursor, has_more, total? } }`、`ApiError = { error: { code, message, details? } }`。API 函数写成 `client.get<PaginatedResponse<T>>(path, { params })`，调用方从 `.data.data` 取。
- 字段名与后端保持 snake_case（`published_at`、`tenant_id`），不在前端转 camelCase。
- 可空字段用 `?:`；枚举用字符串字面量联合（`'rss' | 'website' | 'manual'`），与后端 `Literal` / CHECK 一致。
- 不用 `any`；遇到存量 `unknown[]`（如 `IntelligenceSource.industry_tags`）在触碰时收紧。
- `DataTableColumn<T>` 的 `value` 必须是 `T` 的键，`format` / `render` 的入参按列类型标注。

## 常见错误

- 只改了 `shared-api` 函数路径没改返回泛型，页面拿到 `unknown`。
- 后端删字段前端仍引用：字段是可选的，type-check 通过，运行时显示 `-`——删字段要 grep 前端引用。
