<!-- /autoplan restore point: /Users/lay/.gstack/projects/client_get/main-autoplan-restore-20260512-212940.md -->
## Context

V3 反推链路中，租户关键词归一为平台关键词后，系统通过励销云 stage 1 采集中国同行/供应商。当前 `lixiaoyun_raw_companies` 以 `(keyword_master_id, source_id)` 保留 raw 证据，因此同一家公司被多个关键词采到时会保留多行。现有 Admin 同行公司页仍作为 raw 视图保留；本 change 新增独立“同行公司（清洗）”页，展示去重后的同行公司池。

已有 D-008 约束指出：励销云不进入海外客户 `clean_companies`，只作为 stage 2 输入。这个边界仍然成立。本 change 新增的是平台内部同行清洗层，不是租户客户库，也不修改 Tendata stage 2 反查链路。

## Goals / Non-Goals

**Goals:**

- 建立励销云 raw → peer company 的同行清洗 v1 规则。
- 新增 Admin “同行公司（清洗）”页，用 Next.js 实现去重同行公司视图；原 Admin 同行公司页保持不变。
- 新增清洗页列表默认字段和筛选条件与现有同行公司页保持一致，详情页补充是否有英文名、raw 数、关键词数。
- 保留 raw 证据和 raw → peer 的追溯关系。
- 对历史 raw 数据提供 backfill，使旧数据也能进入 peer 层。
- 使用 Next.js 实现本次 Admin 同行公司清洗页，作为后续 Admin 迁移到 Next.js 全栈的试点。

**Non-Goals:**

- 不把励销云同行写入海外客户 `clean_companies`。
- 不把同行公司直接物化给租户公司列表。
- 不做模糊匹配、人工合并或主体拆分。
- 不新增专门的 5 分钟 peer 清洗轮询 worker。
- 不改变 Tendata stage 2 buyer lookup 输入构造、执行、重试或去重逻辑。
- 不新增 peer 级 Tendata lookup ledger。
- 不迁移 `tendata_raw_companies.keyword_master_id`，也不新增 `keyword_master_ids[]`；该需求移入后续 “Tendata 从 peer pool 反查” change。
- 不替换、删除或重写原 Admin 同行公司页。
- 不改变励销云采集分页、跨天续采、每日上限、停止/重试规则。
- 不在本 change 完成整个 Admin Vite 应用到 Next.js 的全量迁移；仅新增同行公司清洗页相关 Next.js 页面/入口。

## Decisions

### D1. 新增独立 peer clean 层，不复用 `clean_companies`

新增平台内部同行实体层，建议表结构为：

- `peer_companies`：去重后的同行公司，一家公司一行。
- `peer_company_keywords`：同行公司与平台关键词的多对多命中关系。
- `peer_company_sources`：同行公司与 `lixiaoyun_raw_companies` raw 行的追溯关系。

不复用 `clean_companies`，因为 `clean_companies` 当前表达海外客户公司池，并通过 Tendata/外贸通来源服务租户客户列表。励销云同行是中国供应商/同行，不应进入租户客户资产。

替代方案：

- 只在 Admin API 上 `GROUP BY` raw 行：实现轻，但无法给 worker 提供稳定输入池。
- 让励销云进入 `clean_companies`：模型复用多，但破坏 D-008 边界，且会让客户库混入中国同行。

### D2. 同行公司 v1 去重主键优先使用 website host，其次使用 source_id

清洗时生成稳定 `identity_type` + `identity_value`：

1. raw 有 `domain` / `officialWebsite` 时，取规范化 website host：去协议、去路径/query/hash、转小写、去尾部斜杠、去常见 `www.` 前缀。
2. 无有效 website host 时，使用 `source_id`，即励销云 API 返回公司条目的内部 id。

唯一约束建议为 `UNIQUE (identity_type, identity_value)`。

原因：官网域名比关键词下的 raw 行更接近真实公司身份；source_id 是励销云返回的公司条目 id，可作为无官网时的稳定 fallback。当前 raw 表保留 `(keyword_master_id, source_id)`，允许同一 source_id 因不同关键词出现多行；peer 层再把这些命中合并。

边界：

- 如果没有 website host 且没有 source_id，则该 raw 不进入 peer 层，但 raw 仍保留用于排查。
- 第一版不使用中文名或英文名作为去重主键，避免同名误合并和别名漏合并。
- v1 不做在线 identity re-parent / merge。raw source 首次关联到 peer 后，后续如果同一 raw 补到了 website host，只补充 `domain` / `website_host` 等展示字段和诊断信息，不自动把 `source_id` identity 改迁到 `website` identity，也不在线合并两个 peer。后续如需身份重算或人工 merge，另开 change 处理。

### D3. 字段合并保持简单：非空补空，关键词和来源追加去重

`peer_companies` 保存用于展示和后续 Tendata 输入的字段：

- 中文名、英文名、website host/domain、成立日期、法人、统一社会信用代码、注册资本、员工规模、注册地址、联系人数量、首次/最近命中时间。

字段合并 v1 规则：

- 稳定身份字段由 identity 决定，不被后续 raw 改写。
- 展示字段优先非空补空；后续 raw 有更完整英文名、域名、工商字段时可补齐空值。
- `peer_company_keywords` 追加去重，不覆盖旧关键词。
- `peer_company_sources` 追加每条 raw 来源，保留 `raw_company_id`。
- `last_seen_at` 每次命中更新，`first_seen_at` 保留首次命中。

### D4. 励销云 raw 写入时同步 upsert peer 层

主路径不新增 5 分钟轮询任务。`_upsert_lixiaoyun_raw` 成功写入 raw 后，在同一事务内 upsert peer 层和关系表。

