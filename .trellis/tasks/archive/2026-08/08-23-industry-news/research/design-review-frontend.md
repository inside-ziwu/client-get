# Research: design.md §5 / implement.md A10–A12、B3 前端契约核证

- **Query**: 逐条核对 design.md §5（前端）与 implement.md A10–A12、B3 的断言是否与 `frontend/` 真实组件契约相符
- **Scope**: internal（只读；未改任何产品代码）
- **Date**: 2026-08-23
- **事实来源**: `frontend/packages/shared-ui/src/components/{filter-bar,data-table,list-page,table-state,pagination,switch,badge,button}.tsx`、`shared-ui/src/index.ts`、`shared-ui/src/theme/{tailwind-preset.ts,globals.css}`、`shared-api/src/{client.ts,query-keys.ts,index.ts,tenant/*,admin/*}`、`shared-types/src/{api,models,enums}.ts`、`apps/tenant/src/app/(dashboard)/{companies,intelligence}/page.tsx`、`apps/tenant/src/components/layout/navigation.ts`、`apps/tenant/src/lib/{api,format}.ts`、`apps/admin/src/app/(dashboard)/{intelligence-sources,ai-config}/`、`apps/admin/src/lib/*`、`apps/admin/src/components/layout/navigation.ts`、`apps/tenant/test/`、`.trellis/spec/frontend/*.md`、axios 1.15.0 `toFormData.js`、backend `app/core/responses.py`、`app/services/admin_config_service.py`

结论符号：**成立** = 与代码一致可照写；**需改** = 方向对但写法/文案/类型要调整；**不成立** = 代码不支持该写法。

---

## ① 核对表

### 1. FilterBar：控件类型、布尔开关、draft → applied

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| schema 支持类别多选、来源多选 | 成立 | `filter-bar.tsx:66-72` `kind: 'multiSelect'`，`name` 必须是 `readonly string[]` 类型的键（`KeysMatching<T, readonly string[]>`）；`options: {label,value}[]`、`optionState?: 'ready'|'loading'|'empty'`、`searchPlaceholder?` | draft 里 `categories: string[]`、`sources: string[]`（来源用 `id` 作 value、`name` 作 label） |
| 语种单选 | 成立 | `filter-bar.tsx:60-65` `kind: 'select'`，`name` 必须是 `string` 键；未选显示 `placeholder ?? '不限'`，内置「不限」项清空（`:213-215`） | `lang: string`（`'' | 'en' | 'zh-CN' | 'zh-TW'`） |
| 「只看未读」布尔开关 | **不成立（需改表示法）** | `FilterDraftValue = string \| readonly string[]`（`filter-bar.tsx:18`，spec `component-guidelines.md:58,122`）——draft 值**不允许 boolean**；`FilterField` 没有 `'switch'`/`'boolean'` kind（`:55-77`） | 二选一：(a) `kind: 'custom'`（`:73-77,142-155`）把 `unread_only` 存成字符串 `'' \| '1'`，`render` 里放 `<Switch aria-label="只看未读" checked={values.unread_only === '1'} onCheckedChange={v => setValue('unread_only', v ? '1' : '')} disabled={disabled} />`（Radix Switch 是 `type="button"`，不会触发表单提交）；(b) 更省事且不用 custom：`kind: 'select'`，options `[{value:'1',label:'只看未读'}]`，placeholder「全部」。两者都随「查询」才生效。若产品要求开关**即时生效**，则不该进 FilterBar（契约：输入只改 draft，`component-guidelines.md:121`），应放在 `ListPage` 的 `filters` 插槽里 FilterBar 下方的独立容器（先例：`companies/page.tsx:162-181` 在 FilterBar 下叠了一个 banner），自己持有 applied 状态并 `setPage(1)` |
| draft → applied：查询 / 重置 | 成立 | `FilterBar` 受控：`values` + `onChange(next)`（`:267-269`）；表单 submit 调 `onSubmit(values)`（`:316-321`）；「重置」只调 `onReset`（`:295-303`），**不会**自己清 draft；Enter 等同查询。页面侧先例 `companies/page.tsx:76-87`：`handleApplyFilters` 设 applied + `setPage(1)`；`handleResetFilters` 同时清 draft、applied、page | design §5.1「draft → applied 按 FilterBar 契约」可照写；`onReset` 里必须自己 `setDraft(EMPTY)` + `setApplied(EMPTY)` + `setPage(1)` |
| 其他 props | 成立 | `FilterBarProps`（`:79-91`）：`isSubmitting`、`appliedCount`、`layout: 'grid' \| 'compact'`（默认 grid，`lg:grid-cols-4`，4 个字段恰好一行，`:263-266`）、`collapseAdvanced`、`optionStateMode`、`actionsPlacement` | 4 个字段用默认 `grid` 即可；选项来自 `/industry-news/filters` 时给 multiSelect/select 传 `optionState`（先例 `company-list-filter-bar.tsx:147-148`） |

