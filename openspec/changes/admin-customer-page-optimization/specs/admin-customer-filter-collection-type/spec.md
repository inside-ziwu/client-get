## ADDED Requirements

### Requirement: 按采集类型筛选客户数据
系统 SHALL 在 admin 客户数据列表页提供「采集类型」筛选，允许用户按「关键词采集」或「精准反推」过滤数据。

#### Scenario: 筛选关键词采集
- **WHEN** 用户选择筛选条件「采集类型 = 关键词采集」
- **THEN** 列表只显示 `data_source_tags` 包含 `"外贸通关键词采集"` 的公司，分页总数同步更新

#### Scenario: 筛选精准反推
- **WHEN** 用户选择筛选条件「采集类型 = 精准反推」
- **THEN** 列表只显示 `data_source_tags` 为 NULL、空数组、或不包含 `"外贸通关键词采集"` 的公司

#### Scenario: 不限采集类型
- **WHEN** 用户选择筛选条件「采集类型 = 不限」或未选择
- **THEN** 列表显示全部公司，不按采集类型过滤

#### Scenario: 采集类型与其他筛选条件组合
- **WHEN** 用户同时设置「采集类型」和其他筛选条件（国家、行业等）
- **THEN** 所有筛选条件以 AND 逻辑叠加

### Requirement: 表格显示采集类型列
系统 SHALL 在客户数据列表表格中显示「采集类型」列，替代已移除的「电话」列。

#### Scenario: 关键词采集数据展示
- **WHEN** 公司的 `data_source_tags` 包含 `"外贸通关键词采集"`
- **THEN** 采集类型列显示「关键词采集」

#### Scenario: 精准反推数据展示
- **WHEN** 公司的 `data_source_tags` 不包含 `"外贸通关键词采集"`（含 NULL 和空数组）
- **THEN** 采集类型列显示「精准反推」

### Requirement: API 返回 collection_type 计算字段
后端 SHALL 在 `GET /api/v1/collection/wmt-clean-companies` 的列表响应中为每条记录返回 `collection_type` 字段，值为 `"keyword"` 或 `"reverse"`。

#### Scenario: 后端计算关键词采集
- **WHEN** 记录的 `data_source_tags` 包含 `"外贸通关键词采集"`
- **THEN** 响应中 `collection_type` 值为 `"keyword"`

#### Scenario: 后端计算精准反推
- **WHEN** 记录的 `data_source_tags` 为 NULL、空数组、或不包含 `"外贸通关键词采集"`
- **THEN** 响应中 `collection_type` 值为 `"reverse"`

### Requirement: 页面标题和描述更新
系统 SHALL 将页面标题从「外贸通客户数据」改为「客户数据」，描述从「waimaotong_clean_companies 清洗后的公司数据及联系人。」改为「清洗后的公司数据及联系人。」

#### Scenario: 页面标题展示
- **WHEN** 用户访问 admin 客户数据页
- **THEN** 页面标题显示「客户数据」，描述显示「清洗后的公司数据及联系人。」