原因：同行清洗轻量，不涉及 tenant materialization 和联系人深度清洗；同步写入最简单，也避免 Admin 页面出现“raw 已有但 peer 还没清洗”的短暂不一致。

失败策略采用 raw + peer 强一致：如果 peer upsert 或关系表写入失败，本次 raw 写入事务也失败，让 collection task 通过现有重试机制重跑。不得吞掉 peer 错误后只依赖 backfill 修复在线数据，否则新增清洗页会出现沉默漏数。

补偿路径保留一个脚本或 service 方法，用于按同一规则扫描历史 `lixiaoyun_raw_companies` 并重建 peer 层。

### D5. 新增 Admin “同行公司（清洗）”页，以 peer 层为列表真源，并用 Next.js 实现

新增独立 Admin “同行公司（清洗）”页读取 peer 层，建议路由为 `/collection/peers-cleaned`。原 Admin 同行公司页继续读取当前 raw 数据并保持原行为。本次新增页使用 Next.js 实现，作为后续 Admin 迁移到 Next.js 全栈的试点；现有 Vite Admin 只需要提供菜单入口、跳转或临时并存，避免把整个 Admin 迁移绑进本 change。

Next.js 落点采用正式 monorepo app：在 `frontend/apps/admin-next` 新增 Admin Next.js 试点应用，复用 `frontend/packages/shared-api` / `frontend/packages/shared-types` 的类型与 API 约定。`nextjs-spike/` 只能作为技术参考，不作为生产页面直接部署或继续扩展，避免形成两套 Admin 运行时、认证、构建和 API client。

部署采用独立 Next.js 运行时：新增 `clientget-admin-next` 镜像，`frontend/apps/admin-next` 使用 Next.js `output: 'standalone'` 构建为 Node server。现有 `clientget-admin` Vite/nginx 镜像不承载 Next.js 页面，只提供到 admin-next `/collection/peers-cleaned` 的入口或跳转。上线时需要新增 Sealos 应用或入口规则，把 admin-next 暴露给管理员访问。

当 `clientget-admin-next` 使用独立公网域名时，浏览器不会共享 `admin.xinanpcb.com` 的 `sessionStorage`。现有 Vite Admin 入口需要把当前 Admin session token 通过 URL hash 一次性传给 admin-next；admin-next 首次加载后读取 hash、写入本域 `sessionStorage`，并立即清理地址栏 hash。token 不得放入 query string，避免进入服务端访问日志。

独立域名的 admin-next 页面不能把用户困在单页体验里。清洗页需要提供与现有 Admin 一致的左侧菜单壳；当前清洗页高亮，点击其他菜单时回跳到现有 Vite Admin 公网入口。这样 Next.js 试点页仍是独立运行时，但运营能从左侧菜单回到其他后台功能。

`admin-next` 作为 pnpm workspace app 时，Next config 需要显式配置 `transpilePackages`，让 Next 编译本地 workspace 包。至少覆盖 `@shared/api`、`@shared/types`；如果页面直接使用共享 hooks/ui，也覆盖 `@shared/hooks`、`@shared/ui`。

新增清洗页的列表默认字段和筛选条件必须与现有同行公司页保持一致。列表仍展示同行公司业务字段和关键词数组，不新增 lookup 状态、失败原因、是否已反查、buyer_count / Tendata 结果数等列。

清洗页中的联系人数量是 peer 级聚合值，不是单条 raw 行字段：统计该 peer 关联的所有 `lixiaoyun_raw_contacts`，按 `email` 优先去重；没有 email 时按 `source_contact_id` 去重；两者都没有时按 raw contact id 兜底计数。联系人数量筛选也按这个 peer 聚合值执行。

列表 API 必须批量聚合 keywords、raw_count、source_ids、contact_count，不允许对每个 peer 再单独查询 keywords/sources/contacts。backfill 必须按主键分页或分批处理历史 raw，不能一次性把全表读入内存。

API 响应至少包含：

- `id`
- `name`
- `english_name`
- `has_english_name`
- `domain` / `website_host`
- `keywords`: `{ keyword_master_id, keyword, keyword_normalized }[]`
- `keyword_count`
- `source_ids`: 励销云 source_id 去重数组或计数
- `raw_count`
- 现有展示字段：成立日期、法人、统一社会信用代码、注册资本、员工规模、注册地址、联系人数量、首次/最近命中时间

筛选继续支持公司名、英文名、官网、关键词、工商字段、联系人数量等现有同行页查询意图，并与现有同行公司页保持一致。

详情页展示合并后的同行字段、关键词数组、raw/source 统计，并明确展示：

- 是否有英文名
- raw 数
- 关键词数

详情页不展示 lookup 状态、失败原因、最近命中时间、buyer_count / Tendata 结果数、是否已反查。

### D6. Tendata 反查链路移出本 change

后续 “Tendata 从 peer pool 反查” change 再处理以下事项：

- buyer lookup 输入从 raw competitors 切换为 peer companies。
- 同一 peer company 多关键词命中时只反查一次。
- peer 级 Tendata lookup ledger、失败重试、attempt、结果统计。
- `tendata_raw_companies.keyword_master_id` 数组语义或 `keyword_master_ids[]` 迁移。

本 change 只保证 peer pool 本身已经具备未来所需的公司去重、关键词数组和 raw 证据追溯能力。

### D7. Admin 页面字段裁决

用户已确认新增 Admin “同行公司（清洗）”页：

- 列表默认字段和筛选条件与现有同行公司页保持一致。
- 详情页展示是否有英文名、raw 数、关键词数。
- 移除 lookup 状态、失败原因、最近命中时间、buyer_count / Tendata 结果数、是否已反查等前端展示字段。
- 原 Admin 同行公司页保持不变。

字段分层如下：