### 2. DataTable 列定义：width / type / render / format / 行点击 / 行级样式

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| `width` 预设值 | 成立 | `component-width.ts:1-3`：`WidthPreset = 'small' \| 'medium' \| 'large'`，`WidthSpec = WidthPreset \| { custom: number }`；未声明默认 `medium`（`data-table.tsx:93`）。**实际像素**：`globals.css:62-64` small=64px / medium=96px / large=144px（commit `7ffc926` 2026-07-24 收紧；spec `component-guidelines.md:217` 仍写 96/144/224，已漂移，见 ③） | design 的 `large/medium/small` 三档可照写；标题列 `large` 与公司列表「公司名」同档 |
| `type` 取值 | 成立 | `data-table.tsx:26-65`：`'text' \| 'number'`（`render?`、`format?`）、`'date'`（**必须**提供 `format` 或 `render` 之一，`:32-44`）、`'status'`（`statusMap` + `render?`）、`'boolean'`（`getBooleanLabel` + `booleanMode: 'readOnly' \| 'interactive'`）、`'actions'`（`render` 必填，全表只能一个，`:216`） | 标题列写 `type: 'text', value: 'title', render`；时间列 `type: 'date', value: 'time', format` |
| `render` / `format` 签名与优先级 | 成立 | `render: (row: T) => ReactNode`；`format: (value: unknown, row: T) => ReactNode`；`value: keyof T \| ((row: T) => unknown)`（`:22-24`）；优先级 `render > format > 类型默认`（`:171-172`，spec `:234`） | `format` 的 `value` 是 `unknown`，需 `value as string \| undefined`（先例 `intelligence/page.tsx:60`） |
| 「点击标题新窗口打开并置已读」应放 `render` 里的 `<a>`/`<button>` 还是 `onRowClick` | 成立（只能放 `render`） | `DataTableProps`（`:74-85`）**没有** `onRowClick`；`<tr>` 的 className 固定（`:306`）；spec `component-guidelines.md:242`「首版不提供整行点击，详情入口使用有焦点态的显式链接或按钮」 | 标题列 `render` 返回 `<a href={row.url} target="_blank" rel="noopener noreferrer" onClick={() => markRead.mutate(row.id)} className=…>`（仓库先例 `admin/collection/customers/client-page.tsx:563-571`）。`<a>` 比 `<button>+window.open` 多拿到中键/Ctrl 点击与可访问名，且 Vitest 不必 mock `window.open`（见 10）。注意：自定义 `render` 会**失去**默认 `TruncatedText` 的截断 + Tooltip（`:110-151,174`），需自己加 `truncate`（先例 `intelligence/page.tsx:31`） |
| 行级样式钩子（已读/未读整行区分） | **不成立** | 无 `getRowClassName` / `rowClassName` 之类 prop（`:74-85`），`<tr className="h-10 border-b border-ui-border-soft last:border-b-0">` 写死（`:306`）；五件套 API 冻结（spec `:9,26`） | 已读/未读只能在**单元格**内区分（标题列 `render` 切换类名），design §5.1 正是这么写的，成立；不要为整行变色改 DataTable |
| `Tooltip` 截断（admin 地址列） | 成立 | `type: 'text'` 且不给 `render` 时自动 `TruncatedText`：溢出才挂 Tooltip（`:110-151`） | 地址列直接 `{ id:'url', type:'text', value:'url', width:'large' }`，不要写 render |
| 启用开关列 | 成立 | `type: 'boolean', booleanMode: 'interactive'` 渲染共享 `Switch`，带 `aria-label=getBooleanLabel(row)`、`disabled=isBooleanDisabled(row)`（`:185-194`）；先例 `admin/intelligence-sources/client-page.tsx:232-242` + `updatingIds` 集合（`:79,164-179`） | 照抄该先例；spec `:316`「pending 时 disabled 并保留当前视觉状态」 |

### 3. TableState：空态文案可定制性、loading / error / refreshing 传参

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| 空态文案「本实例尚未配置动态源」 | **不成立** | `TableStateSpec` 空态只有 `{ kind: 'empty'; filtered?: boolean; onResetFilters?: () => void }`（`table-state.tsx:3-6`），文案写死为 `暂无${entityName}` / `没有符合当前条件的${entityName}`（`:22`），无 `description`/`message` | 三条路：(a) **不经 TableState**：`filters.has_sources === false` 时不渲染 DataTable，在 `ListPage` children 位置渲染一个说明块（与 `companies/page.tsx:175` 那种 `rounded-ui-md border … text-ui-body` 容器同款）；(b) 向后兼容扩展：给 `empty` 变体加可选 `description?: string`（spec `component-guidelines.md:26` 允许「不改变默认行为的向后兼容可选项」，但要同步改 spec §TableState 契约文本 + 两端调用方不受影响）；(c) 用 `kind:'error'`+`description`——语义错误，不建议。推荐 (a)，零契约改动 |
| 「暂无动态」 | 成立 | `entityName="动态"` → `暂无动态`；同时 aria-label 变 `动态列表`（`data-table.tsx:249`）、loading `正在加载动态…`（`table-state.tsx:18`）、error `动态加载失败`（`:33`） | 若嫌「正在加载动态…」拗口可用 `entityName="行业动态"`（→「暂无行业动态」「行业动态列表」），测试断言随之 |
| 「没有符合筛选的动态」 | 需改 | 真实文案是 `没有符合当前条件的${entityName}`（`:22`） | design / 测试用例改成「没有符合当前条件的动态」；传 `filtered: appliedCount > 0, onResetFilters`（先例 `companies/page.tsx:149`） |
| loading / error / refreshing 传参 | 成立 | 页面算一个 `tableState`：`isLoading → {kind:'loading'}`；`isError → {kind:'error', description:'请检查网络后重试', onRetry: refetch}`；`items.length===0 → {kind:'empty',…}`；否则 `undefined`（先例 `intelligence/page.tsx:84-90`、`companies/page.tsx:144-150`）。`state` 非空时**不渲染数据行**（`data-table.tsx:301-302`）。刷新用 `isRefreshing={q.isFetching && !q.isLoading}`，表头下出现「更新中…」+ `aria-busy`（`:237-246`） | 照写；错误描述面向用户，不透传异常（spec `:270`） |
| 「refetch 期间保留旧行（五件套契约）」 | 需改（design 漏了前提） | 翻页/筛选会换 queryKey，不加 `placeholderData: keepPreviousData` 时 `isLoading` 为 true、旧行消失（先例 `companies/page.tsx:60-64` 加了；`intelligence/page.tsx` 因无分页没加）；spec `state-management.md:20` | 列表 `useQuery` 加 `placeholderData: keepPreviousData`；`Pagination isDisabled={listQuery.isLoading}` |

