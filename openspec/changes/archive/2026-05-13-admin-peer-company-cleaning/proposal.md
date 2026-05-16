## Why

Admin 现有同行公司页当前直接展示 `lixiaoyun_raw_companies`，同一家公司被多个关键词采到时会出现多行。运营仍需要保留原 raw 视图，同时也需要一个独立的“同行公司（清洗）”页查看去重后的同行公司池。后续 Tendata stage 2 会从这个去重池取输入，但 Tendata 反查链路不在本 change 实施。

## What Changes

- 新增平台内部“同行公司清洗层”，把励销云 raw 同行公司清洗为一家公司一行的同行实体。
- 同行公司去重主键优先级：
  - 有官网/网址时，使用规范化后的 website host 作为去重主键。
  - 无官网/网址时，使用励销云 API 返回的 `source_id` 作为去重主键。
- 同一同行公司被多个平台关键词采到时，保留多关键词命中关系，并在新增的 Admin “同行公司（清洗）”页以关键词数组展示。
- 新增 Admin “同行公司（清洗）”页，使用 Next.js 实现去重同行公司视图；原 Admin 同行公司页保持不变。
- 新增清洗页的列表默认字段和筛选条件与现有同行公司页保持一致，详情页仅展示是否有英文名、raw 数、关键词数。
- 本 change 只为后续 Tendata stage 2 提供去重后的同行公司池，不改 Tendata 反查执行链路、不新增 peer 级 Tendata lookup ledger、不迁移 `tendata_raw_companies.keyword_master_id` 为数组。
- 同行身份清洗需要保留 identity 来源/置信度/规则版本或等价诊断信息，便于排查 website host/source_id 误合并。
- 励销云 raw 入库时同步 upsert 同行清洗层；历史 raw 数据通过一次性 backfill 重建同行清洗层。
- 本次 Admin 同行公司控制台前端使用 Next.js 实现，作为后续 Admin 迁移到 Next.js 全栈的试点；现有 Vite Admin 可保留入口或跳转。
- 保留 raw 层作为证据，不删除、不覆盖励销云原始采集记录。

## Non-Goals

- 不把励销云同行公司写入海外客户 `clean_companies`。
- 不让租户直接看到励销云同行公司。
- 不改变 Tendata raw → clean customer 的清洗规则。
- 不改变 Tendata stage 2 buyer lookup 输入构造、执行、重试或去重逻辑。
- 不新增 peer 级 Tendata lookup ledger。
- 不在本 change 修改 `tendata_raw_companies.keyword_master_id`，也不新增 `keyword_master_ids[]`。
- 不替换或删除原 Admin 同行公司页。
- 不新增 5 分钟 peer 清洗轮询 worker；同行清洗主路径随励销云 raw 写入同步完成。
- 不引入模糊匹配、人工合并后台、同义词合并或复杂公司主体识别。
- 不改变励销云 stage 1 的跨天续采、每日上限和 cursor 规则。

## Capabilities

### New Capabilities

- `admin-peer-company-cleaning`: 平台 SHALL 将励销云 raw 同行公司清洗为去重后的同行公司池，并新增 Admin “同行公司（清洗）”页展示去重实体与关键词数组；原 Admin 同行公司页 SHALL 保持不变。

### Modified Capabilities

- 无。

## Impact

| 模块 | 影响 |
| --- | --- |
| 数据库 | 新增同行公司清洗层相关表，至少包含同行实体、关键词命中关系、raw source 追溯关系；新增 website host/source_id 去重索引。 |
| 后端采集服务 | `lixiaoyun_raw_companies` upsert 成功后，同事务 upsert 同行清洗层；保留 raw 表当前唯一约束。 |
| 后端 Admin API | 新增清洗页所需的 peer list/detail API，返回去重同行实体、关键词数组、source/raw 统计等字段；原 raw 同行公司 API 保持兼容。 |
| 后端 Tendata stage 2 | 不在本 change 改动；后续 change 再切换为从 peer pool 取输入并处理归因。 |
| 后端 Tendata 状态/归因 | 不在本 change 新增 lookup ledger，不改 `tendata_raw_companies.keyword_master_id`。 |
| 前端 Admin | 新增 Next.js “同行公司（清洗）”页；原同行公司页不变。新页面列表默认字段和筛选条件与现有同行公司页保持一致，详情页仅补充是否有英文名、raw 数、关键词数；新增独立 `clientget-admin-next` 镜像用于部署 Next.js 试点页。 |
| 数据迁移/回填 | 新增 Alembic migration；提供历史 `lixiaoyun_raw_companies` backfill，按相同规则重建 peer 层。 |
| 测试 | 覆盖 website host 去重、source_id fallback、多关键词数组、backfill 幂等、Next.js 清洗页字段展示。 |

## Traceability

- 决策追溯：D-008=B（励销云不进入海外客户 `clean_companies`）、D-035（V3 仅开放 lixiaoyun + tendata 反推链路）。
- 能力域：C2 KeywordMaster / 反推采集闭环；业务目标 R-2（励销云 stage 1 中国同行 + 腾道 stage 2 海外买家反查）。