| 层级 | 字段 | 展示位置 |
| --- | --- | --- |
| 列表字段 | 与现有同行公司页一致，包括原有公司、官网、关键词、工商、联系人等字段口径 | 列表 |
| 筛选条件 | 与现有同行公司页一致 | 筛选区 |
| 新增聚合 | 是否有英文名、raw 数、关键词数 | 详情页 |

## Risks / Trade-offs

- [官网域名误合并] 多家公司共用集团官网或平台页可能被合并 → 第一版接受该风险；Admin 可通过 raw source 追溯发现，后续再做人工拆分。
- [source_id 作用域不明] 如果励销云 source_id 不是全局公司 id，而只是搜索结果 id，fallback 可能漏合并 → 有官网时优先官网；无官网时宁可漏合并，不做中文名模糊合并。
- [后补官网不自动合并] 首次无官网时按 source_id 建 peer，后续补官网不会自动迁移到 website identity → v1 接受少量漏合并，换取清洗链路简单、幂等、可回滚。
- [英文名缺失] 去重同行没有英文名时后续无法作为 Tendata 输入 → 新增清洗页仍展示该同行，并在详情显示是否有英文名。
- [同步 upsert 增加采集写入成本] raw 写入时多写几张表 → 关系表 upsert 简单、索引明确，成本可控；批量采集仍按同一事务处理。
- [历史数据不一致] 部署后旧 raw 未 backfill 会导致 Admin peer 页缺历史 → migration 后必须运行 backfill，并记录 dry-run/执行统计。
- [Next.js 试点范围] 当前正式 Admin 是 Vite app，Next.js 只有 spike → 本 change 只把同行公司控制台作为 Next.js 试点，不把全 Admin 迁移纳入范围。

## Migration Plan

1. 新增 Alembic migration：创建 `peer_companies`、`peer_company_keywords`、`peer_company_sources` 及唯一约束/索引。
2. 后端实现 peer upsert service，并在励销云 raw upsert 成功后同事务调用。
3. 新增 backfill 脚本或命令：扫描历史 `lixiaoyun_raw_companies`，按同一规则重建 peer 层，支持 dry-run。
4. 新增 Admin peer cleaning API，使其返回新增清洗页所需字段。
5. 在 `frontend/apps/admin-next` 使用 Next.js 实现 Admin “同行公司（清洗）”页面；现有 Vite Admin 提供菜单入口、跳转或兼容壳。
6. 新增 admin-next 构建/镜像脚本，产出独立 `clientget-admin-next` 镜像，并记录 Sealos 入口配置要求。
7. 部署后先运行 migration，再运行 peer backfill，再发布/验证新增清洗页。

Rollback：

- 前端可隐藏 Vite Admin 中的 Next.js “同行公司（清洗）”入口，并停止或回滚 `clientget-admin-next` 应用；原 Admin 同行公司页不受影响。
- 后端 raw 表不受破坏；peer 表可保留不用。

## Open Questions

- 无待实施者自行裁决的 Open Question。
- 用户已确认原 Admin 同行公司页不变，本 change 新增“同行公司（清洗）”页。
- 用户已确认 `tendata_raw_companies.keyword_master_id` 数组语义移出本 change，放入后续 “Tendata 从 peer pool 反查” change。
- 用户已确认新增清洗页使用 Next.js 实现；列表默认字段和筛选条件与现有同行公司页一致，详情页仅补充是否有英文名、raw 数、关键词数。
- 用户已确认在线写入采用 raw + peer 同事务强一致；peer upsert 失败时 raw 写入失败并由 collection task 重试。
- 用户已确认 Next.js 试点页落在 `frontend/apps/admin-next`，不直接把 `nextjs-spike/` 转成生产页面。
- 用户已确认 v1 不做在线 identity re-parent / merge；raw source 首次关联 peer 后，后补官网只补字段和诊断，不自动改变 peer identity。
- 用户已确认清洗页联系人数量使用 peer 级去重聚合：email 优先，source_contact_id 次之，raw contact id 兜底；联系人筛选按聚合值执行。
- 用户已确认 Next.js Admin 试点采用独立 `clientget-admin-next` 镜像和 Next standalone 运行时，现有 Vite Admin 只提供入口/跳转。

## Eng Review Report

本节由 `/plan-eng-review` 在 2026-05-12 追加，基于已收窄后的范围：新增同行公司清洗层与 Admin “同行公司（清洗）”页；原同行公司页、Tendata 反查链路、`tendata_raw_companies.keyword_master_id` 均不改。

### Step 0: Scope Challenge

复杂度阈值触发：本 change 仍会触及数据库 migration、采集写入、backfill、Admin API、shared API、Next.js 新 app、Vite 入口、镜像构建和测试。收窄后的范围可以接受，因为这些都是“新增清洗页可信可用”所需的最小闭环。

明确不再继续砍范围；真正的 scope guard 是不碰 Tendata 执行链路、不替换原同行公司页、不把 `nextjs-spike/` 转正。

### What Already Exists

| Sub-problem | Existing Code / Flow | Review Decision |
| --- | --- | --- |
| 励销云 raw 写入 | `backend/app/services/collection_service.py::_upsert_lixiaoyun_raw` | 复用为在线 peer upsert 入口，并改为返回 raw id |
| raw 证据唯一性 | `lixiaoyun_raw_companies` 现有 `(keyword_master_id, source_id)` 唯一约束 | 保留 raw 证据层，不改唯一约束 |
| 原同行公司页 | `frontend/apps/admin/src/pages/PeersData/index.tsx` | 保持原 raw 视图不变，只新增入口 |
| 原 Admin raw API | `AdminCollectionService.list_v3_raw_companies` | 原 API 保持兼容；新增 peer cleaning API，不把原 API 改成 peer API |
| 多关键词关系范式 | `clean_company_keywords` | 借鉴多对多关系，但新建 `peer_company_keywords` |
| 租户级同行模型 | `competitor_companies` | 不复用，需在 migration/code 注释说明边界 |
| Next.js spike | `nextjs-spike/` | 仅作参考；正式 app 放在 `frontend/apps/admin-next` |

