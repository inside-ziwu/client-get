# PR B · 前端清理（B3）工作报告

> 分支 `refactor/industry-news-legacy-cleanup`，主检出。范围：`design.md` §6「前端」行 + `implement.md` §2 B3。只改 `frontend/`，未 commit / stash / checkout，未改 `.env*`。日期 2026-08-23。

## 一、删除的文件（6 个，`git rm` 等价）

| 文件 | 说明 |
|---|---|
| `frontend/apps/tenant/src/app/(dashboard)/intelligence/page.tsx` | 租户「情报中心」页（整个 `intelligence/` 目录） |
| `frontend/apps/tenant/test/intelligence/intelligence-page.test.tsx` | 对应 Vitest（整个 `test/intelligence/` 目录） |
| `frontend/apps/admin/src/app/(dashboard)/intelligence-sources/page.tsx` | 管理端「情报源管理」SSR 预取壳 |
| `frontend/apps/admin/src/app/(dashboard)/intelligence-sources/client-page.tsx` | 管理端「情报源管理」客户端页（含新增 / 编辑 / 批量导入 / 删除） |
| `frontend/packages/shared-api/src/tenant/intelligence.ts` | 租户 `intelligenceApi`（articles / read / star / archive / subscriptions） |
| `frontend/packages/shared-api/src/admin/intelligence-sources.ts` | 管理端 `intelligenceSourcesApi`（list / get / create / update / delete / batchImport） |

## 二、行级修改（8 个文件，净 -858 行 / +1 行）

| 文件 | 改动 |
|---|---|
| `frontend/packages/shared-api/src/index.ts` | 删两行类型再导出：`IntelligenceSource`、`IntelligenceArticle / IntelligenceSubscription` |
| `frontend/packages/shared-api/src/tenant/index.ts` | 删 `intelligenceApi` 导入与 `intelligence:` 注册 |
| `frontend/packages/shared-api/src/admin/index.ts` | 删 `intelligenceSourcesApi` 导入与 `intelligenceSources:` 注册 |
| `frontend/packages/shared-api/src/query-keys.ts` | 删 tenant 区 `intelligence` 与 admin 区 `intelligenceSources` 两组键 |
| `frontend/packages/shared-types/src/models.ts` | 删「情报」整段（`FetchConfig`、`IntelligenceSource`、`IntelligenceArticle`、`IntelligenceArticlePublication`、`IntelligenceArticlePublicationWithArticle`）及头部三个随之失去引用的枚举导入 |
| `frontend/packages/shared-types/src/api.ts` | 删 `IntelFilters`；删孤儿 `ImportResult`（rg 确认仅被已删的情报源页面与 API 引用） |
| `frontend/packages/shared-types/src/enums.ts` | 删 `// === 情报 ===` 段的三个孤儿类型别名 `IntelligenceSourceType` / `IntelligenceArticleStatus` / `ArticlePublicationStatus`（design §6 列为 `enums.ts:30-33` 删除项；rg 确认删 models.ts 后全仓无引用）。**保留** `AiModelType` 的 `'intelligence'`、`AiUsageType` 的 `'intelligence_summary'`、`NotificationCategory` 的 `'intelligence'` 三处枚举成员（design 明确保留，现位于 `:34, 35, 38`） |
| `frontend/apps/admin/src/app/(dashboard)/ai-config/client-page.tsx` | 删 `SCENE_LABELS` 的 `intelligence_summary: '情报摘要'`；灌入 state 时去掉 `.filter(item => item.scene !== 'intelligence_summary')`，还原为 monorepo 合并时的 `setSceneDefaults(query.data.scene_defaults ?? [])`（PR B 迁移删除该场景默认行后二者均为死代码）。渲染处 `SCENE_LABELS[record.scene] ?? record.scene` 有兜底，若迁移前后短暂存在未知场景也不会崩 |

导航：tenant `components/layout/navigation.ts:30` 与 admin `components/layout/navigation.ts:33` 在 PR A 已分别换成 `/industry-news`「行业动态」与 `/industry-news-sources`「动态源管理」；`rg` 确认两端 `src/` 内（含路由预取、`usePermission`、middleware）没有任何 `intelligence` 路径残留。

