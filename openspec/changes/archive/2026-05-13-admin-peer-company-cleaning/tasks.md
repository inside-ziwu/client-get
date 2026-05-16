## 1. 数据库与迁移

- [x] 1.1 新增 Alembic migration（建议文件名 `20260512_0040_peer_company_cleaning.py`）：创建 `peer_companies`、`peer_company_keywords`、`peer_company_sources`。
- [x] 1.2 在 `peer_companies` 增加 `identity_type`、`identity_value`、中文名、英文名、domain/website_host、工商展示字段、联系人数量、`first_seen_at`、`last_seen_at`、时间戳字段。
- [x] 1.3 为 `peer_companies` 增加 `UNIQUE (identity_type, identity_value)`，并为 `website_host`、`source_id`/identity、`english_name`、`last_seen_at` 建必要索引。
- [x] 1.4 为 `peer_company_keywords` 增加 `peer_company_id`、`keyword_master_id`、`created_at`，并增加 `UNIQUE (peer_company_id, keyword_master_id)`。
- [x] 1.5 为 `peer_company_sources` 增加 `peer_company_id`、`raw_company_id`、`source_id`、`created_at`，并增加 `UNIQUE (raw_company_id)` 或等价幂等约束。
- [x] 1.6 为 peer identity 增加可解释元数据字段或等价记录：`identity_source`/`identity_confidence`/`merge_reason`/`identity_rule_version`，用于排查 website host 或 source_id 误合并。
- [x] 1.7 为聚合查询补必要索引：`peer_company_keywords(keyword_master_id, peer_company_id)`、`peer_company_sources(peer_company_id)`、`peer_company_sources(raw_company_id)`、`lixiaoyun_raw_contacts(raw_company_id)` 已有索引需确认可复用。
- [x] 1.8 明确评估既有 `competitor_companies`：在设计或代码注释中说明其与新 `peer_companies` 的边界、是否遗留、是否不复用，以及不复用原因。
- [x] 1.9 更新 `backend/03_database/schema.sql` 中的目标 schema 快照，保持与 Alembic migration 一致。

## 2. 后端同行清洗服务

- [x] 2.1 新增或扩展 service 方法：从 Lixiaoyun raw 字段派生 peer identity，优先规范化 website host，其次使用 `source_id`。
- [x] 2.2 实现 website host 规范化：去协议、路径、query、hash、尾斜杠，转小写，去常见 `www.` 前缀；无法得到 host 时返回空。
- [x] 2.3 实现 peer company upsert：按 `identity_type + identity_value` 幂等创建/更新同行实体，字段合并采用非空补空与 `last_seen_at` 更新。
- [x] 2.4 实现 peer keyword upsert：同一 peer company 可关联多个 `keyword_master_id`，重复处理不产生重复关系。
- [x] 2.5 实现 peer source upsert：保留 raw company id 到 peer company 的追溯关系，重复处理不产生重复 source 行。
- [x] 2.6 调整 `_upsert_lixiaoyun_raw` 或等价 SQL，使 raw upsert 成功后能返回 `raw_company_id`（例如 `RETURNING id`），供 `peer_company_sources` 使用。
- [x] 2.7 将 `_upsert_lixiaoyun_raw` 写入成功后的 raw 行结果接入 peer upsert，同事务更新 peer 层。
- [x] 2.8 在线写入采用 raw + peer 同事务强一致：peer upsert 或关系表写入失败时，raw 写入也失败，并由 collection task 现有重试机制重跑；不得吞掉 peer 错误后只依赖 backfill 修复在线数据。
- [x] 2.9 v1 不做在线 identity re-parent / merge：raw source 首次关联 peer 后，后补官网只补字段和诊断，不自动改变 peer identity。
- [x] 2.10 保持 D-008 边界：不得把 Lixiaoyun raw 写入海外客户 `clean_companies`。

## 3. 历史数据 Backfill