### Architecture Review

1. [P1] (confidence: 9/10) `openspec/changes/admin-peer-company-cleaning/design.md` — 在线写入失败策略原先不明确，已裁决为 raw + peer 同事务强一致，peer 失败则 raw 失败并由 collection task 重试。
2. [P1] (confidence: 9/10) `frontend/` / `nextjs-spike/` — Next.js 生产落点原先不明确，已裁决为 `frontend/apps/admin-next`，`nextjs-spike/` 不转正。
3. [P2] (confidence: 8/10) peer identity flow — 后补官网可能触发 identity 迁移复杂度，已裁决 v1 不做在线 re-parent / merge。
4. [P2] (confidence: 8/10) peer contact aggregation — 清洗页联系人数量原先口径不清，已裁决为 peer 级去重聚合。
5. [P1] (confidence: 9/10) deployment — Next.js 页面原先没有发布路径，已裁决新增独立 `clientget-admin-next` standalone 镜像。

### Code Quality Review

1. [P2] (confidence: 8/10) backend service shape — 建议实现一个单一 `PeerCompanyCleaningService` 或等价模块，供 online upsert 与 backfill 共用；避免 online/backfill 各写一套 identity 与 merge 逻辑。
2. [P2] (confidence: 8/10) Admin filter parity — 新 API 必须复用或镜像原同行页筛选语义；字段名可以是 peer API 专用，但筛选口径不得悄悄分叉。
3. [P2] (confidence: 8/10) Next monorepo build — `admin-next` 必须配置 `transpilePackages` 编译 workspace 包，避免 shared packages 在 Next build 中失败。
4. [P3] (confidence: 7/10) historical Autoplan section — 历史 autoplan 仍包含 Tendata/ledger 建议，已加 superseded note；实现者必须以本节前面的 Decisions / Tasks 为准。

### Test Review

```text
CODE PATH COVERAGE PLAN
=======================
[GAP] DB migration
  ├─ peer_companies unique(identity_type, identity_value)
  ├─ peer_company_keywords unique(peer_company_id, keyword_master_id)
  ├─ peer_company_sources unique(raw_company_id)
  └─ schema.sql parity

[GAP] PeerCompanyCleaningService
  ├─ website normalize: protocol/path/query/case/www/blank
  ├─ identity: website > source_id > skip
  ├─ no online re-parent after source_id fallback
  ├─ field merge: non-empty fills empty, last_seen_at updates
  ├─ keyword/source relation idempotency
  └─ raw + peer transaction rollback on peer failure

[GAP] Backfill
  ├─ dry-run reports counts and mutates nothing
  ├─ actual run creates peer/source/keyword
  ├─ repeated run is idempotent
  └─ batches by primary key, no full-table memory load

[GAP] Admin peer cleaning API
  ├─ list returns one row per peer
  ├─ keyword filter returns peer and full keyword array
  ├─ contact count dedup: email > source_contact_id > raw contact id
  ├─ empty result total=0
  ├─ no lookup/Tendata fields required by UI
  └─ original raw API contract remains unchanged

[GAP] admin-next page
  ├─ uses peer cleaning API, not raw API
  ├─ columns/filter parity with original peer page
  ├─ detail shows only has_english_name/raw_count/keyword_count additions
  ├─ forbidden lookup/Tendata fields absent
  ├─ loading/error/empty states
  └─ next.config output standalone + transpilePackages

USER FLOW COVERAGE PLAN
=======================
[GAP] Existing `/collection/peers` raw page still works
[GAP] Vite Admin entry opens `/collection/peers-cleaned`
[GAP] Same company via multiple keywords renders one row
[GAP] Backfill dry-run -> actual -> rerun keeps counts stable
[GAP] `clientget-admin-next` standalone build/image can reach backend API

Coverage before implementation: 0 tested / 29 planned paths.
Required test additions are captured in tasks 5.x, 6.x, and 7.x.
```

Test plan artifact written for QA consumption:

`/Users/lay/.gstack/projects/client_get/lay-main-eng-review-test-plan-20260512-231300.md`

### Performance Review

1. [P1] (confidence: 8/10) peer list API — keywords/raw/source/contact aggregates must be computed in SQL batches; N+1 per peer will become visibly slow on Admin pagination.
2. [P2] (confidence: 8/10) indexes — add indexes for `peer_company_keywords(keyword_master_id, peer_company_id)`, `peer_company_sources(peer_company_id)`, and confirm existing `lixiaoyun_raw_contacts(raw_company_id)` is used.
3. [P2] (confidence: 8/10) backfill — must batch by raw id or equivalent cursor, not load all historical raw rows into memory.

### NOT In Scope

- Tendata buyer lookup input switch: deferred to “Tendata 从 peer pool 反查”.
- Peer-level Tendata lookup ledger: deferred with Tendata execution change.
- `tendata_raw_companies.keyword_master_id` array migration / `keyword_master_ids[]`: deferred with Tendata attribution change.
- Replacing original Admin 同行公司页: explicitly out; original raw page remains.
- Online identity re-parent / automatic merge: deferred to future identity merge/change if needed.
- Full Admin migration to Next.js: out; this change only creates `admin-next` pilot app and one page.

### Failure Modes

