# 前端工人完成报告（行业动态 · PR A · A10–A12）

## 改动文件清单

新增：
- `frontend/packages/shared-api/src/tenant/industry-news.ts`（`industryNewsApi`：`list` / `filters` / `markRead`）
- `frontend/packages/shared-api/src/admin/industry-news-sources.ts`（`list` / `fetch` / `toggle`）
- `frontend/apps/tenant/src/app/(dashboard)/industry-news/page.tsx`（租户「行业动态」页，五件套 + `keepPreviousData` + `<a target="_blank">` + 页面本地 `clickedIds`）
- `frontend/apps/tenant/test/industry-news/industry-news-page.test.tsx`（4 条用例）
- `frontend/apps/admin/src/app/(dashboard)/industry-news-sources/{page,client-page}.tsx`（SSR 预取壳 + 监控页：启停 Switch、「从未」时间列、错误计数标红、「立即抓取」按 `reason` toast、空列表说明块）

修改：
- `shared-types/src/models.ts`：新增「行业动态」段（`IndustryNewsItem` / `IndustryNewsSource` / `IndustryNewsFilterOptions` + `IndustryNewsLang` / `IndustryNewsStrategy`）
- `shared-types/src/api.ts`：新增 `IndustryNewsFilters`（`'category[]'` / `'source_id[]'` 数组键）
- `shared-api/src/tenant/index.ts`、`admin/index.ts`：注册两个 api
- `shared-api/src/index.ts`：从 `@shared/types` 再导出行业动态类型（design §5.3）
- `shared-api/src/query-keys.ts`：tenant 区新增 `industryNews`（`all` / `list` / `filters`，带 `tenantScope()`；旧 `intelligence` 未动）
- tenant `navigation.ts:30`：「情报→情报中心」改为「行业动态 → `/industry-news`」
- admin `navigation.ts:33`：改为「动态源管理 → `/industry-news-sources`」
- admin `ai-config/client-page.tsx:65`：灌入 state 时过滤 `intelligence_summary` 场景（不渲染、不随整份 PUT 提交）；`:34` 标签按 design 留待 PR B

## 门禁输出摘要

- `pnpm type-check`：6 个 workspace 全部 Done
- `pnpm --filter @apps/tenant test`：60 用例 59 通过；新页 4/4 通过。唯一失败 `companies-page.test.tsx > 短字段使用 small` 是**存量失败**：该断言涉及的 `companies/page.tsx` 与 `shared-ui` 本次均未触碰（git status 可证），单跑该文件同样失败，与本次改动无关
- `pnpm build:admin`：exit 0，路由表含 `/industry-news-sources`

## 与 design 的偏离

无实质偏离。两处实现细节照 design-review 核证执行：「只看未读」用 `kind: 'custom'` + 字符串 draft（`'' | '1'`）渲染 Switch；两个「未配置动态源」说明块不经 TableState、在表格外渲染。

## 留给协调者的事项

1. 上述 companies 存量失败建议在 PR A 外单独处理（或确认豁免）。
2. A12 验证里的「本地起 admin 手工点启停与立即抓取」未做——后端接口尚未就绪且任务书禁止连接后端，待后端 A9 落地后补冒烟。
3. 「立即抓取」成功后 30 秒自动 invalidate 一次用的是 `setTimeout`，如评审认为不妥可改。
4. 未做任何 git 操作，改动全部留在工作区。