## 三、验证输出（原样）

### 1. `cd frontend && pnpm type-check`

首跑 `apps/admin` 失败 3 条 `TS2307`，全部来自 `apps/admin/.next/types/app/(dashboard)/intelligence-sources/page.ts` 与 `.next/types/validator.ts`——上一次 build 留下的生成物引用了已删页面（`.next/` 为 `.gitignore:14` 忽略的构建产物，tsconfig `include` 含 `.next/types/**/*.ts`）。跑过 `pnpm build:admin` 重新生成后再跑：

```
Scope: 6 of 7 workspace projects
packages/shared-types type-check: Done
packages/shared-ui type-check: Done
packages/shared-hooks type-check: Done
packages/shared-api type-check: Done
apps/admin type-check: Done
apps/tenant type-check: Done
```

6 个包全部 Done。

### 2. Vitest

```
> @apps/tenant@0.1.0 test
 Test Files  17 passed (17)
      Tests  60 passed (60)

> @shared/ui@0.1.0 test
 Test Files  21 passed (21)
      Tests  85 passed (85)
```

### 3. Build

`pnpm build:admin`：`✓ Compiled successfully`，20 个路由，清单含 `/industry-news-sources`，**无 `/intelligence-sources`**：

```
├ ƒ /ai-config
├ ƒ /collection/customers … /collection/waimaotong
├ ƒ /contact-classification
├ ƒ /email-templates
├ ƒ /industry-news-sources
├ ○ /login
├ ƒ /scoring-templates
├ ƒ /tenants
├ ƒ /warmup-rules
├ ○ /work-schedule, /work-schedule/countries/[iso3], /work-schedule/rule-sets/[id]
```

`pnpm build:tenant`：`✓ Compiled successfully`，17 个路由，清单含 `/industry-news`，**无 `/intelligence`**：

```
├ ○ /companies
├ ○ /curated-customers
├ ○ /force-change-password
├ ○ /industry-news
├ ○ /login
├ ○ /onboarding
├ ○ /send-plans, /send-plans/[id], /send-plans/[id]/edit, /send-plans/new
├ ○ /settings/ai-provider, /settings/scoring, /settings/team
├ ○ /templates
```

### 4. rg 门禁

```
$ rg -n -i "intelligence" frontend --glob '!node_modules' --glob '!.next' --glob '!**/enums.ts'
（无输出，exit=1）

$ rg -n -i "intelligence" frontend --glob '!node_modules' --glob '!**/enums.ts'   # implement.md B3 原命令（不排除 .next）
（无输出，exit=1）
```

`enums.ts` 内剩余三处即设计保留的枚举成员（`:34 AiModelType`、`:35 AiUsageType`、`:38 NotificationCategory`）。补充核查 `rg -n "情报|IntelFilters|ImportResult" frontend --glob '!node_modules' --glob '!.next'` 同样无输出（exit=1）：`frontend/` 下已无「情报」字样。

## 四、疑点 / 留给协调者

1. **`enums.ts:30-33` 的处置**：任务书写「保留 enums.ts 里的枚举成员」，design §6 写「删 `enums.ts:30-33`、保留 `:39, 40, 43` 三处枚举成员」。我按 design 执行：删了三个已无引用的类型别名，保留三处枚举成员。若协调者的本意是 enums.ts 整文件不动，`git checkout -- frontend/packages/shared-types/src/enums.ts` 一行可还原（type-check 不受影响，因 models.ts 已不再导入它们）。
2. **`.next/types` 陈旧产物**：任何在删页面之后、未重新 build 之前直接跑 `pnpm type-check` 的人都会看到同样的 3 条 `TS2307`；CI 干净检出不受影响。若要在本地复现「干净」结果，先 `pnpm build:admin` 或删 `apps/admin/.next`。
3. 工作区内 `README.md`、`backend/03_database/schema_docs.json`、`schema_notes.md`、`.trellis/spec/frontend/quality-guidelines.md` 的改动来自同时进行的后端 / 文档代理，本次未触碰。
