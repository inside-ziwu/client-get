# 前端交付评审（行业动态 · PR A · A10–A12）

- **对象**：worktree `/Users/lay/orca/workspaces/ClientGet/industry-news-frontend`，分支 `inside-ziwu/industry-news-frontend`（基于 main `dac67d1`），`git status --short` 列出的 9 个修改 + 6 个新增路径
- **对照**：design.md v3 §4 / §5 / §9、prd.md R1 / R2 / AC1–AC5、implement.md A10–A12、`design-review-frontend.md`、`review-resolution.md` F1–F9、`.trellis/spec/frontend/*.md`、工人报告 `frontend-report.md`
- **日期**：2026-08-23
- **评审方式**：逐文件对照契约与五件套真实签名（`filter-bar.tsx` / `data-table.tsx` / `list-page.tsx` / `pagination.tsx`）、先例页（`companies/page.tsx`、`intelligence/page.tsx`、`admin/intelligence-sources/{page,client-page}.tsx`）；门禁在 worktree 复跑

---

## ① 发现与处置

### 发现（2 项，均已修）

| # | 问题 | 证据（路径:行号，修前） | 处置 |
|---|---|---|---|
| 1 | 筛选选项请求（`/industry-news/filters`）失败时页面无任何提示：`optionState` 落到 `'empty'`，三个下拉以「暂无可选项」禁用，用户无法区分"没有选项"与"加载失败"，也没有重试入口；与 companies 先例（`companies/page.tsx:174-179` 的 `role="alert"` 提示 + 重试）不一致 | `frontend/apps/tenant/src/app/(dashboard)/industry-news/page.tsx:222-232` | **已修**：`filters` 插槽改为 `flex-col gap-ui-sm` 容器，FilterBar 下方在 `filtersQuery.isError` 时渲染提示块「筛选选项加载失败，列表仍可浏览。」+ 「重试」按钮（`filtersQuery.refetch()`），类名与先例逐字一致；新增 Vitest 用例「筛选选项加载失败时提示并可重试，列表仍可浏览」（断言 alert 文案、列表行仍在、点重试后 `filters` 被第二次调用且 alert 消失） |
| 2 | 测试没有锁定已拍板口径「`markRead` 成功后不 invalidate 列表，点过的行保持可见」（design §5.1 加粗项、review-resolution F5 / C10）：用例 2 只断言 `markRead` 被调用与类名切换，若将来有人加回 `invalidateQueries` 测试不会失败 | `frontend/apps/tenant/test/industry-news/industry-news-page.test.tsx:103-114` | **已修**：用例 2 末尾补两条断言——`link` 仍在文档内、`tenantApi.industryNews.list` 仅调用 1 次 |

### 核对通过（无需改）