- [x] 3.1 新增 backfill service 或脚本（建议 `backend/scripts/backfill_lixiaoyun_peer_companies.py`），支持 dry-run 和实际执行。
- [x] 3.2 dry-run 输出候选 raw 行数、可生成 peer 数、source 关系数、keyword 关系数、缺 identity 跳过数、website/source_id identity 分布、低置信/冲突候选数。
- [x] 3.3 实际执行按与在线写入相同的 identity 与 upsert 规则扫描历史 `lixiaoyun_raw_companies`，按主键分页或分批处理，避免一次性加载全表。
- [x] 3.4 backfill 支持重复运行且结果幂等。
- [x] 3.5 backfill 实跑输出固定统计，至少包含 raw 总数、peer 总数、去重率、英文名覆盖率、跳过数和冲突候选数。

## 4. Admin API 与前端“同行公司（清洗）”页

- [x] 4.1 新增 Admin peer cleaning list/detail API，使其以 peer 层为真源返回一行一个同行公司；原同行公司页/API 保持不变。
- [x] 4.2 API 响应包含 `id`、`name`、`english_name`、`domain`/`website_host`、`keywords[]`、`raw_count`、`source_ids` 或 source 统计、工商展示字段、peer 级去重联系人数量、`first_seen_at`、`last_seen_at`。
- [x] 4.3 API 支持现有同行页查询意图：公司名/英文名/官网、关键词、成立时间、注册资本、员工规模、联系人数量、有英文名、有域名；联系人数量筛选按 peer 级去重联系人数量执行。
- [x] 4.4 API 增加详情页所需聚合字段：`has_english_name`、`raw_count`、`keyword_count`。
- [x] 4.5 API 可保留后端 debug 所需 identity 元数据：identity 类型、identity value、置信度/来源/规则版本、raw 冲突候选统计；默认列表不展示。
- [x] 4.6 API 不为本轮 Admin 页面新增 lookup 状态、失败原因、最近命中时间、buyer_count / Tendata 结果数、是否已反查等展示字段。
- [x] 4.7 Admin peer cleaning list API 聚合 keywords、raw_count、source_ids、contact_count 时必须在 SQL 层批量聚合，避免每个 peer 单独查询 keywords/sources/contacts 的 N+1。
- [x] 4.8 更新 `frontend/packages/shared-api` 中 Admin collection 类型与请求方法，匹配新的 peer API 响应。
- [x] 4.9 在 `frontend/apps/admin-next` 使用 Next.js 新增 Admin “同行公司（清洗）”页（建议路由 `/collection/peers-cleaned`）；`nextjs-spike/` 仅作参考，不作为生产 app；现有 Vite Admin 保留原同行公司页，并提供到新清洗页的入口、跳转或兼容壳。
- [x] 4.10 新增 `clientget-admin-next` 构建与推送路径：Next.js 使用 `output: 'standalone'`，独立镜像运行 Node server；现有 `clientget-admin` Vite/nginx 镜像不承载 Next.js 页面。
- [x] 4.11 `frontend/apps/admin-next/next.config.*` 明确配置 `transpilePackages`，至少覆盖 `@shared/api`、`@shared/types`，如页面直接使用 hooks/ui 则同时覆盖 `@shared/hooks`、`@shared/ui`。
- [x] 4.12 记录 Sealos 入口/应用配置要求，使管理员能从现有 Vite Admin 入口访问 admin-next `/collection/peers-cleaned`。
- [x] 4.12a 支持独立 admin-next 公网域名的登录态承接：Vite Admin 入口通过 URL hash 一次性传递 session token，admin-next 读取后写入本域 sessionStorage 并清理 hash；不得使用 query string 传 token。
- [x] 4.12b admin-next 独立域名页面保留 Admin 左侧菜单壳，当前“同行公司（清洗）”高亮，点击其他菜单回跳到现有 Vite Admin 公网入口。
- [x] 4.13 Next.js 列表默认字段与现有同行公司页保持一致；筛选条件也与现有同行公司页保持一致。
- [x] 4.14 Next.js 控制台展示 `keywords[]` 多 tag；关键词过多时折叠显示并在详情展示完整列表；无关键词时展示空态。
- [x] 4.15 Admin 同行公司详情 Drawer 或详情面板展示合并后的同行字段、关键词数组、raw/source 统计，并额外展示是否有英文名、raw 数、关键词数。
- [x] 4.16 保留或补充 raw debug/detail 入口，使运营可从 peer 公司追溯 raw 证据。
- [x] 4.17 Admin 页面或 backfill 输出提供数据健康统计，至少能看到 raw 数、peer 数、去重率、英文名覆盖率。
- [x] 4.18 Admin 页面移除/不展示 lookup 状态、失败原因、最近命中时间、buyer_count / Tendata 结果数、是否已反查字段。

