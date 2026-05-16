## Context

`admin/collection/tendata` 是平台运营查看腾道 raw 公司的页面。当前主表同时展示公司业务字段、内部 enrichment 状态字段，以及一个硬编码的 `tendata` tag。详情抽屉只显示 `contacts_count` 和“raw 不返回联系人明细”的说明。

V3 当前已存在 `tendata_raw_contacts` 表，且 raw API 已有统一路径 `/raw/{provider}/companies/{raw_company_id}/contacts`。但 service 只支持 `lixiaoyun`，`provider=tendata` 会直接返回空数组。因此要显示腾道联系人明细，需要前后端一起补齐，而不是只改 UI。

## Goals / Non-Goals

**Goals:**

- 让腾道 raw 主表聚焦公司级字段，隐藏内部 enrichment 状态列。
- 删除主表中没有信息增量的硬编码 `采集方式 = tendata`。
- 在腾道 raw 详情抽屉中显示 `tendata_raw_contacts` 明细。
- 保持 raw company list 轻量；联系人明细通过详情抽屉按需加载。
- 默认不返回 `raw_payload`，避免把 provider 原始 payload 暴露到普通运营视图。

**Non-Goals:**

- 不改变 `tendata_raw_companies` / `tendata_raw_contacts` schema。
- 不改变 cleanup_service 或 clean/tenant 联系人合并规则。
- 不在主表直接展开联系人明细。
- 不为 raw payload 调试视图新增功能。
- 不影响励销云 raw 联系人明细现有行为。

## Decisions

### 1. 主表删除 4 个展示列，而不是只隐藏状态 tag 样式

删除列：

- `补详情` → `detail_status`
- `贸易` → `trade_status`
- `联系人` → `contacts_status`
- `采集方式` → 当前硬编码 `tendata`

理由：前三个是内部抓取状态，不是运营浏览 raw 公司列表时的主业务信息；第四个与页面“腾道数据”上下文重复，且不是 schema 字段。保留这些列会让主表横向过宽，也容易把“联系人状态”误读为“联系人数量”。

替代方案：把三列移动到详情抽屉。暂不采用，因为当前需求明确是主表隐藏；如排障需要，可未来在 debug/detail 区域补充。

### 2. 详情抽屉按需调用 contacts API

详情抽屉打开时，用当前 raw company id 调用：

```text
GET /api/v1/raw/tendata/companies/{raw_company_id}/contacts
```

返回字段用于展示：

- `name`
- `position`
- `email`
- `phone`
- `mobile`
- `created_at`

理由：raw 主表仍保持分页轻量；只有用户打开详情时才查询 1:N 联系人。

替代方案：raw company list 直接返回 contacts 数组。暂不采用，因为会放大列表响应体，也违背 provider raw APIs 默认 payload-light 的约定。

### 3. 后端扩展现有 service 分支，不新增路由

现有 route 已覆盖 `{provider}`，因此只需要让 service 支持 `provider == "tendata"`，从 `tendata_raw_contacts` 查询。`lixiaoyun` 分支保持不变；不支持的 provider 继续返回空或按现有错误策略处理。

理由：复用已有 API 形状，避免新增一条只服务腾道的路由。

### 4. 删除旧文案，替换为 raw/clean 区分说明

旧文案“V3 raw 列表默认不返回联系人明细，仅返回联系人数量；联系人明细在清洗后的客户/租户视图中查看。”与新决策冲突。

新语义应为：raw 详情展示 provider 原始联系人；clean/tenant 视图展示清洗去重合并后的联系人。

## Risks / Trade-offs

- **Risk: 腾道联系人数据为空时用户误以为接口失败** → Drawer 明确空态“暂无 raw 联系人”，并保留联系人数量展示。
- **Risk: raw 联系人与 clean 联系人数量不一致** → 文案明确 raw 是 provider 原始联系人，clean/tenant 是清洗合并后视图。
- **Risk: 邮箱/电话字段可能为空** → 表格允许空值显示 `—`，不做 sendability 判断。
- **Risk: 列删除影响排障效率** → 内部 enrichment 状态仍在 API 和 DB 中保留；未来可放到 debug 入口，不作为主表默认列。
