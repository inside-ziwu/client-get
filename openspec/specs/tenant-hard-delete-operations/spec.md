# tenant-hard-delete-operations Specification

## Purpose
TBD - created by archiving change hard-delete-muzi-groups-sending-plans. Update Purpose after archive.
## Requirements
### Requirement: Tenant hard delete operation previews target rows before execution
系统 SHALL 在任何破坏性数据库写入前提供硬删除 dry-run 预览，并且范围限定为赵奎租户 slug `t-019dc238`。

#### Scenario: Preview target tenant cleanup
- **WHEN** 操作人未提供执行确认，只对 tenant slug `t-019dc238` 运行硬删除操作
- **THEN** 系统 MUST 返回匹配的 `muzi` tenant company、tenant contacts、groups、group_members、sending_plans、sequence_steps、sending_plan_recipients、sequence_enrollments、emails、email_events、email_send_locks 的计数
- **AND** 系统 MUST NOT 删除或更新任何数据库行

#### Scenario: Preview finds unexpected muzi candidates
- **WHEN** tenant slug `t-019dc238` 下公司名精确匹配 `muzi` 的 tenant company 为 0 个或多个
- **THEN** 系统 MUST 列出候选 ID 与识别字段
- **AND** 系统 MUST 在执行前停止

#### Scenario: Operator explicitly confirms multiple muzi candidates
- **WHEN** tenant slug `t-019dc238` 下公司名精确匹配 `muzi` 的 tenant company 为多个
- **AND** 操作人已人工确认这些候选都是目标手工测试数据
- **AND** 执行命令显式提供完整候选 `tenant_company_id` 列表
- **THEN** 系统 MAY 继续执行硬删除
- **AND** 系统 MUST 拒绝任何遗漏候选、包含额外 ID、或 ID 不属于精确匹配候选的确认列表

### Requirement: Tenant hard delete operation removes only target tenant data
系统 SHALL 使用 slug `t-019dc238` 解析出的 tenant id 约束每一条硬删除语句，并且 SHALL NOT 影响其他租户。

#### Scenario: Execute tenant cleanup
- **WHEN** 操作人对 tenant slug `t-019dc238` 提供显式确认并执行硬删除操作
- **THEN** 系统 MUST 硬删除目标租户的 groups 与 group_members
- **AND** 系统 MUST 硬删除目标租户的 sending_plans 及其租户侧依赖发送数据，包括用户已确认属于测试数据的 emails 与 email_events
- **AND** 系统 MUST 硬删除公司名精确匹配 `muzi` 的 tenant company 及其租户侧依赖行
- **AND** 系统 MUST NOT 删除任何其他租户的行

#### Scenario: Tenant is missing
- **WHEN** 操作人未提供 tenant slug `t-019dc238`，或该 slug 无法解析
- **THEN** 系统 MUST 在预览或执行前拒绝操作

### Requirement: Hard delete operation preserves shared source data by default
系统 SHALL 默认保留 shared clean/provider 来源数据，除非实施期依赖检查证明该行只属于目标手工公司且操作显式纳入该行。

#### Scenario: Muzi tenant company points to clean company
- **WHEN** 硬删除操作删除 `muzi` tenant company
- **THEN** 系统 MUST 默认保留关联的 clean company 与 clean contacts
- **AND** 系统 MUST 只删除租户侧 company/contact 行和依赖的租户操作行

### Requirement: Hard delete operation verifies deletion outcome
系统 SHALL 在执行后运行删除结果核验，并报告目标剩余行。

#### Scenario: Verification succeeds
- **WHEN** 硬删除事务提交
- **THEN** 系统 MUST 核验目标租户 groups、group_members、sending_plans、以及已确认的 `muzi` tenant company 行不再存在
- **AND** 系统 MUST 报告这些目标的剩余行数为 0

#### Scenario: Verification finds remaining target rows
- **WHEN** 删除后核验发现仍有目标剩余行
- **THEN** 系统 MUST 报告表名与剩余计数
- **AND** 本次操作 MUST 被视为未完成