### 4. ListPage 插槽、Pagination props、useCursorPagination

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| ListPage 标题 / 描述 / 头部操作区 | 成立 | `ListPageProps`（`list-page.tsx:4-13`）：`title`、`description?`、`primaryAction?`（header 右侧，`:34`）、`filters?`、`selectionToolbar?`、`children`、`pagination?` | admin「立即抓取」→ `primaryAction={<Button …>立即抓取</Button>}`；spec `:47`「primaryAction 是页面唯一主操作」、`:236`「非新增语义不用 CreateButton」——用普通 `Button`（`variant` 默认或 `outline`） |
| Pagination props「page / pageSize / total / onChange」 | 需改（写法） | 真实签名 `pagination.tsx:9-32`：`value: { page, pageSize }` + `onChange(next: {page,pageSize})` + 必填 `mode`；`mode:'total'` 时 `total: number`、`showPageJump?`；`mode:'unknownTotal'` 时 `hasNextPage`；`pageSizeOptions` 默认 `[20,50,100]`（`:34`）；`isDisabled` | 写成 `<Pagination mode="total" total={total} value={{page,pageSize}} onChange={next => {setPage(next.page); setPageSize(next.pageSize);}} isDisabled={listQuery.isLoading} />`（先例 `companies/page.tsx:189-202`）；页码分页完全支持，不是只有游标 |
| `useCursorPagination` 是否与页码分页冲突 | 成立（无冲突） | `shared-hooks/src/useCursorPagination.ts:4-15` 只是 `useInfiniteQuery` 封装（`cursor`/`has_more`），仓库内**零消费方**；spec `state-management.md:31`「页码分页在页面里 page / pageSize state + Pagination 组件」 | 不用它 |

### 5. 设计令牌类名与 Badge

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| `text-ui-foreground` | 成立 | 颜色 token `tailwind-preset.ts:44` → `--ui-foreground: #111111`（`globals.css:27`）；用法 `companies/page.tsx:112`、`table-state.tsx:33` | — |
| `text-ui-body-strong` | 成立（注意是字号/字重，不是颜色） | `fontSize` `tailwind-preset.ts:69` = 14px/500；用法 `intelligence/page.tsx:31`、`table-state.tsx:33` | 未读标题 `text-ui-body-strong text-ui-foreground` 两个类同时写（一个管字重一个管色） |
| `text-ui-muted-foreground` | 成立 | `tailwind-preset.ts:46` → `#6b7280`（`globals.css:29`）；用法 `data-table.tsx:242`、`intelligence/page.tsx:32` | 已读标题用它；对比未读 `#111111` 差异明显 |
| `text-ui-caption` | 成立 | `fontSize` `tailwind-preset.ts:70` = 12px/500；用法 `data-table.tsx:242` `text-ui-caption text-ui-muted-foreground` | `target_domain` 灰字照 design 写 |
| `text-ui-danger-foreground` | 成立 | `tailwind-preset.ts:58` → `#b91c1c`（`globals.css:41`）；用法 `companies/page.tsx:175,341` | 错误计数 >0 时套在 `render` 的 `<span>` 上 |
| Badge `tone` / `variant` | 成立 | `badge.tsx:19` `BadgeTone = 'neutral' \| 'success' \| 'warning' \| 'info' \| 'danger'`；`BadgeProps` 为 `tone` 与 legacy `variant`（`default/secondary/outline/destructive`，`:7-12`）二选一（`:31-35`）；用法 `admin/email-templates/client-page.tsx:158` `tone="neutral"`；spec `quality-guidelines.md:22` 语义色走 tone | 类别列 `<Badge tone="neutral">`；或直接 `type:'status', statusMap:{}`——未知值自动回退 neutral Badge（`data-table.tsx:176-179`），但类别是客户自定文本，用 `render` 更直观 |

