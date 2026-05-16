## Why

V3 反推链路中，平台关键词先通过励销云找到中国同行/供应商，再由腾道反查海外买家；腾道 raw 数据已经承载海外买家证据，但从 raw 清洗合并到平台干净库、再到租户公司列表展示的业务规则尚未固化。当前需要先明确“平台实体清洗”和“租户可见性物化”的边界，避免出现 admin 干净库有数据、租户侧看不到或看得到但运营状态断层的问题。

## What Changes

- 新增腾道 raw → clean_companies 的平台实体清洗规则。
- 明确腾道 raw 必须有公司名与国家，缺国家的 raw 不进入干净库。
- 明确第一版去重主规则为 `normalized_name + country_iso3`。
- 明确字段合并策略：
  - 全局非空补空。
  - 数值摘要字段 `trade_amount_3y_usd` / `trade_count` / `contacts_count` 保留最新来源摘要。
  - 描述摘要字段 `industry_desc` / `employee_num` 保留最新来源摘要。
  - 证据集合字段 `product_tags` / `pcb_suppliers` / `aliases` 追加去重。
- 明确清洗成功后，干净公司必须继承腾道 raw 上的 `keyword_master_id`，并追加维护干净公司与平台关键词的关联。
- 明确 `clean_company_keywords` 是平台关键词与干净公司的命中关系表，必须保留；取消租户订阅不删除该平台关系。
- 明确租户订阅决定基础展示：订阅某平台关键词的租户，应看到该平台关键词关联的干净公司。
- 明确将可见性物化到租户私有状态层，`tenant_companies` 增加 `visibility_status = visible / hidden` 作为租户公司列表的基础展示依据；后续评分、标签、分组、发信由租户自行运营，不作为基础展示前置。
- 明确 `tenant_companies.business_status` 去掉交互态 `selected`，改为运营阶段 `new / in_group / in_plan / contacted / archived`。
- 明确 `tenant_companies.data_status` 由系统判断数据是否够运营，不由租户手动判断，也不决定公司是否显示。
- 明确取消 tenant 关键词后，如果该租户已无其他 active 关键词覆盖某家公司，则该公司在该租户侧隐藏，并清空该租户对该公司的私有运营状态；以后重新订阅按新客户重新开始。
- 明确租户公司列表不再以 `clean_company_keywords + tenant_keyword` 动态 join 作为基础展示依据，而是以 `tenant_companies.visibility_status = visible` 为准。
- 明确 `company_scores.tenant_company_id`、`group_members.tenant_company_id`、`scoring_jobs.tenant_company_id` 语义上指向 `tenant_companies.id`，应统一为 `bigint` 并补外键。
- 明确历史可见性、旧 `selected` 状态、`tenant_company_id` 类型对齐等迁移必须有回填/清理策略，不允许默认全量可见或强行 uuid 转 bigint。
- 暂不改变腾道采集任务触发逻辑；本 change 假设腾道 raw 已存在。

## Capabilities

### New Capabilities

- `tendata-cleaning-pipeline`: 定义已有腾道 raw 如何清洗合并为平台干净公司、继承平台关键词，并物化到订阅租户的公司列表。

### Modified Capabilities

- 无。

## Impact

- 后端：`cleanup_service`、`collection_service` 中 raw → clean 相关逻辑、租户公司可见性物化逻辑。
- 数据库：可能涉及 `tenant_companies` 可见字段/状态字段、`business_status` 约束调整、相关 `tenant_company_id` 类型与外键对齐、干净公司与平台关键词关联表、必要索引。
- Tenant API：公司列表应以租户私有可见状态为展示依据，同时保留平台关键词订阅关系作为物化来源。
- Admin API：干净库与 cleanup health 需要能追溯 source 与关键词继承状态。
- 不涉及：腾道 stage2 采集任务自动触发、励销云 stage1 跨天续采、邮件发送流程实现。
