## Context

上一轮修复已覆盖 `tendata_raw_companies.raw_payload.contacts → clean_contacts`，但线上只读统计显示腾道联系人主路径并不在 `raw_payload.contacts`。

线上证据：

- `tendata_raw_companies` 共 8338 条。
- `contacts_count > 0` 共 1926 条。
- `tendata_raw_companies.raw_payload.contacts` 为 0 个公司、0 条联系人。
- `tendata_raw_contacts` 共 300453 条联系人，其中 109471 条有 email。
- `tendata_raw_contacts` 覆盖 1924 个 raw company。
- `clean_company_sources` 已能把 1661 个有 raw contacts 的 raw company 关联到 clean company。
- visible tenant 中 `contacts_count > 0` 的公司有 1856 个，当前无 `clean_contacts` 的也有 1856 个；其中 1656 个可从 `tendata_raw_contacts` 回填，约 103389 条 email 联系人。

因此，正确修复不是重新采集优先，也不是读取 `raw_payload.contacts`，而是补齐 `tendata_raw_contacts → clean_contacts` 这条线上主链路。

## Goals / Non-Goals

**Goals:**

- 新 cleanup 处理腾道 raw company 时，自动把 `tendata_raw_contacts` 中有 email 的联系人写入 `clean_contacts`。
- 提供一次性 backfill，把历史已存在的 `tendata_raw_contacts` 回填到 `clean_contacts`。
- 回填后 tenant 公司联系人详情 API 可展示姓名、职位、邮箱、电话。
- backfill 可重复运行，不产生重复联系人。

**Non-Goals:**

- 不修改数据库 schema。
- 不改 tenant 前端或 admin raw 页面。
- 不重新采集腾道联系人。
- 不为没有 email 的联系人创建 `clean_contacts`，因为当前幂等键依赖同公司 email。
- 不自动创建 `tenant_contacts` 私有状态；tenant 联系人 API 通过 `LEFT JOIN tenant_contacts` 已能展示 clean 联系人。

## Decisions

### 1. `clean_company_sources` 是 raw 到 clean 的关联权威

历史回填从 `clean_company_sources` 出发：

```sql
clean_company_sources.source_type = 'tendata'
clean_company_sources.source_company_id = tendata_raw_contacts.raw_company_id
```

这样避免用公司名模糊匹配，也避免把同名、同国家以外的历史联系人误挂到错误 clean company。

### 2. 只回填有 email 的联系人

`clean_contacts` 当前唯一约束是 `(clean_company_id, email) WHERE email IS NOT NULL`。为保证 backfill 幂等且不重复插入，只写入 `email IS NOT NULL` 的 raw contacts。没有 email 的 raw contacts 保留在 `tendata_raw_contacts`，不进入 tenant 展示。

### 3. cleanup 与 backfill 使用同一映射和写入语义

cleanup 和 backfill 都应执行同一类 upsert：

- `clean_company_id` 来自 `clean_company_sources`
- `name` 来自 `tendata_raw_contacts.name`
- `position` 来自 `tendata_raw_contacts.position`
- `email` 来自 `tendata_raw_contacts.email`
- `phone` 来自 `tendata_raw_contacts.phone`
- conflict 时补齐空字段并更新 `updated_at`

cleanup 顺序必须固定为：

1. upsert `clean_companies`
2. upsert `clean_company_sources`
3. 通过 `clean_company_sources(source_type='tendata', source_company_id=<raw_company_id>)` 读取 `clean_company_id`
4. materialize `tendata_raw_contacts` 到 `clean_contacts`
5. materialize / update `tenant_companies`

这样 cleanup 和 backfill 都以 `clean_company_sources` 为 raw 到 clean 的唯一映射权威，避免 cleanup 用临时 `clean_id` 直写、backfill 用 source mapping 写入，导致两条路径语义分叉。

### 4. backfill upsert 前必须按 clean company + email 去重

线上 `tendata_raw_contacts` 约 30 万行，可能出现同一 clean company 下同一 email 多条 raw contact。backfill 的写入输入必须先去重，再执行 `INSERT ... ON CONFLICT`，否则 PostgreSQL 可能因同一条语句内多次命中同一 conflict key 而失败。

去重规则固定为：

- 分组键：`clean_company_id, lower(email)`
- 仅保留 `email IS NOT NULL` 的联系人
- 优先保留信息更完整的联系人：`name`、`position`、`phone` 非空字段更多者优先
- 完整度相同则取较新的 raw contact；仍相同则取 id 更大的 raw contact

建议实现使用 `row_number() over (partition by clean_company_id, lower(email) order by completeness desc, created_at desc nulls last, id desc)` 或等价 `DISTINCT ON`。

### 5. backfill 先本地/只读统计，再生产执行

实施时先提供 dry-run/统计查询，输出：

- 可回填 clean company 数
- 可回填联系人行数
- 去重前候选联系人行数
- 去重后将 upsert 的联系人行数
- 已有 clean contacts 数
- 执行后插入/更新行数

正式生产 backfill 属于外部副作用，必须由用户明确触发。

## Risks / Trade-offs

- 联系人量较大，线上约 10 万条 email 联系人可回填；backfill 应使用单条 SQL 或批处理，避免 Python 逐行慢写。
- 同一 clean company 可能关联多个 tendata raw company，同 email 可能重复；写入前必须按 `clean_company_id + lower(email)` 去重，再以 `clean_company_id + email` 幂等 upsert。
- 回填会让 tenant 详情突然显示大量历史联系人；这是预期修复，不创建租户私有发送状态。

## Migration Plan

无需 Alembic schema 迁移。

发布后：

1. 新 cleanup worker 处理后续 tendata raw company 时自动写入 `clean_contacts`。
2. 用户明确触发后，运行历史 backfill。
3. 运行只读验收 SQL，确认 visible tenant 的 `contacts_count > 0` 且 `clean_contacts = 0` 的可回填缺口下降。

## Open Questions

无阻塞决策。执行生产 backfill 前需要用户单独确认触发，因为它会写生产数据库。