### 6. `createPrefetchPage` / `serverApi.get` 签名、key 一致性、`queryKeys` 工厂

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| `createPrefetchPage` 签名 | 成立 | `create-prefetch-page.tsx:8-18`：`createPrefetchPage<TData>({ queryKey: QueryKey; fetchFn: (token: string) => Promise<TData>; Component: ComponentType })`，`'server-only'`；`prefetchQuery({ queryKey, queryFn: () => fetchFn(token) })`（`:25-28`） | 写 `createPrefetchPage<PaginatedResponse<IndustryNewsSource>>({...})`，与 `admin/intelligence-sources/page.tsx:7-11` 逐字同构 |
| `serverApi.get` 签名 | 成立 | `server-api.ts:58-60` `get: request`；`request<T>(path: string, options: { token: string; params?: Record<string, string\|number\|boolean\|null\|undefined> }): Promise<T>`（`:3-6,24`）；走 `BACKEND_INTERNAL_URL` + `/admin` 前缀、3 秒超时（`:8-13,27`） | design §5.2 `serverApi.get('/api/v1/industry-news-sources', { token })` 成立；泛型由 `createPrefetchPage<TData>` 反推 |
| 预取 key 与客户端 key 一致 | 成立 | `intelligence-sources/page.tsx:8` 与 `client-page.tsx:86` 同为 `['admin', 'intelligence-sources']`；spec `directory-structure.md:25-27`、`state-management.md:21`、`quality-guidelines.md:38`。**另一个一致性前提**：预取返回形状 = 客户端 `queryFn` 返回形状——list 页客户端返回 axios `.data`（响应体）（`client-page.tsx:87`），预取直接返回响应体；而 `ai-config/page.tsx:9-15` 因客户端返回 `.data.data`（`client-page.tsx:46-47`）所以预取里多剥一层 `.data` | 两文件各写一次字面量 `['admin', 'industry-news-sources']`（仓库 8 个 admin 预取页全是字面量），或把 key 常量定义在 `client-page.tsx` 导出给 `page.tsx` 引用以防手误。**不建议**在 server-only 的 `page.tsx` 里 import `queryKeys`：`query-keys.ts:1` 会把 `@shared/hooks` 的 zustand persist（`localStorage`）带进服务端模块，仓库无此先例（仅 work-schedule 两个 `'use client'` 页用 `queryKeys.admin.*`） |
| `queryKeys` 工厂结构与 tenant scope 写法 | 成立 | `query-keys.ts:3-6` `tenantScope()` 取 `payload.tid`；tenant 键顶层：`all: () => ['tenant', tenantScope(), '<feature>'] as const`，`list: (filters?) => [...all(), 'list', filters]`（`:10-71`）；admin 键在 `queryKeys.admin.<feature>`，`all: () => ['admin', '<feature>']`（`:73-120`）；spec `state-management.md:17` 新代码一律用工厂 | 新增放 tenant 区（可紧挨 `emails`，PR A 不删 `intelligence:35-39`）：`industryNews: { all: () => ['tenant', tenantScope(), 'industryNews'] as const, list: (filters?: Record<string, unknown>) => [...queryKeys.industryNews.all(), 'list', filters] as const, filters: () => [...queryKeys.industryNews.all(), 'filters'] as const }`。admin 可选加 `admin.industryNewsSources: { all: () => ['admin','industryNewsSources'] as const, list: () => [...all(),'list'] }`，但若加了就得 page.tsx 也用同一数组（见上一行的取舍） |
| design §5.1 `useQuery(queryKeys.industryNews.filters())` | 需改（缩写） | `useQuery` 需要对象：`useQuery({ queryKey: queryKeys.industryNews.filters(), queryFn: async () => (await tenantApi.industryNews.filters()).data.data })`（先例 `intelligence/page.tsx:13-16`） | 展开写法即可 |

