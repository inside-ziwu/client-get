## ADDED Requirements

### Requirement: collection_type 口径单一真源
系统 SHALL 在共享模块 `collection_source` 中维护采集标签常量、jsonb SQL 片段与 keyword/reverse 判定函数，admin service、tenant service、行业 fan-out worker 均引用该模块，口径与 admin 端已上线行为一致。

#### Scenario: 判定口径
- **WHEN** 公司 `data_source_tags` 包含「外贸通关键词采集」（含同时带其他标签如「腾道」）
- **THEN** collection_type = 'keyword'；NULL、空数组或不包含时 = 'reverse'

### Requirement: tenant 列表按采集类型筛选
系统 SHALL 在 tenant 公司列表提供「采集类型」筛选（不限/关键词采集/精准反推），后端按 jsonb 包含语义过滤。

#### Scenario: 筛选关键词采集
- **WHEN** 用户选择「采集类型 = 关键词采集」
- **THEN** 列表只显示 data_source_tags 包含「外贸通关键词采集」的公司，分页总数同步

#### Scenario: 筛选精准反推
- **WHEN** 用户选择「采集类型 = 精准反推」
- **THEN** 列表只显示 data_source_tags 为 NULL、空数组或不包含该标签的公司

#### Scenario: 与其他筛选条件叠加
- **WHEN** 采集类型与国家、行业、评分等筛选同时设置
- **THEN** 所有条件以 AND 逻辑叠加

### Requirement: tenant 列表与详情展示采集类型
系统 SHALL 在 tenant 公司列表新增「采集类型」列，并在公司详情展示采集类型；后端列表与详情响应均返回 `collection_type` 计算字段。

#### Scenario: 列表展示
- **WHEN** 列表渲染任一公司行
- **THEN** 采集类型列显示「关键词采集」（keyword）或「精准反推」（reverse），无空白；列头数组与空态 colSpan 与新列数一致

#### Scenario: 详情展示
- **WHEN** 用户打开公司详情
- **THEN** 详情显示的采集类型与列表行一致

### Requirement: 既有 jsonb 筛选修复
系统 SHALL 修复 tenant_query_service 中 4 处对 jsonb 列误用数组操作符的筛选（source_type、sources×2、product_tags），传参调用不得报 500。

#### Scenario: source_type/sources 筛选回归
- **WHEN** API 调用传入 source_type 或 sources 参数
- **THEN** 查询以 jsonb 包含/展开语义正常执行并返回过滤结果

#### Scenario: product_tags 筛选回归
- **WHEN** API 调用传入 product_tags 参数
- **THEN** 查询正常执行，不出现 operator does not exist 错误