| Failure Mode | Covered By Plan | User Impact |
| --- | --- | --- |
| peer upsert fails after raw insert | raw + peer same transaction + rollback test | task retries instead of silent missing peer |
| same raw later gains website | no re-parent test | no surprise merge; possible accepted漏合并 |
| list API does N+1 aggregates | performance tasks/indexes | avoids slow Admin page |
| backfill interrupted mid-run | idempotent upsert + rerun test | operator can rerun safely |
| original raw page broken by new entry | regression/source contract test | protects existing workflow |
| admin-next cannot build workspace packages | `transpilePackages` contract test | catches before deploy |
| forbidden Tendata fields appear in UI | source constraint test | keeps page scope aligned with user decision |

Critical silent gaps after review: 0, assuming tasks are implemented as written.

### Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| DB migration/schema | `backend/alembic`, `backend/03_database` | none |
| Peer cleaning service + collection hook | `backend/app/services` | DB migration |
| Backfill script | `backend/scripts`, service | Peer cleaning service |
| Admin peer cleaning API | `backend/app/api`, `backend/app/services` | DB migration |
| Shared API/types | `frontend/packages/shared-api`, `frontend/packages/shared-types` | Admin API contract |
| admin-next app/page | `frontend/apps/admin-next` | Shared API/types |
| Vite Admin entry | `frontend/apps/admin` | admin-next route decision |
| Docker/deploy | `frontend/Dockerfile*`, `frontend/deploy` | admin-next app |

Parallel lanes:

- Lane A: DB migration/schema -> peer cleaning service -> backfill.
- Lane B: Admin peer cleaning API, after DB migration.
- Lane C: admin-next scaffold/build config can start in parallel, then wire API after shared types exist.
- Lane D: Vite Admin entry and deploy scripts after admin-next route/image name is stable.

Execution order: start DB migration first. Then run Lane A service/backfill and Lane B API in parallel. Start admin-next scaffold in parallel with API, but wire final data once API types land. Deploy scripts last.

Conflict flags: backend service/API lanes both touch `backend/app/services`; coordinate or keep sequential if one person is implementing.

## Autoplan Review Report

本节由 `/autoplan` 在 2026-05-12 评审 `admin-peer-company-cleaning` 后追加。它不代表已经实施，只代表实施前需要锁定的方案判断。

> Superseded scope note, 2026-05-12: 后续用户已裁决本 change 只新增同行公司清洗层与 Admin “同行公司（清洗）”页；原同行公司页保持不变。Tendata 反查输入切换、peer 级 lookup ledger、`tendata_raw_companies.keyword_master_id` 数组语义或 `keyword_master_ids[]` 迁移均移出本 change，进入后续 “Tendata 从 peer pool 反查” change。以下 Autoplan 内容保留为历史评审记录，不作为本 change 实施范围。

### Review Summary

当前方案方向成立：Admin 不应继续把 `lixiaoyun_raw_companies` 一条 raw 一行当作同行公司列表，Tendata stage 2 也不应从重复 raw 行直接生成反查输入。

但两个独立 CEO 视角都指出同一个更大的问题：这个 change 不只是“同行公司展示清洗”，更像是在建立 stage 2 的同行查询输入池。若只新增 peer 表和 Admin 去重展示，而不设计 peer 级 Tendata 反查台账、归因、状态与运营观测，后续仍会在任务层和 raw 层反复补幂等。

推荐把本 change 的实施目标修正为：

> 建立可解释、可追溯、可运营的 peer company input pool；Admin 展示去重同行只是其中一个入口，Tendata 反查幂等与归因才是主路径收益。

### CEO Review

#### Premise Challenge

| Premise | Evaluation | Decision |
| --- | --- | --- |
| Admin raw 重复展示值得修 | 成立，但不是最大收益点 | 保留，但不作为唯一目标 |
| 同一公司多关键词命中时 Tendata 应只查一次 | 大体成立，但必须保留多关键词语境归因 | 保留 peer 级去重，禁止丢归因 |
| 英文同行名是 Tendata 合理输入 | 有风险，英文名缺失、别名、品牌名不一致会影响召回 | 增加可反查数、英文名覆盖率、命中率指标 |
| website host 优先于 source_id | v1 可接受，但会误合并集团官网、平台页、代理站 | 增加身份来源、置信度、冲突观测 |
| source_id 可作为 fallback | 需明确：它是励销云 API 返回条目的内部 id，来自 `item.get("id")`，不是本地 DB id | 实施前抽样确认其公司级稳定性 |
| 不做 5 分钟轮询，随 raw upsert 同步清洗 | 成立，简单且一致 | 保留，同步失败策略需明确 |

#### What Already Exists

| Sub-problem | Existing Code / Schema | Leverage |
| --- | --- | --- |
| 励销云 raw 入库 | `backend/app/services/collection_service.py` 的 `_upsert_lixiaoyun_raw` | 在线 upsert peer 层应挂在这里 |
| raw 表唯一性 | `lixiaoyun_raw_companies` 当前以 `(keyword_master_id, source_id)` 保留证据 | peer 层可在 raw 之上做跨关键词合并 |
| Admin 同行页 | `frontend/apps/admin/src/pages/PeersData/index.tsx` 当前读 `listV3RawCompanies('lixiaoyun')` | 前端只需从 raw API 切到 peer API，表格语义要改 |
| Admin raw API | `backend/app/services/admin_collection_service.py` 的 `list_v3_raw_companies` | 可复用筛选/分页思路，但查询真源要换 peer 层 |
| Tendata stage 2 输入 | `collection_service.py` 当前从 competitors 提取 `company_name_en` | 需要改成 peer company 输入池 |
| Tendata raw 归因限制 | `tendata_raw_companies` 当前单 `keyword_master_id` | 多关键词归因不能靠重复反查解决 |
| 既有关键词关系模式 | `clean_company_keywords` | 可借鉴多对多关键词关系建模 |
| 既有 `competitor_companies` | migration 中存在租户级 competitor 模型 | 必须明确它与新 peer 层边界，避免三套同行概念并存 |

#### Dream State Delta

