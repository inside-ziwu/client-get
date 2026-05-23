## ADDED Requirements

### Requirement: 新建计划时发件人名称 SHALL 默认取 tenant 租户名称

进入新建计划向导时，发件人名称字段自动填入当前 tenant 的租户名称（`tenants.name`），用户可修改。

#### Scenario: 打开新建计划向导
- **GIVEN** 当前 tenant 名称为"信安 PCB"
- **WHEN** 用户进入新建计划向导的基本信息步骤
- **THEN** 发件人名称字段已填入"信安 PCB"

#### Scenario: 用户修改发件人名称
- **GIVEN** 发件人名称已默认填入"信安 PCB"
- **WHEN** 用户将其改为"张经理"
- **THEN** 字段值更新为"张经理"，不会被重置

### Requirement: 新建计划时发送域名 SHALL 默认取最早验证域名

进入新建计划向导时，发送域名字段自动选中已验证域名中 `created_at` 最早的一个。若无已验证域名则不选中。

#### Scenario: 有多个已验证域名
- **GIVEN** tenant 有 3 个已验证域名，created_at 最早的是 `a.com`
- **WHEN** 用户进入新建计划向导
- **THEN** 发送域名下拉框默认选中 `a.com`

#### Scenario: 无已验证域名
- **GIVEN** tenant 没有已验证域名
- **WHEN** 用户进入新建计划向导
- **THEN** 发送域名下拉框未选中，显示"无已验证域名"

### Requirement: 新建计划时发件邮箱 SHALL 默认取选中域名的 sender_email

进入新建计划向导时，发件邮箱字段自动填入当前选中域名的 `sender_email`。若域名未维护 sender_email 则留空。

#### Scenario: 默认域名有 sender_email
- **GIVEN** 默认选中域名 `a.com` 的 sender_email 为 `info@a.com`
- **WHEN** 用户进入新建计划向导
- **THEN** 发件邮箱字段已填入 `info@a.com`

#### Scenario: 默认域名无 sender_email
- **GIVEN** 默认选中域名 `a.com` 的 sender_email 为 null
- **WHEN** 用户进入新建计划向导
- **THEN** 发件邮箱字段为空，用户需手动填写

### Requirement: 切换域名时发件邮箱 MUST 自动联动更新

用户在基本信息步骤切换发送域名时，发件邮箱字段 MUST 自动替换为新域名的 `sender_email`。

#### Scenario: 切换到有 sender_email 的域名
- **GIVEN** 当前域名为 `a.com`（sender_email=`info@a.com`）
- **WHEN** 用户将域名切换到 `b.com`（sender_email=`sales@b.com`）
- **THEN** 发件邮箱自动更新为 `sales@b.com`

#### Scenario: 切换到无 sender_email 的域名
- **GIVEN** 当前域名为 `a.com`（sender_email=`info@a.com`）
- **WHEN** 用户将域名切换到 `c.com`（sender_email=null）
- **THEN** 发件邮箱清空为空字符串