### 7. `shared-api` 函数模板与 `PaginatedResponse.pagination`

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| tenant 文件模板 | 成立 | `tenant/companies.ts:107-126`、`tenant/intelligence.ts:29-46`：`export function xxxApi(client: AxiosInstance) { return { list: (filters?: F) => client.get<PaginatedResponse<T>>('/api/v1/…', { params: filters }), detail: (id) => client.get<ApiResponse<T>>(…), markRead: (id) => client.post<ApiResponse<…>>(`/api/v1/…/${id}/read`) } }`；注册在 `tenant/index.ts:18-36`（import + `createTenantApi` 返回对象一行）；类型再导出在 `shared-api/src/index.ts:25-43` | 新建 `tenant/industry-news.ts`：`list(filters?: IndustryNewsFilters)`、`filters()`（`client.get<ApiResponse<IndustryNewsFilterOptions>>`）、`markRead(id)`；`tenant/index.ts` 加 `industryNews: industryNewsApi(client)` |
| admin 文件模板 | 成立 | `admin/intelligence-sources.ts:17-32`、`admin/scoring-templates.ts:17-32`；注册 `admin/index.ts:13-26` | 新建 `admin/industry-news-sources.ts`：`list()` → `client.get<PaginatedResponse<IndustryNewsSource>>('/api/v1/industry-news-sources')`、`fetch()` → `client.post<ApiResponse<{ triggered: boolean }>>('/api/v1/industry-news-sources/fetch')`、`toggle(id, is_active)` → `client.patch<ApiResponse<IndustryNewsSource>>(…/${id}, { is_active })` |
| `params` 传递与数组参数 | 成立 | axios 1.15.0 `toFormData.js:27,172-186`：数组值序列化为 `key[]=a&key[]=b`（会先剥再补 `[]`），后端 `Query(alias="countries[]")`（`backend/app/api/tenant/ops.py:41-46`）；前端类型键名直接写 `'countries[]'?: string[]`（`tenant/companies.ts:63-68`），`buildParams` 只在非空时塞键（`company-filters.tsx:133-150`） | design §4 的 `category[]?` / `source_id[]?` 与现有约定一致：`IndustryNewsFilters` 写 `'category[]'?: string[]; 'source_id[]'?: string[]; lang?: string; unread_only?: boolean; page?: number; page_size?: number`；后端 A9 用 `Query(alias="category[]")` 收 |
| `PaginatedResponse.pagination` 字段 | 成立 | `shared-types/src/api.ts:5-12`：`{ cursor: string \| null; has_more: boolean; total?: number }`；后端 `app/core/responses.py:8-22` `paginated_response(data, *, cursor=None, has_more=False, total=0)` **总是**输出 `total` | 页码分页取 `listQuery.data?.pagination?.total ?? 0`（`companies/page.tsx:67`），`mode="total"`；spec `component-guidelines.md:309` 只在 total 可靠时用 total 模式——后端 `count(*)` 可靠 |
| 类型文件归属（design §5.3：`models.ts` 放模型、`api.ts` 放 Filters） | 成立（与 spec 一致，但与存量页面用法并存） | spec `type-safety.md:12`：`models.ts` 领域模型、`api.ts` 响应壳与筛选参数；存量：`IntelFilters` 在 `shared-types/api.ts:64-69` 被 `shared-api/tenant/intelligence.ts:2` 引用（符合 spec），而页面消费的 `IntelligenceArticle` 定义在 `shared-api/tenant/intelligence.ts:4-18` 并由 `shared-api/src/index.ts:43` 再导出（`models.ts:362-391` 另有一套陈旧重复定义，无人引用） | 按 design 放 `shared-types`，`shared-api` 文件 `import type { … } from '@shared/types'`，页面 `import type { IndustryNewsItem } from '@shared/types'`；不要再在 shared-api 里重复定义一份 |

### 8. 导航结构与替换点；全仓 `/intelligence`、`intelligence-sources`、`情报` 引用

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| tenant `navigation.ts` 结构 | 成立 | `DashboardNavigationGroup { label; items: { href; label; icon }[] }`（`shared-ui/dashboard-shell.tsx:10-19`）；`tenant/navigation.ts:30` 一行：`{ label: '情报', items: [{ href: '/intelligence', label: '情报中心', icon: Newspaper }] }`；`Newspaper` 已在 `:7` 导入；激活判定 `pathname === href \|\| startsWith(href + '/')`（`dashboard-shell.tsx:45-46`） | 只改 `:30` → `{ label: '行业动态', items: [{ href: '/industry-news', label: '行业动态', icon: Newspaper }] }`；「导航可一行还原」成立 |
| admin `navigation.ts` | 成立 | `admin/navigation.ts:33`：`{ href: '/intelligence-sources', label: '情报源管理', icon: Globe2 }`（营销分组 `:30-41`）；`Globe2` 仅此一处使用（`:7`） | 改 `:33` → `{ href: '/industry-news-sources', label: '动态源管理', icon: Globe2 }`；若换 `Newspaper` 图标需同时改 `:2-14` import（删 `Globe2` 加 `Newspaper`） |
| 深链接 / 文案 / 测试引用是否还有别处 | 成立（已穷举） | 无 middleware 路由表（admin `middleware.ts:16` 只按 cookie 放行）、无 `usePermission` 页面键涉及情报（`usePermission.ts:5-21`）、`app-shell.tsx` 无 href→prefetch 映射 | 全部命中清单见 ②；PR A 后遗留页只是失去入口，直接访问 `/intelligence` 仍可打开（design §9 已接受） |

### 9. admin「AI 配置」页场景列表与 `intelligence_summary`

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| 场景列表位置 | 成立 | `admin/ai-config/client-page.tsx`：`SCENE_LABELS` 常量 `:31-37`（`:34` `intelligence_summary: '情报摘要'`）；`sceneDefaults` state `:41`，由接口 `scene_defaults` 灌入 `:64-65`；渲染 `:285-287` `sceneDefaults.map(...)`，标签 `SCENE_LABELS[record.scene] ?? record.scene`；切换时 `updateSceneDefault` 把**整份** `next` PUT 回去（`:142-149`） | 场景行不是前端枚举，而是后端返回什么就渲染什么 |
| 最小隐藏改法 | 成立 | 后端 `PUT /ai-config/scene-defaults` 逐项 upsert、不删未提交的场景（`admin_config_service.py:881-921`），并校验每项 `model_id` 存在且 active（`:896-899`）；`schemas/admin_config.py:121-126` Literal 仍含 `intelligence_summary`（design 说不动） | 一行：`:65` 改为 `setSceneDefaults((query.data.scene_defaults ?? []).filter((item) => item.scene !== 'intelligence_summary'))`——既不渲染也不再随 PUT 提交该场景（避免它若指向 inactive 模型而拖垮整次 PUT 的 422）。只在 `:285` 渲染处 filter 也可，但 PUT 仍会带上隐藏行。PR B 再删 `:34` 标签 |