## 5. 后端测试

- [x] 5.1 添加 `backend/tests/test_peer_company_cleaning.py`：website host 规范化单元测试，覆盖协议、路径、query、大小写、`www.` 等价输入归一到同一 host，以及空/异常网址 fallback。
- [x] 5.2 添加 peer upsert 测试：同 website host 多 raw 行合并为一个 peer company。
- [x] 5.3 添加 fallback 测试：无 website 但有 `source_id` 时按 `source_id` 去重。
- [x] 5.4 添加边界测试：无 website 且无 `source_id` 时不创建 peer company。
- [x] 5.5 添加多关键词测试：同一 peer company 关联多个 `keyword_master_id`，重复处理幂等。
- [x] 5.6 添加 online 强一致测试：peer upsert 抛错时 `_upsert_lixiaoyun_raw` 所在事务回滚，raw 行不应留下半成功数据。
- [x] 5.7 添加 backfill dry-run 与实际执行幂等测试。
- [x] 5.8 添加 Admin peer cleaning API 测试：返回去重 peer、`keywords[]`、分页 total 与筛选结果。
- [x] 5.9 添加 Admin peer cleaning API 空结果测试：无匹配时返回空 data 和 total=0。
- [x] 5.10 添加 peer 联系人数量聚合测试：同一 peer 多 raw contacts 按 email 优先、source_contact_id 次之、raw contact id 兜底去重计数，联系人数量筛选命中聚合值。
- [x] 5.11 添加 raw upsert 返回 id 与 source trace 测试：online upsert 后 `peer_company_sources.raw_company_id` 指向正确 raw 行。
- [x] 5.12 添加 identity 元数据/冲突候选测试：同一 website host 下出现不同工商身份时能被统计或标记。
- [x] 5.13 添加后补官网不 re-parent 测试：同一 raw 首次按 source_id 建 peer 后，后续补官网只补展示字段，不改变已关联 peer identity。
- [x] 5.14 添加原同行公司页/API 不变的回归测试或接口契约检查。
- [x] 5.15 添加 Alembic/schema 快照测试：migration 创建的 peer 表、唯一约束、索引与 `backend/03_database/schema.sql` 一致。

## 6. Next.js 前端测试与验收

- [x] 6.1 新增 `frontend/apps/admin-next/test/peer-cleaning-page-contract.test.mjs` 或等价源码约束测试，覆盖页面查询使用 peer cleaning API 而不是 raw API。
- [x] 6.2 覆盖关键词数组展示：多关键词 peer 只渲染一行并显示多个 tag。
- [x] 6.3 覆盖筛选交互：关键词筛选命中 peer 后仍显示完整关键词数组。
- [x] 6.4 覆盖详情页新增字段展示：是否有英文名、raw 数、关键词数。
- [x] 6.5 添加字段禁止展示测试：页面源码不得渲染 lookup 状态、失败原因、最近命中时间、buyer_count / Tendata 结果数、是否已反查。
- [x] 6.6 添加 `frontend/apps/admin-next` 构建契约测试或源码约束：`next.config.*` 包含 `output: 'standalone'` 和必要 `transpilePackages`。
- [x] 6.7 添加 Vite Admin 入口回归测试：原 `/collection/peers` 路由仍指向原 PeersData 页，并存在进入 Next.js 清洗页的入口或跳转。
- [x] 6.7a 添加独立域名登录态承接契约测试：Vite Admin 入口生成 `#token=` hash，admin-next 消费 hash 后清理地址栏并从 sessionStorage 发起 API 请求。
- [x] 6.7b 添加 admin-next 导航壳契约测试：页面包含“同行公司（清洗）”左侧菜单高亮与回跳 Vite Admin 的菜单导航。
- [x] 6.8 手工验收新增“同行公司（清洗）”页：同一官网被多个关键词采到时只显示一行。
- [x] 6.9 手工验收数据健康统计：raw 数、peer 数、去重率、英文名覆盖率符合 backfill dry-run/实跑统计。
- [x] 6.10 手工验收列表默认字段和筛选条件与现有同行公司页一致，且不展示 lookup 状态、失败原因、最近命中时间、buyer_count / Tendata 结果数、是否已反查。
- [x] 6.11 手工验收 API 500 / 空结果 / 慢加载时的 loading、error、empty 状态，用户不会看到空白页面。

