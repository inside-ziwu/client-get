## Why

Admin Next.js 上线后，「同行公司」页面列表大量字段显示为 `-`。根因是页面仍查询旧 `/collection/raw/lixiaoyun` API，并从 `raw_payload` 读取字段；后端旧 raw API 默认不返回 payload，也不返回 `english_name`、`esdate`、`reg_capital`、`employee_scale`、`reg_address` 等字段。

## What Changes

- 将 Admin Next.js「同行公司」页面改为查询新版 raw API `/raw/lixiaoyun/companies`。
- 使用新版 API 返回的顶层字段渲染英文名、员工规模、注册资金、成立时间、注册地址、网址、联系人、关键词、采集时间。
- 保留页面现有筛选表单和详情 Sheet。
- 修正后端 V3 raw API 的 Lixiaoyun 字段兜底：当标准列为空但 `raw_payload` 内存在英文名或联系人数量时，列表 API 仍返回真实值。
- 更新前端共享 API 类型和契约测试，防止页面回退到旧 raw API 或 `raw_payload` 字段映射。

## Non-Goals

- 不修改「同行数据（清洗）」页面，该页面已查询 `peer-companies` API。
- 不修改数据库 schema、worker 或采集清洗逻辑。
- 不调整菜单、权限、部署脚本或镜像 tag 规则。

## Capabilities

### New Capabilities

- `admin-peers-raw-display`: Admin「同行公司」raw 页面 SHALL 使用后端 V3 raw Lixiaoyun company API 展示真实字段。

### Modified Capabilities

- None.

## Impact

| Area | Impact |
| --- | --- |
| frontend/apps/admin-next | Update `/collection/peers` data source and field mapping. |
| frontend/packages/shared-api | Add typed client method for `/raw/lixiaoyun/companies`. |
| backend | Update existing V3 raw Lixiaoyun list query fallback for `english_name` and `contacts_count`. |
| database | No change. |
| deployment | Requires rebuilding and pushing `clientget-admin` image after verification. |
