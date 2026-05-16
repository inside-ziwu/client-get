## Why

admin 客户数据/干净公司库与 tenant 客户公司/精选客户当前以 `country_iso3` 作为机器国家键，但 admin/tenant 页面展示和筛选需要对人使用中文国家名称。当前需要新增一条明确规则：前端面向人的国家值统一使用中文，筛选和后端执行仍使用 ISO3；干净公司库继续保存 `country_iso3`，不做国家字段数据 update。

## What Changes

- admin 客户数据列表、详情、筛选，以及 tenant 客户公司列表、详情、精选客户、筛选中的人类可读国家值统一使用中文国家名称。
- 前端国家筛选项使用中文 label、ISO3 value；用户选择中文国家后，实际请求和后端查询仍使用 `country_iso3`。
- admin 与 tenant 共用前端共享模块中的小型国家映射表和展示 helper；不引入大型 i18n/国家库，不新增数据库国家表。
- 国家展示第一版以 ISO3 到中文名称的确定性映射为主；中文输入原样展示，未知值原样保留，不做完整国家解析或别名推断。
- 对无法可靠识别的国家值，不做猜测式转换，应保留原值以便追溯。
- admin 客户数据/干净公司库不更新国家存储值；如果后端持久化 `country_iso3`（如 `USA`），前端展示 `美国` 且用户选择 `美国` 能筛选到对应 `USA` 数据即可。

## Capabilities

### New Capabilities

- `customer-country-localization`: 定义 admin/tenant 客户数据国家展示与筛选的中文化要求，并约束干净公司库继续使用 `country_iso3`。

### Modified Capabilities

- 无。

## Impact

- 影响 admin/tenant 客户数据列表、详情、筛选控件、前端共享国家映射工具和相关测试用例。
- 不影响 admin 客户数据/干净公司库的数据存储；不执行正式数据 update。
- 不引入外部 API、数据库 schema 或部署依赖变更。