```text
CURRENT
  Lixiaoyun raw rows
      │  one row per keyword hit
      ▼
  Admin duplicates + Tendata may duplicate lookup

THIS PLAN, AFTER REVIEW
  Lixiaoyun raw evidence
      │
      ▼
  Peer company input pool
      ├─ identity: website_host > source_id
      ├─ keywords[] attribution
      ├─ raw sources[]
      ├─ lookup ledger/status
      └─ observability metrics
      │
      ├─ Admin peer console
      └─ Tendata stage 2 deduped lookup

12-MONTH IDEAL
  Peer intelligence asset
      ├─ merge/split overrides
      ├─ query aliases / preferred English names
      ├─ per-peer ROI and buyer yield
      ├─ replayable cleaning rule versions
      └─ explainable attribution into customer outcomes
```

#### Alternatives

| Approach | Effort | Pros | Cons | Decision |
| --- | --- | --- | --- | --- |
| A. Admin API `GROUP BY` raw | Low | 最快解决展示重复 | worker 没有稳定输入池，Tendata 幂等仍散落 | Reject |
| B. 独立 peer company clean 层 | Medium | 保持 D-008 边界，支持 Admin 与 Tendata 共用 | 需要新增表、backfill、API | Accept as base |
| C. peer company input pool + lookup ledger | Medium+ | 同时解决展示、反查幂等、状态、配额观测 | v1 范围扩大，需多一张台账或等价状态模型 | User Challenge, recommended |
| D. 复用 `clean_companies` | Medium | 复用客户库能力 | 污染海外客户资产，破坏 D-008 | Reject |
| E. 复用/改造 `competitor_companies` | Unknown | 可能减少概念债 | 现有模型偏 tenant 级，与平台 peer pool 边界不清 | Must evaluate before implementation |

#### CEO Dual Voices Consensus

```text
CEO DUAL VOICES -- CONSENSUS TABLE
===============================================================
Dimension                            Subagent  Codex   Consensus
──────────────────────────────────── ──────── ─────── ─────────
1. Premises valid?                   partial  partial CONFIRMED
2. Right problem to solve?           no       no      USER CHALLENGE
3. Scope calibration correct?        no       no      USER CHALLENGE
4. Alternatives sufficiently explored? no     no      CONFIRMED GAP
5. Competitive/business risks covered? no     no      CONFIRMED GAP
6. 6-month trajectory sound?         weak     weak    CONFIRMED GAP
===============================================================
```

两个声音的共同建议：不要只做“去重表”。至少把 Tendata peer 级反查状态、关键词归因、运营指标纳入方案，否则半年后会变成概念债和归因债。

### Design Review

UI scope detected: Admin 同行公司页会从 raw 表变为 peer company 控制台。

#### Design Scorecard

| Dimension | Score | Finding | Required Plan Clarification |
| --- | ---: | --- | --- |
| Information hierarchy | 6/10 | 当前计划只说一行一个 peer，没说明运营最先看什么 | 首屏应突出“是否可反查”：英文名、反查状态、关键词数、raw 数、最近命中 |
| States | 5/10 | loading/empty/error/backfill partial 未定义 | 增加空态、无英文名、未 backfill、反查失败、部分归因缺失状态 |
| Interaction model | 6/10 | 详情 Drawer 有 raw 追溯，但没有运营动作 | v1 至少展示禁用/跳过/待处理状态；若不做操作，明确只读 |
| Data density | 7/10 | 同行页适合密集表格，不需要营销式页面 | 保持紧凑表格，关键词 tag 限高折叠 |
| Accessibility | 5/10 | tag、筛选、Drawer 键盘行为未写 | 任务中补键盘可达、空态文本、筛选控件 label |
| Responsive | 5/10 | 未定义窄屏策略 | Admin 可优先桌面，但表格列折叠策略需明确 |
| Visual consistency | 7/10 | 可沿用现有 Admin 表格模式 | 复用现有筛选区、表格、Drawer 组件 |

#### Design Decisions

- Admin 页面标题和文案应从“励销云原始记录”改为“同行公司池”或等价语义，避免运营误以为看到的是 raw。
- 表格主列建议顺序：公司名、英文名/可反查状态、官网/identity、关键词、raw 数、联系人数、Tendata 反查状态、最近命中。
- 关键词数组过多时应折叠为前 N 个 tag + count，详情中展示完整列表。
- 无英文名 peer 不是错误，应作为“不可进入 Tendata”状态展示。
- 若 backfill 尚未执行，应有 Admin 可见提示或统计，否则页面看起来像数据变少。

### Engineering Review

#### Architecture Graph

```text
Lixiaoyun API item
      │
      ▼
_upsert_lixiaoyun_raw(...)
      │ returns raw_company_id
      ▼
PeerCompanyCleaner
      ├─ derive_identity(website_host > source_id)
      ├─ upsert peer_companies
      ├─ upsert peer_company_keywords
      └─ upsert peer_company_sources
             │
             ├──────────────► Admin peer API ─────► Admin /collection/peers
             │
             └──────────────► Peer lookup selector
                                  │
                                  ▼
                         peer_company_tendata_lookups
                                  │
                                  ▼
                            Tendata buyer lookup
```

#### Critical Engineering Findings

