## Why

赵奎租户（tenant slug: `t-019dc238`）下，租户端手工添加的公司 `muzi`、现有全部群组、以及现有发送计划需要从当前环境中彻底移除；普通业务 API 当前多采用软删除，无法满足这次数据清理的“硬删除”要求。

本 change 先把一次性硬删除的范围、顺序、验证和回滚边界写清楚，避免直接执行破坏性 SQL 时误删共享干净公司、其他租户数据或邮件发送历史依赖。

## What Changes

- **BREAKING**: 新增一次性运营清理流程，仅针对赵奎租户 `t-019dc238` 硬删除 tenant 手工添加的 `muzi` tenant company 及其租户侧关联数据。
- **BREAKING**: 硬删除赵奎租户 `t-019dc238` 下全部群组与群组成员，不走现有 `groups.deleted_at` 软删除语义。
- **BREAKING**: 硬删除赵奎租户 `t-019dc238` 下全部发送计划及其步骤、收件人、运行态队列/记录；这些是用户确认的测试数据，即使已产生 `emails` / `email_events` 也纳入硬删除，不走现有 `sending_plans.deleted_at` 软删除语义。
- 清理前必须输出待删除预览和数量；清理后必须输出核验结果，确认目标公司、群组、发送计划在租户侧不可见且数据库中目标行不存在。
- 不删除平台级 clean company / clean contacts / provider raw 数据，除非它们只属于本次手工 company 且当前 design 明确证明无共享依赖。

## Capabilities

### New Capabilities
- `tenant-hard-delete-operations`: 定义一次性租户数据硬删除操作的范围、顺序、预览、执行、核验与安全边界。

### Modified Capabilities
- `tenant-company-status-semantics`: 明确本次硬删除是受控运营清理，不应通过 `business_status` 或 `visibility_status` 表达删除结果。
- `tenant-sending-plan-creation`: 明确发送计划硬删除后的租户发送计划列表、详情与创建链路应保持一致，不依赖被删除计划。

## Impact

- 后端：可能新增一次性脚本或受控管理命令；涉及 `tenant_companies`、`tenant_contacts`、`groups`、`group_members`、`sending_plans`、`sequence_steps`、`sending_plan_recipients` 以及发送运行态相关表。
- 数据库：执行显式 `DELETE`，必须在事务内按外键依赖顺序删除；执行前后记录只读核验 SQL。
- 测试：需要覆盖预览计数、删除顺序、租户隔离、以及删除后列表/详情不可见。
- 前端：不新增日常 UI；如实现为脚本或管理命令，前端无需改动。