### 10. `formatDateTime` 签名、`window.open` 先例、Vitest mock

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| `formatDateTime` 签名 | 成立 | tenant `lib/format.ts:8-15`：`formatDateTime(value?: string \| number \| Date \| null, format = 'YYYY-MM-DD HH:mm')`，无效/空返回 `'-'`；admin `lib/format.ts:3-10` 同签名（无 tz 插件）；列用法 `intelligence/page.tsx:60` `format: (value) => formatDateTime(value as string \| undefined, 'YYYY-MM-DD')`、`companies/page.tsx:131` | design §5.1 `formatDateTime(..., 'YYYY-MM-DD')` 成立；admin「上次成功时间」照 `admin/intelligence-sources/client-page.tsx:244-249`（空显示「从未」） |
| `window.open` 先例 | **不成立（无先例）** | 全仓 `rg "window\.open"` 为空；新窗口外链先例只有 `<a target="_blank" rel="noopener noreferrer">`（`admin/collection/customers/client-page.tsx:563-571`、`waimaotong/client-page.tsx:455-463`） | 用 `<a>` 形态（见 2）；若坚持 `window.open(url, '_blank', 'noopener,noreferrer')`，调用本身在浏览器可行，只是没有既有写法可抄 |
| Vitest 对 `window.open` 的 mock | 需补（无先例） | `test/setup.ts` 只 `import '@testing-library/jest-dom/vitest'`；仓库无 `vi.stubGlobal` / `vi.spyOn(window, 'open')`；jsdom 的 `window.open` 未实现（调用时 console 打 "Not implemented: window.open"，不抛错） | 若用 `window.open`：测试里 `const open = vi.spyOn(window, 'open').mockImplementation(() => null)`，断言 `toHaveBeenCalledWith(url, '_blank', 'noopener,noreferrer')`，`afterEach` `mockRestore`。若用 `<a>`：无需 mock，断言 `getByRole('link', { name })` 的 `href` / `target` / `rel` 属性 + `fireEvent.click` 后 `markRead` 被调用 |

### 11. `test/intelligence/intelligence-page.test.tsx` 作为新页面测试模板

| 断言 | 结论 | 证据 | 建议 |
|---|---|---|---|
| 可作模板 | 成立 | `:5-12` `vi.mock('@/lib/api', () => ({ tenantApi: { intelligence: { list: vi.fn(), markRead: vi.fn() } } }))`；`:29-38` `QueryClient({ retry:false })` + `QueryClientProvider` 包裹；`:41-45` `beforeEach` 设默认 resolved 值；`:49-58` 按 `columnheader` 断言列宽类；`:60-69` 错误态 + 重试；`:71-86` pending 行内禁用。spec `quality-guidelines.md:14-16` 点名它为模板 | 新文件 `test/industry-news/industry-news-page.test.tsx`，mock 对象换成 `industryNews: { list, filters, markRead }`；`list` 返回 `{ data: { data: rows, pagination: { total } } }`（先例 `companies-page.test.tsx:52`）；`filters` 返回 `{ data: { data: { categories, sources, langs, has_sources } } }` |
| 未被模板覆盖的两点 | 需补 | (1) 该测试没 mock `@shared/hooks`，`queryKeys.*` 里的 `useAuthStore.getState()` 走真实 zustand（jsdom 有 localStorage，可用）；要断言 tenant scope 或 `tid` 时按 `team-status-toggle.test.tsx:22-27` mock；(2) 页面若用 `toast`，按 `companies-page.test.tsx:24-26` mock `sonner` | 新页面 A11 四条用例（未读/已读类名、点击调用 + 乐观置已读、`has_sources=false` 空态、筛选参数透传）都能在此模板内写；「筛选参数透传」断言 `tenantApi.industryNews.list` 的 `toHaveBeenCalledWith(expect.objectContaining({ 'category[]': [...], unread_only: true, page: 1, page_size: 50 }))` |

---

## ② PR B 前端清理清单补全（文件:行号）

implement.md B3 只写到目录级；逐行如下（PR A 已替换导航两行不再列）。

### 删除整个文件 / 目录

| 路径 | 说明 |
|---|---|
| `frontend/apps/tenant/src/app/(dashboard)/intelligence/page.tsx` | 目录内仅此一文件（108 行） |
| `frontend/apps/tenant/test/intelligence/intelligence-page.test.tsx` | 目录内仅此一文件 |
| `frontend/apps/admin/src/app/(dashboard)/intelligence-sources/page.tsx`、`client-page.tsx` | 目录内仅此两文件 |
| `frontend/packages/shared-api/src/tenant/intelligence.ts` | `IntelligenceArticle`、`IntelligenceSubscription`、`intelligenceApi` |
| `frontend/packages/shared-api/src/admin/intelligence-sources.ts` | `IntelligenceSource`、`intelligenceSourcesApi` |

### 文件内行级删除