| Severity | Finding | Impact | Required Decision |
| --- | --- | --- | --- |
| Critical | D6 currently says “未被同一逻辑反查过”，但没有 peer 级 lookup ledger | 无法稳定判断同一 peer 是否已查、失败是否重试、是否占用配额 | 推荐新增 `peer_company_tendata_lookups` 或等价状态表 |
| High | 多关键词归因仍是 Open Question | 选主关键词会污染效果统计；按关键词重复查会浪费配额 | 实施前必须决定多归因模型 |
| High | `competitor_companies` 未评估 | 三套“同行/竞品”模型并存会制造概念债 | design 必须写明保留/废弃/不复用原因 |
| High | website host 误合并缺少观测字段 | 集团站、平台页会把不同主体压成一个 peer | 增加 `identity_source`、`identity_confidence`、`merge_reason` 或等价字段 |
| Medium | `_upsert_lixiaoyun_raw` 当前不返回 raw id | `peer_company_sources.raw_company_id` 无法干净写入 | raw upsert SQL 需要 `RETURNING id` |
| Medium | 同步 peer upsert 失败策略未定义 | 一次 peer 写失败可能阻断 raw 采集，或造成 raw/peer 不一致 | 推荐 raw 写入成功优先，peer 错误记录并由 backfill 修复，除非违反约束 |
| Medium | 缺少清洗规则版本 | 未来规则升级无法解释、重算、回滚 | 加 `identity_rule_version` 或 backfill run/version 记录 |

#### Test Diagram

| Flow / Branch | Test Type | Coverage Required |
| --- | --- | --- |
| website normalization | unit | protocol/path/query/case/www/blank/malformed |
| identity priority | unit | website 优先于 source_id；无 website 才 fallback |
| no identity | unit/integration | raw 保留，peer 不创建，skip 统计增加 |
| online raw upsert → peer upsert | integration | 同事务/同 session 下产生 peer、keyword、source |
| duplicate raw by keywords | integration | 一个 peer，多 keyword，多 source |
| existing peer field merge | unit/integration | 非空补空，last_seen 更新，first_seen 保持 |
| backfill dry-run | command test | 输出 raw/peer/source/keyword/skip 统计，不写库 |
| backfill actual rerun | integration | 重复运行幂等 |
| Admin peer API filter | API test | 关键词筛选命中 peer 后返回完整 keywords[] |
| Admin peer UI | frontend test | 一行多 tag，无英文名状态，空态 |
| Tendata peer selection | service test | 同 peer 多关键词只生成一个 lookup input |
| lookup ledger idempotency | integration | 已成功 peer 不重复查，失败按策略重试 |
| attribution persistence | integration | buyer lookup context 或 attribution 表保留 keyword_master_ids[] |

Test plan artifact: `/Users/lay/.gstack/projects/client_get/lay-main-test-plan-20260512-214017.md`

### DX Review

DX scope detected: Admin API、backfill 命令、migration、debug/observability 都会被开发和运维使用。

#### Developer Journey Map

| Stage | Developer Need | Current Risk | Requirement |
| --- | --- | --- | --- |
| Read spec | 明确 peer 与 raw、clean、competitor 边界 | 模型名相近 | design 写清边界和复用决策 |
| Run migration | 知道新增了哪些表/索引 | migration 与 schema.sql 漏同步 | tasks 保留 schema snapshot 更新 |
| Implement online upsert | 拿到 raw row id | 现函数不返回 id | 明确 `RETURNING id` |
| Run backfill dry-run | 先看影响范围 | 输出不够会不敢跑 | dry-run 必须有统计 |
| Run backfill actual | 可重复、可恢复 | 中断后不知状态 | 幂等 + 执行统计 |
| Inspect Admin API | 快速验证去重 | 字段语义不清 | API 类型命名清晰 |
| Debug bad merge | 找 raw 证据 | 只能看到合并结果 | source trace + merge reason |
| Debug Tendata duplicate | 查 peer 是否反查过 | 无状态台账 | lookup ledger |
| Release/rollback | 知道怎么回退 | UI 回退不等于业务回退 | 标记已生成 lookup 和结果归因 |

#### DX Scorecard

| Dimension | Score | Recommendation |
| --- | ---: | --- |
| Getting started | 6/10 | backfill 命令需 copy-paste 示例 |
| API naming | 7/10 | peer API 与 raw API 命名要明显区分 |
| Error messages | 5/10 | backfill/peer upsert 错误需包含 raw id、source_id、identity |
| Docs findability | 6/10 | design 和 tasks 已在 change 内，需补运行命令 |
| Upgrade path | 5/10 | 需标明 migration、backfill、Admin 切换、Tendata 切换顺序 |
| Dev env friction | 6/10 | 需要本地测试数据或 dry-run 输出 |
| Debuggability | 5/10 | lookup ledger 与 merge reason 是关键 |
| Operability | 5/10 | 需要上线指标和回滚语义 |

TTHW assessment: 当前从零验证约 30-45 分钟；目标是 10-15 分钟内完成 migration + dry-run + 一条样例 peer 验证。

### Error And Rescue Registry

| Error / Bad State | Detection | Rescue |
| --- | --- | --- |
| peer upsert 失败但 raw 已写入 | error log + skip/backfill diff | backfill 重跑修复，失败 raw id 可定位 |
| website host 误合并 | 同 peer 多个信用代码/法人/中文名冲突 | 标记 low confidence，后续支持拆分/override |
| source_id 不稳定 | 同 source_id 对应多个明显不同主体 | 降低 source_id fallback 信任，保留 raw 不合并 |
| Tendata 重复反查 | lookup ledger 同 peer 多条 success | 唯一约束阻止，异常数据用 ledger 修复 |
| 多关键词归因丢失 | buyer result 只能查到主关键词 | attribution 表或 context 保留 keyword_master_ids[] |
| backfill 未执行 | peer count 明显小于 raw identity count | Admin 指标提示，运行 backfill |
| 英文名缺失导致无查询 | 可反查 peer 数低 | Admin 展示缺英文名数，后续补英文名/别名 |

### Failure Modes Registry