| 范围 | 核对项 | 证据 |
|---|---|---|
| 契约 §4 | `IndustryNewsFilters` 键名 `'category[]'` / `'source_id[]'` / `lang` / `unread_only` / `page` / `page_size`，与 design §5.3 逐字一致 | `shared-types/src/api.ts:71-79` |
| 契约 §4 | `list` → `client.get<PaginatedResponse<IndustryNewsItem>>('/api/v1/industry-news/items', { params })`；`filters` → `ApiResponse<IndustryNewsFilterOptions>`（含 `has_sources`）；`markRead` → `POST /api/v1/industry-news/items/${id}/read`，返回 `{ item_id; is_read: true }` | `shared-api/src/tenant/industry-news.ts:12-17` |
| 契约 §4 | 页面从 `pagination.total` 取总数（`mode="total"`），不依赖 `has_more` | tenant `page.tsx:193` |
| 契约 §4 | admin `list` → `ApiResponse<IndustryNewsSource[]>`（`success_response` 数组，不分页）；`fetch` → `POST …/fetch` 返回 `{ triggered; reason?: 'in_progress' \| 'no_sources' }`；`toggle` → `PATCH …/${id}` body `{ is_active }` | `shared-api/src/admin/industry-news-sources.ts:6-13` |
| 契约 §4 | `fetch()` 三分支提示：`triggered` → 「已开始抓取，稍后刷新查看」+ 30 秒后 invalidate 一次；`in_progress` → 「一轮抓取正在进行」；否则 → 「本实例没有可抓取的源」；`onError` 另有失败提示；按钮 pending 时禁用并显示「触发中…」 | admin `client-page.tsx:44-57, 155-163` |
| admin 预取 | `page.tsx` 与 `client-page.tsx` 的 key 同为字面量 `['admin', 'industry-news-sources']`；预取 `createPrefetchPage<ApiResponse<IndustryNewsSource[]>>` 返回响应体，客户端 `queryFn` 返回 axios `.data`（响应体），形状一致 | `page.tsx:6-8`、`client-page.tsx:36-39` |
| 五件套 | FilterBar draft 全为 `string \| string[]`（`unread_only: '' \| '1'`）；「只看未读」`kind: 'custom'` 渲染共享 `Switch`，`aria-label="只看未读"`，className 与 `data-table.tsx:189` 逐字相同；`onSubmit` 设 applied + `setPage(1)`；`onReset` 自清 draft / applied / page；`optionState` 传入 multiSelect / select | tenant `page.tsx:20-28, 93-136, 198-207` |
| 五件套 | `placeholderData: keepPreviousData`；`Pagination mode="total" total value onChange isDisabled={isLoading}`，默认每页 50，`pageSizeOptions` 默认 `[20,50,100]` 不超 design 的 ≤100 | tenant `page.tsx:74-78, 234-243` |
| 五件套 | `TableState` 五态：`loading` / `error`（`description: '请检查网络后重试'`, `onRetry`）/ `empty`（`filtered: appliedCount > 0`, `onResetFilters`）/ `isRefreshing={isFetching && !isLoading}`；`entityName="动态"` 自动得「暂无动态」「没有符合当前条件的动态」 | tenant `page.tsx:209-215, 251-258` |
| 五件套 | 标题列 `<a href target="_blank" rel="noopener noreferrer" onClick={markClicked}>`；未读 `truncate text-ui-body-strong text-ui-foreground`，已读 `truncate text-ui-muted-foreground`；`is_external` 时标题后 `text-ui-caption text-ui-muted-foreground` 灰字 `target_domain`；`clickedIds` 页面本地 `useState<ReadonlySet>`，渲染 `row.is_read \|\| clickedIds.has(row.id)`；`markRead` 不 invalidate | tenant `page.tsx:65-66, 80-88, 145-163` |
| 五件套 | 列宽全部用 `small` / `medium` / `large` 预设，无像素 / 颜色散写（grep `w-\[`、`#hex`、`text-red-*` 为空）；用到的令牌（`gap-ui-xs`、`bg-ui-surface-soft`、`border-ui-border`、`text-ui-danger-foreground`、`rounded-ui-md`）均在 `tailwind-preset.ts` 中存在 | tenant / admin 两页 |
| 五件套 | admin：地址列 `type: 'text'` 不给 render（自动截断 + Tooltip）；启用列 `type: 'boolean', booleanMode: 'interactive'` + `updatingIds`（`onMutate` 加、`onSettled` 删）；上次成功列空显示「从未」；错误计数 >0 套 `text-ui-danger-foreground`；空列表渲染说明块「本实例尚未配置动态源（由开发随种子导入）」且「立即抓取」仍可点（PRD R2） | admin `client-page.tsx:59-77, 88, 106-137, 142, 165-168` |
| 五件套 | `ListPage` 仅一个 `primaryAction`（`Button variant="outline"`，非新增语义不用 `CreateButton`）；`className="tenant-page"` / `"admin-page"` 传给 ListPage 与 `companies/page.tsx:154`、`email-templates/client-page.tsx:187` 先例一致 | — |
| 类型 | 六个新文件与测试中无 `any`；模型（`IndustryNewsItem` / `IndustryNewsSource` / `IndustryNewsFilterOptions`）在 `shared-types/models.ts`，筛选参数在 `api.ts`；`shared-api` 两文件均 `import type … from '@shared/types'`，不再重复定义；可空字段按 type-safety.md 用 `?:` | `models.ts:457-502`、`api.ts:71-79` |
| 类型 | `queryKeys.industryNews` 在 tenant 区，`all()` 带 `tenantScope()`，`list(filters)` / `filters()` 派生；旧 `intelligence` 键未动 | `query-keys.ts:40-44` |
| 类型 | 未删除任何 `intelligence` 旧代码：`tenant/intelligence.ts`、`admin/intelligence-sources.ts`、两个旧页面、旧测试、`IntelFilters`、`SCENE_LABELS.intelligence_summary` 均在；`git status` 无删除项 | `git status --short` |
| 导航 | tenant `navigation.ts:30` → `{ label: '行业动态', items: [{ href: '/industry-news', label: '行业动态', icon: Newspaper }] }`；admin `navigation.ts:33` → `{ href: '/industry-news-sources', label: '动态源管理', icon: Globe2 }`，各一行 | `git diff` |
| AI 配置 | `ai-config/client-page.tsx:65-66` 灌入 state 时 `filter((item) => item.scene !== 'intelligence_summary')`，既不渲染也不随整份 PUT 提交；`:34` 标签保留待 PR B | `git diff` |
| 测试 | 原四条用例真实覆盖 design §9：① 未读 / 已读类名（`toHaveClass`）；② `<a>` 的 href / target / rel + 点击后 `markRead('item-1')` 被调用且行变已读态；③ `has_sources=false` → 「本实例尚未配置动态源」且 `queryByRole('table')` 不存在；④ 选类别 + 开关后点「查询」，`list` 的 `toHaveBeenLastCalledWith(expect.objectContaining({ 'category[]': ['PCB 技术 / 工程'], unread_only: true, page: 1, page_size: 50 }))`，并先断言输入只改 draft（未点查询前 `list` 仅 1 次）；mock `list` 返回 `{ data: { data: rows, pagination: { total } } }`；jsdom polyfill 与 `company-filter-option-feedback.test.tsx` 同法 | `industry-news-page.test.tsx` |