| 文件:行号 | 内容 |
|---|---|
| `frontend/packages/shared-api/src/tenant/index.ts:10` | `import { intelligenceApi } from './intelligence';` |
| `frontend/packages/shared-api/src/tenant/index.ts:28` | `intelligence: intelligenceApi(client),` |
| `frontend/packages/shared-api/src/admin/index.ts:6` | `import { intelligenceSourcesApi } from './intelligence-sources';` |
| `frontend/packages/shared-api/src/admin/index.ts:19` | `intelligenceSources: intelligenceSourcesApi(client),` |
| `frontend/packages/shared-api/src/index.ts:7` | `export type { IntelligenceSource } from './admin/intelligence-sources';` |
| `frontend/packages/shared-api/src/index.ts:43` | `export type { IntelligenceArticle, IntelligenceSubscription } from './tenant/intelligence';` |
| `frontend/packages/shared-api/src/query-keys.ts:35-39` | tenant `intelligence: { all, list, subscriptions }` |
| `frontend/packages/shared-api/src/query-keys.ts:80-84` | `admin.intelligenceSources: { all, list, detail }` |
| `frontend/packages/shared-types/src/models.ts:17-19` | import 的 `IntelligenceSourceType`、`IntelligenceArticleStatus`、`ArticlePublicationStatus` |
| `frontend/packages/shared-types/src/models.ts:355-406` | `// === 情报 ===` 段：`FetchConfig`、`IntelligenceSource`、`IntelligenceArticle`、`IntelligenceArticlePublication`、`IntelligenceArticlePublicationWithArticle` |
| `frontend/packages/shared-types/src/enums.ts:30-33` | `// === 情报 ===` 段：`IntelligenceSourceType`、`IntelligenceArticleStatus`、`ArticlePublicationStatus` |
| `frontend/packages/shared-types/src/api.ts:64-69` | `IntelFilters` |
| `frontend/packages/shared-types/src/api.ts:321-329` | `ImportResult`——全仓唯一消费方是 `admin/intelligence-sources.ts:2,30` 与 admin client-page `:4,199`，删后成孤儿，可顺手删（可选） |
| `frontend/apps/admin/src/app/(dashboard)/ai-config/client-page.tsx:34` | `intelligence_summary: '情报摘要',`（A12 隐藏后该标签无用） |

### 必须保留（PRD R5「枚举不动」）

| 文件:行号 | 内容 |
|---|---|
| `frontend/packages/shared-types/src/enums.ts:39` | `AiModelType = … \| 'intelligence' \| …` |
| `frontend/packages/shared-types/src/enums.ts:40` | `AiUsageType = … \| 'intelligence_summary' \| …` |
| `frontend/packages/shared-types/src/enums.ts:43` | `NotificationCategory = … \| 'intelligence' \| …` |

### B3 验证命令修正

`rg -n "intelligence" frontend --glob '!node_modules'` **不可能为空**（上表三行枚举必留）。建议改为与 B2 同口径：`rg -n -i "intelligence" frontend --glob '!node_modules' --glob '!**/enums.ts'` 为空，或明示「只剩 `enums.ts:39,40,43` 三处枚举成员」。`apps/*/tsconfig.tsbuildinfo` 虽含旧路径但被 gitignore，`rg` 默认跳过。

### 文档 / spec 里的前端相关残留（B4 未列全）

| 文件:行号 | 内容 | 处理 |
|---|---|---|
| `README.md:129` | 管理端流程「② 维护行业情报源」 | 改为「② 维护行业动态源」 |
| `README.md:154` | 功能矩阵「情报源管理 🟡 …（#49）」 | A13 已安排改写 |
| `README.md:169` | 功能矩阵「情报中心（阅读侧）… tenant `/intelligence`」 | A13 已安排改写 |
| `.trellis/spec/frontend/state-management.md:3,17` | 事实来源与示例引用 `intelligence/page.tsx`、`queryKeys.intelligence.list(filters)` | 改为 `industry-news/page.tsx`、`queryKeys.industryNews.list(filters)`（走 update-spec） |
| `.trellis/spec/frontend/quality-guidelines.md:14,16` | 测试模板与目录示例 `test/intelligence/intelligence-page.test.tsx`、`test/intelligence/` | 改为 `test/industry-news/…` |
| `.trellis/spec/frontend/directory-structure.md:23` | 页面模式参照 `intelligence/page.tsx` | 改为 `industry-news/page.tsx` |
| `.trellis/spec/frontend/component-guidelines.md:327,329` | 「评分模板与情报源列表统一使用可操作 Switch」「Tenant 简单列表：情报、团队与模板…」 | 改「动态源」「行业动态」 |
| `.trellis/spec/backend/api-guidelines.md:21` | 静态路由先于动态路由的例子引用 `/intelligence-sources/batch-import` | 换成新的 `/industry-news-sources/fetch` 先于 `/{source_id}` |
| `.trellis/spec/backend/error-handling.md:3,18` | 事实来源与 `intelligence_service.publish_article` 白名单例子 | B2 删文件后需换例子 |
| `.trellis/spec/backend/domain-rules.md:20` | 「AI 评级 / 邮件生成 / 情报摘要 当前为启发式桩（#46）」 | 去掉「情报摘要」 |
| `.trellis/spec/backend/database-guidelines.md:44` | 分区表清单 | B4 已列 |
| `docs/database-schema.md`、`docs/database-schema.dbml` | 四表节与 FK 图 | B4「随快照再生」已覆盖 |
| `PROGRESS-2026-Q3.md:16-17,315,324,341`、`docs/solutions/integration-issues/admin-local-production-api-proxy-and-ssr.md:50`、`docs/solutions/database-issues/select-duplicate-alias-shadowing-in-mappings.md:19,25` | 历史记录 / 冻结档案（`quality-guidelines.md:3` 注明 docs/solutions 已冻结） | 不动 |
| `CONTEXT.md:15,19,23` | 已把「情报 / 情报中心 / 情报源」列为 Avoid 词 | 已对齐，不动 |

