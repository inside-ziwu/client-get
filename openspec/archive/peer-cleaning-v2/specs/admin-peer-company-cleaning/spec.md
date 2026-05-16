## MODIFIED Requirements

### Requirement: 清洗字段合并策略改为「最新覆盖」

#### Scenario: 同一 peer 收到更新的 raw 数据
- **GIVEN** peer_companies 已有一条记录，name='深圳芯安科技'
- **WHEN** 新的 raw 记录被清洗，带有 name='深圳市芯安科技有限公司'
- **THEN** peer_companies.name SHALL 更新为 '深圳市芯安科技有限公司'（取最新）
- **AND** 所有非空字段 SHALL 以最新 raw 数据覆盖已有值

#### Scenario: 新 raw 数据字段为空，已有字段非空
- **WHEN** 新的 raw 记录某字段为空（如 english_name=NULL）
- **AND** peer_companies 已有该字段的值
- **THEN** peer_companies 该字段 SHALL 保留已有值，不被空值覆盖

### Requirement: source_id 跨 identity 复用 peer

#### Scenario: 同一 source_id 已通过其他 raw 关联到 peer
- **GIVEN** raw#1 有 domain=example.com，source_id=lx_123，已创建 peer A（identity=website_host:example.com）
- **AND** raw#2 无 domain，source_id=lx_123
- **WHEN** 系统清洗 raw#2
- **THEN** 系统 SHALL 查找 peer_company_sources 中 source_id=lx_123 的已有映射
- **AND** SHALL 复用 peer A，而非创建新 peer

### Requirement: 移除 health 端点

#### Scenario: health 端点不再暴露
- **WHEN** Admin API 被调用
- **THEN** `GET /collection/peer-companies/health` SHALL 不存在（404）

### Requirement: 新增 peer 联系人列表端点

#### Scenario: Admin 查看 peer 公司的联系人
- **WHEN** Admin 请求 `GET /collection/peer-companies/{id}/contacts`
- **THEN** 系统 SHALL 返回该 peer 关联的去重联系人列表
- **AND** 联系人来源于 peer_company_contacts 表
