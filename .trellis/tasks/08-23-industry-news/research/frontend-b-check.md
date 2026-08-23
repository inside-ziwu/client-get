# PR B · 前端与文档/spec 复审（2026-08-23）

> 分支 `refactor/industry-news-legacy-cleanup`，主检出，未提交。复审范围：`git diff -- frontend README.md .trellis/spec backend/03_database/schema_docs.json backend/03_database/schema_notes.md`；依据 `design.md` §6「前端」「文档 / spec」两行、`implement.md` §2 B3/B4、`.trellis/spec/frontend/`。实现者报告：`frontend-b-report.md`。未触碰 `backend/app|scripts|tests|alembic`（另一代理复审）。未 commit / stash / checkout，未改 `.env*`。

## 一、删除是否彻底且不过度

| 核对项 | 结论 |
|---|---|
| `rg -n -i "intelligence" frontend --glob '!node_modules' --glob '!.next' --glob '!**/enums.ts'` | 无输出（exit=1）；不排除 `.next` 同样无输出 |
| `enums.ts` 枚举成员 | `AiModelType`（`:34` `'intelligence'`）、`AiUsageType`（`:35` `'intelligence_summary'`）、`NotificationCategory`（`:38` `'intelligence'`）**仍在**；只删了 `// === 情报 ===` 段的三个类型别名 `IntelligenceSourceType / IntelligenceArticleStatus / ArticlePublicationStatus`（design §6 `enums.ts:30-33` 删除项），与设计一致 |
| `api.ts` 删 `IntelFilters` / `ImportResult` | `git grep HEAD` 核证：两者的全部引用只在已删文件（`admin/intelligence-sources/client-page.tsx`、`shared-api/src/admin/intelligence-sources.ts`、`shared-api/src/tenant/intelligence.ts`）；`models.ts` 删的 `FetchConfig` 同理。现工作区 `rg "IntelFilters|ImportResult|FetchConfig|情报" frontend` 无输出 |
| `shared-api` 三个 index + `query-keys.ts` | 逐 hunk 看：`admin/index.ts` 只删 `intelligenceSourcesApi` 导入与注册，`industryNewsSourcesApi` 相邻行保留；`tenant/index.ts` 只删 `intelligenceApi` 两行；`src/index.ts` 只删两条类型再导出，`IndustryNews*` 再导出保留；`query-keys.ts` 删 tenant 区 `intelligence` 与 admin 区 `intelligenceSources` 两组，`industryNews` / `emailTemplates` / `scoringTemplates` 相邻组完整。无误删 |
| `shared-types/src/index.ts` | `export *` 四文件，无具名导出残留 |
| 导航 / middleware / 权限表 | tenant `navigation.ts:30` → `/industry-news`，admin `navigation.ts:33` → `/industry-news-sources`（PR A 已改）；`rg "intelligence-sources|tenant/intelligence|admin/intelligence" frontend` 无输出 |

## 二、`ai-config/client-page.tsx` 健壮性

- 删了 `SCENE_LABELS.intelligence_summary` 与灌入 state 时的 `.filter(scene !== 'intelligence_summary')`（后者是 PR A 的过渡措施，PR B 迁移删除该场景默认行后为死代码；`init_instance.py` 也不再种该场景）。
- `AiSceneDefault.scene` 为开放 `string`（`shared-api/src/admin/ai-config.ts:15`），渲染处 `SCENE_LABELS[record.scene] ?? record.scene` 有兜底：若前端先于后端发布、或后端 Literal 仍接受该值而被外部 PUT 回灌，页面只会显示原始键名，不崩、不丢其他场景。
- 「删除模型」失败 toast 显示后端原因（PR A 的 CR7 处置）保留。结论：健壮。

## 三、文档 / spec

### 引用的文件 / 符号 / 路由逐个核证（rg）

| 引用 | 存在 |
|---|---|
| `api-guidelines.md`：`ScoringTemplateCreate` / `ScoringTemplateUpdate`（`schemas/admin_config.py:17,122`）、`admin/config.py::update_platform_scoring_template`（`:63`，`model_dump(exclude_unset=True)` `:72`） | ✅ |
| `api-guidelines.md`：`admin/industry_news_sources.py` `POST /fetch`（`:24`）定义在 `PATCH /{source_id}`（`:31`）之前 | ✅ |
| `error-handling.md`：`app/services/industry_news/service.py::run_once`（`:273`）；`FetchError`（`fetchers.py:43`）；savepoint `begin_nested`（`service.py:304,311`）与单源 `error_count +1`（`_SQL_MARK_ERROR`） | ✅ |
| `directory-structure.md` / `state-management.md`：`apps/tenant/src/app/(dashboard)/industry-news/page.tsx` | ✅ |
| `state-management.md`：`queryKeys.industryNews.list / .filters / .all`（`query-keys.ts:35-39`） | ✅ |
| `quality-guidelines.md`：`test/industry-news/industry-news-page.test.tsx` | ✅ |
| `component-guidelines.md:327`：动态源列表 `type: 'boolean'` + `booleanMode: 'interactive'`（`admin/industry-news-sources/client-page.tsx:101-103`） | ✅ |
| `database-guidelines.md:44`、`schema_notes.md:31`：`partitions.py` 只管 `audit_logs` / `emails`；`maintain_partitions.py` 只维护两表 | ✅（与 backend diff 一致） |
| `schema_notes.md:102`「#49 关闭」 | ✅ `gh issue view 49` → CLOSED（2026-08-23） |
| `schema_docs.json` `notifications`「当前无写入路径」 | ✅ `rg "INSERT INTO notifications" backend/app backend/scripts` 无输出 |
| `schema_docs.json` `ai_usage_logs`「AI 功能（邮件生成）经 AiUsageLogService 写入」 | ✅ `tenant_messaging_service.py:15,38` |