---

## ③ 额外发现

1. **表格列宽 token 已漂移**：`globals.css:62-64` 实际为 small=64px / medium=96px / large=144px（commit `7ffc926`，2026-07-24），而 `component-guidelines.md:217` 与 `design-system.md:178-183` 仍写 96/144/224。DataTable 用 `table-fixed` + `w-max min-w-full`（`data-table.tsx:250`），列数少时浏览器会按比例撑开，所以三档是相对密度而非绝对像素；但标题列 `large` 的基线只有 144px，标题被截断是常态，自定义 `render` 时务必保留 `truncate` 或自行加 Tooltip。
2. **乐观更新与 spec 口径冲突**：design §5.1「`onMutate` 乐观把该行 `is_read` 置 true」需要 `queryClient.setQueryData` 改缓存；`state-management.md:19` 写明「mutation 成功后 invalidate，不手改缓存」，且全仓无 `setQueryData` / `onMutate` 先例。等价替代：页面本地 `useState<Set<string>>` 记录「本会话已点过」的 id，渲染时 `row.is_read || clickedIds.has(row.id)`（与 `admin/intelligence-sources/client-page.tsx:79` 的 `updatingIds` 同一手法），`onSettled` 再 invalidate `queryKeys.industryNews.all()`——效果一样、不碰缓存。
3. **「只看未读」+ 点击标题的组合行为**：`unread_only` 生效时，点击后 invalidate 会让该行在下一次 refetch 后从列表消失（它已读）；本地 `clickedIds` 方案下 refetch 前仍显示为已读态，refetch 后消失。这是产品层面是否接受的问题，design 未提。
4. **admin 预取 key 与 `queryKeys` 工厂二选一**：spec 评审清单（`quality-guidelines.md:38`）同时要求「`queryKeys` 工厂」与「admin 预取 key 一致」，但 `create-prefetch-page.tsx` 是 server-only，而 `query-keys.ts:1` 依赖 `@shared/hooks`（zustand persist + `localStorage`）；现有 8 个预取页全用字面量 key，因此 design §5.2 的字面量写法是当前唯一有先例的做法。
5. **A10「只新增，不删旧」与 `queryKeys.admin.intelligenceSources` 命名**：PR A 同时存在 `intelligence`（`:35-39`）与新 `industryNews`，type-check 无冲突。
6. **`entityName` 会进入 aria-label**：Vitest 里 `screen.findByRole('table', { name: '<entityName>列表' })` 是既有断言方式（`intelligence-page.test.tsx:52`），选定 `entityName` 后文案即固定。
7. **`date` 列的 `format` 形参是 `unknown`**：`time` 为 ISO 字符串，`formatDateTime` 接受 `string | number | Date | null | undefined`，需 `value as string | undefined` 断言（`intelligence/page.tsx:60`）。
8. **Switch 视觉**：`switch.tsx:12` 默认 `data-[state=checked]:bg-primary`（shadcn 旧色板），DataTable boolean 列额外加了 `data-[state=checked]:bg-ui-primary`（`data-table.tsx:189`）。若「只看未读」用 FilterBar custom 渲染裸 `Switch`，可照抄该 className 保持一致。

---

## ④ 结论

design §5 与 implement A10–A12 的绝大多数断言与五件套、shared-api、shared-types、admin SSR 预取壳的真实契约相符，可以直接开工；需要改写的只有四处：(1) FilterBar 没有布尔 kind，「只看未读」必须以字符串 draft（`'' | '1'`）经 `kind:'custom'`（渲染 Switch）或 `kind:'select'` 表达，且只能随「查询」生效；(2) TableState 空态文案不可定制，「本实例尚未配置动态源」要在表格外渲染（或向后兼容地给 `empty` 加可选 `description`），而「没有符合筛选的动态」的真实文案是「没有符合当前条件的动态」；(3) Pagination 的 props 是 `mode="total"` + `value={{page,pageSize}}` + `onChange(next)`，列表查询要加 `placeholderData: keepPreviousData` 才能兑现「refetch 保留旧行」；(4) 点击标题走 `render` 里的 `<a target="_blank" rel="noopener noreferrer">`（仓库先例），仓库无 `window.open` 与其 Vitest mock 先例，若坚持 `window.open` 需 `vi.spyOn(window,'open')`。另有两处与 spec 口径的张力需要主 agent 拍板：乐观更新是否改用页面本地 `clickedIds` 以遵守「不手改缓存」，以及 admin 预取 key 用字面量还是工厂。B3 的清理清单在 ② 已补到行号，`rg "intelligence" frontend` 为空的门禁不可达，须放行 `enums.ts:39,40,43` 三处枚举成员，并把 spec 里 6 处以情报页为范例的引用一并换掉。
