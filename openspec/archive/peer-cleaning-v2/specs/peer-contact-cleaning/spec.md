# peer-contact-cleaning Specification

## Purpose
定义同行公司联系人清洗层：将多条 raw 来源的联系人按 email 去重，存储到 peer_company_contacts，关联到 peer_company。

## Requirements

### Requirement: 系统 SHALL 维护去重后的 peer 联系人表

#### Scenario: 同一 peer 下多条 raw 有相同 email 的联系人
- **GIVEN** peer A 关联了 raw#1 和 raw#2
- **AND** raw#1 有联系人 email=zhang@example.com, name='张三', position='经理'
- **AND** raw#2 有联系人 email=zhang@example.com, name='张三', position='总经理'
- **WHEN** 联系人清洗执行
- **THEN** peer_company_contacts SHALL 只存一条 email=zhang@example.com
- **AND** 字段取最新 raw 数据（position='总经理'）

#### Scenario: 联系人无 email 时按 source_contact_id 去重
- **GIVEN** 联系人 email 为空
- **AND** source_contact_id='ct_456'
- **WHEN** 联系人清洗执行
- **THEN** SHALL 按 (peer_company_id, source_contact_id) 去重

#### Scenario: 联系人既无 email 也无 source_contact_id
- **GIVEN** 联系人 email 和 source_contact_id 都为空
- **WHEN** 联系人清洗执行
- **THEN** SHALL 按 (peer_company_id, name, phone) 去重
- **AND** 如果 name 也为空，SHALL 跳过该联系人

### Requirement: peer_company_contacts 表结构

#### Scenario: 表字段定义
- **THEN** peer_company_contacts SHALL 包含：
  - id (bigserial PK)
  - peer_company_id (uuid FK → peer_companies)
  - email (text, nullable)
  - name (text, nullable)
  - position (text, nullable)
  - phone (text, nullable)
  - mobile (text, nullable)
  - source_contact_id (text, nullable)
  - raw_company_id (bigint, 最后一次写入的来源 raw)
  - created_at, updated_at

### Requirement: 清洗联系人后同步更新 peer 的 contact_count

#### Scenario: 联系人清洗完成
- **WHEN** 某个 peer 的联系人清洗完成
- **THEN** peer_companies.contact_count SHALL 等于该 peer 在 peer_company_contacts 中的行数