### 待协调者决定（非缺陷，未改）

| # | 事项 | 说明 |
|---|---|---|
| A | `has_sources === false` 时 FilterBar（4 个字段禁用、占位「暂无可选项」）与 Pagination（「共 0 条」）仍渲染，只有 DataTable 被说明块替换 | design §5.1 字面只要求"不渲染 DataTable，在 children 位置渲染说明块"，实现与之一致；若希望 Instance B 空态更干净，可连筛选区与分页一起隐藏（tenant `page.tsx:222-259`）。属呈现取舍 |
| B | admin「立即抓取」成功后 `setTimeout(30_000)` invalidate（工人报告第 3 项） | 组件卸载后定时器仍会触发一次 `invalidateQueries`，对 app 级 `queryClient` 无害、不会报错；design §5.2 原文就是"30 秒后 invalidate 列表一次"，可按现状结案 |
| C | `shared-api/src/index.ts:44-51` 从 `@shared/types` 再导出六个行业动态类型 | design §5.3 如此要求，type-only 无害；但仓库先例只再导出本包内定义的类型，且两端页面已直接 `import from '@shared/types'`，这组再导出当前无消费方。可保留，或 PR B 顺手删 |
| D | A12「本地起 admin 手工点启停与立即抓取」未做 | 依赖后端 A9，工人已如实列出；待后端落地后在联调阶段补冒烟（含进行中提示、空列表说明） |
| E | 存量失败 `companies-page.test.tsx > 短字段使用 small` | 与本次无关（`companies/page.tsx` 与 `shared-ui` 未触碰，main 上同样失败），已登记 issue；本次按协调者指示忽略 |

---

## ② 门禁最终输出摘要（worktree `frontend/`，评审修改后复跑）

| 命令 | 结果 |
|---|---|
| `pnpm type-check` | 6 个 workspace 全部 `Done`（shared-types / shared-ui / shared-hooks / shared-api / admin / tenant），0 错误 |
| `pnpm --filter @apps/tenant test` | 18 文件 / 61 用例：**60 通过，1 失败**；唯一失败为存量 `test/companies/companies-page.test.tsx > 短字段使用 small，并按内容语义统一表头对齐`（见待决 E）；`test/industry-news/industry-news-page.test.tsx` **5/5 通过**（原 4 条 + 本次新增 1 条），verbose 模式无 act / console 告警 |
| `pnpm build:admin` | `EXIT=0`，`Compiled successfully`，21 个静态页生成；路由表含 `ƒ /industry-news-sources 4.99 kB / 342 kB`（admin 文件在构建后未再改动） |

评审期间改动的文件（均在 worktree，未 commit）：
- `frontend/apps/tenant/src/app/(dashboard)/industry-news/page.tsx`（筛选选项失败提示 + `Button` 导入）
- `frontend/apps/tenant/test/industry-news/industry-news-page.test.tsx`（用例 2 补断言、新增用例 5）

---

## ③ 结论

**可合并（前端部分）。** 契约与 design §4 / §5 逐项一致，五件套用法与先例同构，类型层无 `any`、无重复定义，未删旧 `intelligence` 代码，四条设计要求的用例真实断言了行为；两处非阻断问题已就地修复并补测试，门禁通过（唯一失败为已登记的存量用例）。待决 A–D 不影响合并，可在联调或 PR B 处理。