| Failure Mode | Severity | Plan Coverage | Action |
| --- | --- | --- | --- |
| 重复公司仍重复进入 Tendata | Critical | 部分覆盖 | 增加 peer lookup ledger |
| 多关键词归因被主关键词吞掉 | High | 未锁定 | 实施前决策 |
| 三套同行模型概念冲突 | High | 未覆盖 | 补 `competitor_companies` 边界 |
| 官网域名误合并 | High | 仅风险说明 | 加身份置信度/冲突观测 |
| raw id 缺失导致 source trace 不完整 | Medium | 未覆盖 | raw upsert 返回 id |
| backfill 统计不可解释 | Medium | 部分覆盖 | dry-run 输出固定字段 |
| Admin UI 看不到业务状态 | Medium | 部分覆盖 | 增加 Tendata readiness/status 字段 |

### Cross-Phase Themes

- Tendata peer 级 lookup ledger 被 CEO、Eng、DX 三个阶段共同指出，是高置信度缺口。
- 多关键词归因不能继续作为 open question。它影响业务解释、统计和去重策略。
- Admin peer 页应该从“去重列表”升级为“stage 2 输入池控制台”，至少展示 readiness/status/metrics。
- identity 规则要可解释、可观测、可回滚；website host 优先可以做，但不能黑箱合并。

### NOT In Scope After Review

- 不在本 change 做模糊公司名匹配。
- 不在本 change 做完整人工 merge/split 后台，但需要留下身份置信度和后续 override 入口的模型余地。
- 不把励销云同行公司写入 `clean_companies`。
- 不把同行公司直接开放给租户。
- 不重做励销云 stage 1 采集分页/限额/续采规则。

### User Challenges

#### Challenge 1: v1 是否只做 peer 去重表，还是纳入 peer Tendata lookup ledger

- 用户原始方向：清洗同行公司，Admin 合并展示，Tendata 按公司去重只查一次。
- 两个模型建议：把 peer 级 Tendata lookup ledger 纳入 v1 或至少纳入本 change 的明确任务。
- 理由：没有 ledger，就无法回答“这个 peer 是否查过、何时查过、成功还是失败、是否要重试、占了多少配额、产生多少买家”。
- 我们可能缺的上下文：如果现有 collection task 已经天然持久化了等价状态，可以不新增表，但必须在 design 中指明等价机制。
- 如果模型判断错了，代价是 v1 范围扩大，多一张状态表/服务测试。

推荐：接受挑战，新增 `peer_company_tendata_lookups` 或明确复用等价任务状态。

#### Challenge 2: 多关键词归因是否允许第一版只选主关键词

- 用户原始方向：同一家公司多个关键词命中时，关键词数组表达；Tendata 按公司只采一次。
- 两个模型建议：不应只选主关键词后把其他关键词留作缺口；至少要在 buyer lookup context 或归因关系表保留完整 `keyword_master_ids[]`。
- 理由：关键词效果、租户解释、线索来源都会受影响；重复反查不是解决归因的正确方式。
- 我们可能缺的上下文：如果当前业务暂不使用 Tendata 结果按关键词统计，主关键词短期也可跑通。
- 如果模型判断错了，代价是多做一层归因记录。

推荐：接受挑战，v1 保留完整 keyword set；是否扩展 Tendata raw 表可由实现时选择最小方案。

#### Challenge 3: 是否需要评估 `competitor_companies`

- 用户原始方向：新增 peer clean 层。
- 两个模型建议：实施前必须说明为什么不复用或迁移既有 `competitor_companies`。
- 理由：否则系统会同时有 raw competitors、tenant competitor companies、peer companies 三个相近概念。
- 我们可能缺的上下文：`competitor_companies` 可能已是遗留或未使用表。
- 如果模型判断错了，代价是多写一个保留/不复用说明。

推荐：接受挑战，补一个明确决策，不阻断新增 peer 层。

### Auto-Decided Recommendations

| # | Phase | Decision | Classification | Principle | Rationale | Rejected |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | CEO | 保留 D-008，不复用 `clean_companies` | Mechanical | P4 | 复用会污染海外客户库 | 写入 clean_companies |
| 2 | CEO | 主路径继续同步清洗，不做 5 分钟轮询 | Mechanical | P5 | 同步最简单，Admin 与 worker 一致性最好 | 轮询 worker |
| 3 | CEO | 增加业务指标：raw 数、peer 数、去重率、英文名覆盖率、lookup 节省、Tendata 命中 | Mechanical | P1 | 没指标无法判断收益 | 只做功能验收 |
| 4 | Design | Admin 首屏突出 Tendata readiness/status | Taste | P1 | 这页应服务 stage 2 运营，不只是看表 | 只展示公司基础信息 |
| 5 | Eng | `_upsert_lixiaoyun_raw` 必须返回 raw id | Mechanical | P5 | source trace 需要稳定 raw id | 二次查询猜 raw id |
| 6 | Eng | 增加 identity metadata 或等价字段 | Taste | P1 | website/source_id 合并风险需要可解释 | 只存 identity value |
| 7 | DX | backfill dry-run 必须输出固定统计 | Mechanical | P5 | 运维需要敢跑、能复核 | 只打印成功/失败 |
| 8 | DX | release 顺序必须写入任务：migration → dry-run → backfill → Admin/Tendata 验证 | Mechanical | P1 | 降低上线和回滚不确定性 | 临场手动判断 |

### Final Recommendation

推荐在进入实现前先更新 `proposal.md`、`tasks.md`、`spec.md`，把以下内容从“实现时再确认”提升为实施门禁：

1. peer 级 Tendata lookup ledger 或等价状态模型。
2. 完整多关键词归因，不因按公司去重而丢失 keyword set。
3. `competitor_companies` 与新 peer 层的边界。
4. identity 置信度/来源/规则版本/冲突观测。
5. Admin 页面展示 Tendata readiness/status 和关键运营指标。
6. raw upsert 返回 `raw_company_id`。
7. backfill dry-run/actual 的固定统计与幂等验收。
