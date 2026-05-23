## ADDED Requirements

### Requirement: 群组选择器 SHALL 显示公司数而非联系人数

群组选择器下拉项中，群组名称后的计数 MUST 显示为"X 家公司"格式，反映群组内公司数量。确认步骤中"预估收件人数"同步更新显示。

#### Scenario: 群组包含多家公司
- **GIVEN** 群组"巴西LED照明行业"包含 14 家公司
- **WHEN** 用户在发送计划收件人步骤打开群组选择器
- **THEN** 显示"巴西LED照明行业（14 家公司）"

#### Scenario: 群组包含 1 家公司
- **GIVEN** 群组"测试群组"包含 1 家公司
- **WHEN** 用户打开群组选择器
- **THEN** 显示"测试群组（1 家公司）"

### Requirement: 收件人预览合计 SHALL 显示公司数和收件人数

收件人预览底部合计 MUST 同时显示公司数和收件人数，格式为"合计 X 家公司，Y 位收件人"。

#### Scenario: 预览合计显示
- **GIVEN** 群组包含 14 家公司，按规则选取后共 42 位收件人
- **WHEN** 用户选择该群组并查看收件人预览
- **THEN** 底部显示"合计 14 家公司，42 位收件人"

#### Scenario: 部分公司无有效收件人
- **GIVEN** 群组包含 14 家公司，其中 2 家公司所有联系人都无邮箱
- **WHEN** 用户选择该群组
- **THEN** 合计中公司数仍为 14，收件人数仅统计有效入选的联系人

### Requirement: 系统 SHALL 按联系人分类等级排序选取收件人

从群组选取收件人时，系统 MUST 按以下优先级排序：
1. `position_classification_levels.is_sendable = true` 的联系人优先
2. 在 is_sendable=true 内，按 `sort_order` 从高到低排序（A级 > B级）
3. 未匹配到任何分类等级的联系人排在所有已分类联系人之后
4. 仅选取有邮箱的联系人

#### Scenario: 混合等级公司的收件人选取
- **GIVEN** 某公司有 12 个联系人：3 个 A 级（is_sendable=true, sort_order=100）、4 个 B 级（is_sendable=true, sort_order=80）、2 个 X 级（is_sendable=false, sort_order=10）、3 个未分类，全部有邮箱
- **WHEN** 系统为该公司选取收件人
- **THEN** 选取顺序为：3 个 A 级 → 4 个 B 级 → 1 个未分类，共 8 人
- **AND** X 级联系人因 is_sendable=false 被排除

#### Scenario: 联系人不足 8 人
- **GIVEN** 某公司有 5 个联系人全部 B 级、is_sendable=true、有邮箱
- **WHEN** 系统为该公司选取收件人
- **THEN** 全部 5 人入选

#### Scenario: 全部未分类
- **GIVEN** 某公司有 10 个联系人均未匹配到分类等级，全部有邮箱
- **WHEN** 系统为该公司选取收件人
- **THEN** 取前 8 个作为收件人

#### Scenario: 无有效联系人
- **GIVEN** 某公司所有联系人均无邮箱或均为 is_sendable=false 的等级
- **WHEN** 系统为该公司选取收件人
- **THEN** 该公司收件人为 0 人

### Requirement: 每家公司收件人 MUST NOT 超过 8 人

无论该公司有多少联系人，发送计划中每家公司的收件人上限为 8 人。

#### Scenario: 公司联系人超过 8 人
- **GIVEN** 某公司有 20 个联系人，其中 15 个 A 级 is_sendable=true 有邮箱
- **WHEN** 系统为该公司选取收件人
- **THEN** 仅取前 8 人（按 sort_order 排序后的前 8 个）

#### Scenario: 公司联系人恰好 8 人
- **GIVEN** 某公司有 8 个有效联系人
- **WHEN** 系统为该公司选取收件人
- **THEN** 全部 8 人入选

### Requirement: 收件人预览 SHALL 按公司汇总展示

预览表格 MUST 按公司维度汇总，每家公司显示为一行，标注入选收件人数量。公司行可展开查看收件人明细，明细包含联系人姓名、邮箱、分类等级。

#### Scenario: 预览公司汇总展示
- **GIVEN** 群组包含 3 家公司，分别有 5、8、3 位入选收件人
- **WHEN** 用户查看收件人预览
- **THEN** 显示 3 行，每行显示公司名和收件人数量（如"Ilumac（5 位收件人）"）

#### Scenario: 展开查看明细
- **GIVEN** 预览中某公司行显示"Ilumac（5 位收件人）"
- **WHEN** 用户点击展开该公司行
- **THEN** 展开显示 5 行明细：联系人姓名、邮箱、分类等级名称

#### Scenario: 公司无入选收件人
- **GIVEN** 某公司所有联系人被排除（无邮箱/is_sendable=false/黑名单等）
- **WHEN** 用户查看收件人预览
- **THEN** 该公司仍显示在列表中，收件人数量为 0

### Requirement: 预览 API SHALL 返回按公司分组的收件人数据

新增 `GET /api/v1/send-plans/preview-recipients?group_id={id}` 端点，返回按公司分组的收件人列表及汇总统计。

#### Scenario: 请求预览收件人
- **GIVEN** 群组 ID 有效
- **WHEN** 前端请求 `GET /api/v1/send-plans/preview-recipients?group_id={group_id}`
- **THEN** 返回 JSON 包含 `companies` 数组（每项含 `tenant_company_id`, `company_name`, `recipient_count`, `recipients` 明细）和 `summary`（含 `company_count`, `recipient_count`）

#### Scenario: 群组不存在
- **GIVEN** 群组 ID 无效或不属于当前租户
- **WHEN** 前端请求预览
- **THEN** 返回 422 错误"收件人分组不存在或不属于当前租户"
