## Why

Admin 腾道 raw 页面当前把内部抓取状态列展示在主表里，同时把“采集方式”硬编码为 `tendata`，信息重复且容易误导运营。详情抽屉只显示联系人数量，不显示 `tendata_raw_contacts` 明细，无法在 raw 证据层核对联系人来源。

## What Changes

- 腾道 raw 主表隐藏 `补详情`、`贸易`、`联系人` 三个抓取状态列。
- 腾道 raw 主表删除硬编码 `采集方式 = tendata` 列。
- 腾道 raw 详情抽屉展示该 raw company 关联的联系人明细。
- 后端 raw contacts API 支持 `provider=tendata`，从 `tendata_raw_contacts` 返回 key display fields。
- 删除或替换“V3 raw 列表默认不返回联系人明细”的旧文案，避免与新决策冲突。
- 不改变 raw payload 默认不返回的契约；联系人明细只返回展示必要字段，不返回 `raw_payload`。

## Capabilities

### New Capabilities

- `admin-tendata-raw-contact-details`: 定义 admin 腾道 raw 主表列展示、详情抽屉联系人明细展示，以及 `/raw/tendata/companies/{id}/contacts` API 行为。

### Modified Capabilities

- None.

## Impact

- 前端：admin `CollectionArchive` 腾道页表格列配置与详情 Drawer。
- 共享 API 类型：raw contact row 类型沿用或补齐 tendata 字段。
- 后端：admin raw contacts API service 分支，读取 `tendata_raw_contacts`。
- 测试：后端 service/API 覆盖 tendata contacts；前端至少覆盖列配置和详情联系人渲染。
