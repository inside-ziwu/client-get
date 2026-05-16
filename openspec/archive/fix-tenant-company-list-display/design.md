## Context

tenant 公司列表由 `backend/app/services/tenant_query_service.py` 从 `clean_companies`、`clean_contacts` 与租户私有状态组合返回，前端页面 `frontend/apps/tenant/src/pages/Companies/index.tsx` 负责列表列、详情 Drawer 和联系人明细表展示。用户反馈联系人信息与预期不一致。

当前实现中，联系人字段横跨三层：

- 后端列表：`contacts_count`
- 后端详情：`contacts_count`、`tenant_state`
- 后端联系人明细：`clean_contacts.name`、`position`、`email`、`phone` 和 `tenant_contact_state`
- 前端列表/详情：`Company` 类型、列配置、`normalizeContact`、Drawer 展示

重新排查后确认，展示层字段映射已修，但本地数据仍存在 `clean_companies.contacts_count > 0` 且 `clean_contacts` 无明细的样本。断点在腾道采集/清洗链路：provider 顶层返回 `contacts`，`CollectionService._upsert_tendata_raw()` 只写 `contacts_count` 和原始 `raw_payload`，没有把顶层 `contacts` 保存在 raw company；`CleanupService` 也没有从 raw 中清洗联系人明细到 `clean_contacts`。因此本 change 扩展为同时修复“已采到的联系人明细可被 tenant 展示”的最小数据链路，不做 schema 或 admin 能力改造。

## Goals / Non-Goals

**Goals:**

- tenant 公司列表的联系人数量必须使用当前 clean company 联系人数。
- tenant 公司详情 Drawer 的联系人明细必须使用当前联系人字段，姓名、职位、邮箱、电话和租户联系人状态不得错位。
- 腾道 provider 已返回联系人明细时，raw 入库必须保留这些明细，清洗必须写入 `clean_contacts`，tenant 侧联系人明细接口可直接展示。
- 用测试和手工对照覆盖 admin 有联系人数据但 tenant 不正确展示的回归路径。

**Non-Goals:**

- 不修改联系人分类或评分 worker。
- 不改变 `tenant_companies` / `clean_companies` / `clean_contacts` schema。
- 不实现联系人编辑、主联系人规则、联系人可发送性重算或群组功能。
- 不为历史已经丢失联系人明细的 raw 记录伪造联系人；只有 raw 中实际存在联系人数组时才落 `clean_contacts`。

## Decisions

### 1. 以 V3 clean contact 字段作为 tenant 展示事实源

联系人数量和联系人明细都应从当前 clean 数据读取：联系人数量来自 `clean_companies.contacts_count`，联系人明细来自 `clean_contacts`，租户私有状态只叠加 `tenant_companies` / `tenant_contacts`。这样与现有 V3 契约一致，也避免 tenant 页面读取旧 prospect 字段。

备选方案是前端自行 fallback 到旧字段如 `contact_name`、`contact_title`、`full_name`。该方案会掩盖 API 契约漂移，且容易让 admin 与 tenant 展示继续分叉，因此不采用。

### 2. 先用契约测试锁定字段，再改实现

实施时先补后端服务/API 测试，明确 `/tenant/companies` 与 `/tenant/companies/{id}/contacts` 的返回结构必须包含可展示的联系人数量和联系人明细字段。随后修前端类型与渲染，避免只修 UI 但后端返回仍不稳定。

验收时必须选取同一 `clean_company_id` 做 admin 与 tenant 对照：admin 侧能看到的联系人事实，tenant 侧列表、详情和联系人明细也必须展示同源字段。

### 3. 前端只做字段展示适配

前端应直接读取 `contacts_count`、联系人 `name`、`position`、`email`、`phone`。联系人明细表展示姓名、职位、邮箱和电话四列。`normalizeContact` 仅用于兼容同一 API 的字段命名，不再优先使用旧 prospect/contact 别名覆盖当前 V3 字段。

### 4. 空态要区分“无数据”与“字段读错”

联系人数量为 `0` 时必须显示 `0`，不能被 `value || '—'` 误判为空。联系人明细为空时展示空态；如果 `contacts_count > 0` 但明细接口为空，验收时应记录为数据一致性问题，不在前端静默伪造联系人。

### 5. 腾道联系人明细必须随 raw company 保留并清洗

`TendataCollectionProvider._build_company()` 已产出顶层 `contacts`。`CollectionService._upsert_tendata_raw()` 必须把该顶层字段合并进 `tendata_raw_companies.raw_payload.contacts`，避免后续 cleanup 只能看到数量。`CleanupService._clean_and_link()` 在 upsert clean company/source 后，从 raw 顶层或 `raw_payload.contacts` 读取联系人数组，按 `clean_company_id + email` 幂等 upsert 到 `clean_contacts`。

只接收有 email 的联系人：当前 `clean_contacts` 唯一约束是同公司 email，且 `TenantQueryService.v3_company_contacts()` 可直接展示这些 clean 联系人。没有 email 的联系人暂不写入，避免无法幂等去重。

## Risks / Trade-offs

- 字段名漂移导致修复只覆盖列表不覆盖详情 → 后端列表、详情、联系人明细分别加断言。
- `0` 联系人数被前端当成空值 → 前端渲染使用 nullish 判断而不是 truthy 判断。
- 后端 `contacts_count` 与 `clean_contacts` 实际行数不一致 → 本 change 修复新采集/可重放 raw 中联系人明细的落库链路；历史已经丢失明细的 raw 记录不伪造联系人，后续需要通过重新采集或明确 backfill 任务补齐。

## Migration Plan

无需数据库迁移。

部署时按普通前后端修复发布：先运行后端单测和前端 typecheck/build，再随应用镜像发布。若发现异常，可回滚到上一版前后端镜像；数据无需回滚。

## Open Questions

无阻塞问题。实施中如发现 tenant API 完全缺少 admin 所见联系人数据来源，而不是字段映射问题，需要暂停并补充本 change 的设计与任务。