## 7. 运行验证与收尾

- [x] 7.1 运行后端相关测试，至少覆盖 peer cleaning、Admin peer cleaning API、backfill。
- [x] 7.2 运行 `frontend/apps/admin-next` 清洗页相关测试、type-check/build；必要时运行现有 Vite Admin 入口兼容测试。
- [x] 7.3 运行 Alembic migration 升级验证，并确认 downgrade/rollback 语义可接受。
- [x] 7.4 运行 backfill dry-run，记录候选和跳过统计。
- [x] 7.5 在本地或测试数据上执行 backfill 实跑，确认 peer 表、keyword 关系、source 关系数量符合预期。
- [x] 7.6 本地构建验证 `clientget-admin-next` 镜像或等价 standalone 产物，并确认运行时能访问后端 API。
- [x] 7.7 验证 release 顺序：migration → backfill dry-run → backfill 实跑 → 发布 `clientget-admin-next` → 打开 Vite Admin 入口 → 验证新增“同行公司（清洗）”页。
- [x] 7.8 验证 rollback 语义：可隐藏 Next.js 清洗页入口并停止/回滚 `clientget-admin-next`；原同行公司页、raw API、Tendata 旧链路不受影响。
- [x] 7.9 完成当前 change 的 OpenSpec 验证，并在最终汇报前调用 `verification-before-completion` skill。

## 8. 线上回归修复：Admin collection API schema 兼容

- [x] 8.1 修复原 Admin raw 列表 API，使 `waimaotong_raw_companies`、`tendata_raw_companies`、`lixiaoyun_raw_companies` 查询兼容 0035 之后的 raw schema，不再引用已删除的 `task_id` / `tid` 列。
- [x] 8.2 修复原 Admin clean company 列表与 cleanup health 查询，使其兼容 0034/0036 之后的 `clean_companies` schema，不再引用已删除的 `name_en` / `domain` / `sources` 列。
- [x] 8.3 添加后端回归测试，覆盖旧 Admin Tendata raw、客户数据列表和 cleanup health 的 SQL 不引用迁移后不存在的列。
- [x] 8.4 运行后端相关测试与 OpenSpec 严格校验，并重新构建推送 backend 镜像供线上更新。

## 9. 线上回归修复：原 Admin 同行公司页字段展示

- [x] 9.1 修复原 Admin “同行公司”页的 Lixiaoyun raw API 响应，使迁移后存储在顶层列的 `english_name`、`esdate`、`legalperson`、`uncid`、`reg_capital`、`employee_scale`、`reg_address` 能以旧页面期望的 `raw_payload` key 继续展示。
- [x] 9.2 修复原 Admin “同行公司”页中文名 fallback：当 `raw_payload` 没有 `name_cn/name_zh` 时，应展示 `row.name`，不能展示 `—`。
- [x] 9.3 添加前后端回归测试，覆盖原 `/collection/peers` 仍使用 Lixiaoyun raw 视图，并能从 API 响应展示结构化同行字段。
- [x] 9.4 运行相关验证，并按实际改动重新构建推送 backend/admin 镜像供线上更新。
