# tenant-company-list-ui Specification

## Requirements

### Requirement: tenant 公司列表 SHALL 使用中文国家标签

tenant 公司列表及其复用的公司选择列表 SHALL 向租户端用户展示中文国家标签，不得在常见国家场景下直接展示 ISO3 代码或英文国家名。

#### Scenario: ISO3 国家代码显示为中文
- **GIVEN** 公司数据中的国家值为 `TUR`
- **WHEN** 租户访问公司列表
- **THEN** 页面 SHALL 显示 `土耳其`
- **AND** 页面 MUST NOT 显示裸露的 `TUR`

#### Scenario: 已知英文国家名显示为中文
- **GIVEN** 公司数据中的国家值为 `United States`
- **WHEN** 租户访问公司列表
- **THEN** 页面 SHALL 显示 `美国`

#### Scenario: 未识别国家值保留原始值
- **GIVEN** 公司数据中的国家值无法识别
- **WHEN** 租户访问公司列表
- **THEN** 页面 SHALL 保留原始值
- **AND** 后续实现 SHOULD 通过补充映射表优先解决该漏项，而不是用笼统兜底文案掩盖数据

### Requirement: tenant 公司列表 MUST 移除电话列

tenant 公司列表 MUST 不再展示电话列，以减少横向拥挤并突出公司识别、评分、行业和联系人等核心字段。

#### Scenario: 公司列表不展示电话列
- **WHEN** 租户访问公司列表
- **THEN** 表头 MUST NOT 包含 `电话`
- **AND** 每行 MUST NOT 渲染电话字段单元格

#### Scenario: 空状态列数保持正确
- **GIVEN** 公司列表无数据或正在加载
- **WHEN** 页面渲染空状态
- **THEN** 空状态单元格 SHALL 跨越当前实际列数
- **AND** 表格布局 MUST NOT 因列数变化错位

### Requirement: tenant 公司列表 SHALL 保持现有操作能力

tenant 公司列表 UI 优化 SHALL 保持现有筛选、批量选择、查看详情、加入群组、拉黑、新增公司和分页能力不变。

#### Scenario: 行级操作仍可用
- **WHEN** 租户在公司列表中查看任意公司行
- **THEN** 页面 SHALL 继续提供 `详情`、`群组`、`拉黑` 操作

#### Scenario: 批量操作仍可用
- **WHEN** 租户勾选一个或多个公司
- **THEN** 页面 SHALL 显示批量操作栏
- **AND** 租户 SHALL 能继续将选中公司加入群组