### `schema_docs.json`

`json.load` 通过；`domains` 无「行业情报」，含「行业动态」（三表）；`tables` 无 `intelligence_*`；domains 与 tables 双向一致（无孤儿表、无未分域表）。

### 剩余 `intelligence|情报` 命中（全部为「已删除 / 历史值 / 保留枚举」类说明）

- `schema_notes.md:31`（随 0002 移出）、`:102`（已删除、#49 关闭）
- `schema_docs.json:201`（notifications 原写入方已删）、`:205`（CHECK 枚举保留）、`:206` / `:230`（`entity_type` 历史值）
- `README.md:154` / `:169`（旧页面与表已随 PR B 删除）
- `domain-rules.md:20`（情报摘要场景随模块删除）、`database-guidelines.md:44`（已随 0002 删除）

### 发现并修正（4 处，均为改后仍指向已删符号 / 不存在字段的 spec 漂移）

1. `.trellis/spec/backend/api-guidelines.md:9`：Literal 示例 `source_type: Literal["rss", "website", "manual"]` 来自已删的 `IntelligenceSourceCreate`，全仓已不存在 → 改为 `TenantUserCreate.status: Literal["active", "disabled"]`（`schemas/admin_config.py:87`，对应快照 `users_status_check`）。
2. `.trellis/spec/backend/error-handling.md:17`：404 消息示例「文章不存在或未发布给当前租户」随 `intelligence_service` 消失 → 改为「动态不存在或无权访问」（`industry_news/service.py::mark_read`）。
3. `.trellis/spec/frontend/type-safety.md:15-16`：① 联合类型示例 `'rss' | 'website' | 'manual'` 是已删的 `IntelligenceSourceType` → 改 `IndustryNewsStrategy = 'rss' | 'html' | 'jsonld'`（`models.ts:406`）；② 原改写引用 `IndustryNewsSource.parse_config`，但前端类型没有该字段（管理端 GET 不返回 `parse_config`，design §4）→ 改为真实存在的 `AiModel.config` / `Tenant.settings`；顺带删「存量 `unknown[]`」说法（shared-types 已无 `unknown[]`）。
4. `.trellis/spec/frontend/state-management.md:19`：事实来源改指向 `industry-news/page.tsx`，但该页「点击标题置已读」有意不 invalidate 列表（design §5.1 F5，用户已确认），与同节「mutation 成功后 invalidate」规则表面冲突 → 补一句已确认例外的说明（页面本地 `clickedIds`，失败回滚 + toast），避免读者把范例页当违规。

## 四、门禁（全部通过，复审时重跑）

- `cd frontend && pnpm type-check`：6 个包全部 Done（`.next/types` 已由本轮 build 再生，无 TS2307）。
- `pnpm --filter @apps/tenant test`：17 files / 60 tests passed。
- `pnpm --filter @shared/ui test`：21 files / 85 tests passed。
- `pnpm build:tenant`：✓ Compiled，17 路由，含 `/industry-news`，无 `/intelligence*`。
- `pnpm build:admin`：✓ Compiled，20 路由，含 `/industry-news-sources`，无 `/intelligence-sources`。
- build 后 `git status` 无新增被跟踪文件改动（产物在 `.next/`，已忽略）。

## 五、非阻断观察（留给协调者）

- `schema_notes.md:30`「`backend/alembic/versions/`（70 个迁移）」在 HEAD 时已是 73，PR B 后为 74；属 2026-07-22 快照性计数的既有漂移，不在 PR B 清单内，未改。
- `docs/database-schema.md` / `.dbml` 仍含 `intelligence_*` 四表，按 design §2 / §7 留到发布后 `schema_snapshot.py --prod` 再生，本 PR 不动（符合计划）。
- 发布顺序：前端 B 四套镜像与 backend B 需同批发布；若前端先上而迁移未跑，AI 配置页会短暂显示原始键 `intelligence_summary`（有兜底，不崩）。
