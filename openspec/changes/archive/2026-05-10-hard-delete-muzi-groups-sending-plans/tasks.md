## 1. 范围审计

- [x] 1.1 按 slug `t-019dc238` 定位赵奎租户，并在任何删除预览或执行前打印 tenant id / tenant name。
- [x] 1.2 审计当前数据库 schema，确认引用 `sending_plans`、`sequence_steps`、`sequence_enrollments`、`sending_plan_recipients`、`tenant_companies`、`tenant_contacts`、`groups`、`group_members` 的外键。
- [x] 1.3 实现 `muzi` 公司名精确匹配；打印所有候选，若结果不是预期的租户手工公司，则暂停执行。
- [x] 1.4 在 dry-run 输出中统计目标发送计划的 `emails` 与 `email_events`；这些数据在 `t-019dc238` 租户下已由用户确认为测试数据，可纳入硬删除。

## 2. 清理命令

- [x] 2.1 新增后端一次性脚本或管理命令，默认以 dry-run 模式运行租户硬删除清理。
- [x] 2.2 实现 dry-run 预览计数，覆盖 `muzi` tenant company、tenant contacts、groups、group_members、sending_plans、sequence_steps、sending_plan_recipients、sequence_enrollments、emails、email_events、email_send_locks。
- [x] 2.3 实现执行确认保护，要求 tenant slug 为 `t-019dc238` 且提供显式确认 token。
- [x] 2.4 在事务内按叶子表到主表顺序删除发送计划依赖数据。
- [x] 2.5 在事务内按叶子表到主表顺序删除群组依赖数据。
- [x] 2.6 在事务内删除已确认 `muzi` tenant company 的租户侧依赖数据，默认保留 clean/provider 来源数据。
- [x] 2.7 实现删除后核验输出，打印目标表剩余行数。

## 3. 测试

- [x] 3.1 增加测试，证明 dry-run 只返回计数且不写数据库。
- [x] 3.2 增加测试，证明 execute 模式只删除目标租户行，不影响其他租户。
- [x] 3.3 增加测试，证明 `muzi` 精确匹配不会删除模糊名称匹配，并会在候选数量异常时暂停。
- [x] 3.4 增加测试，证明被硬删除的发送计划从列表/详情消失，且之后仍可新建发送计划。
- [x] 3.5 增加测试，证明被硬删除的 tenant company 不通过 `business_status` 或 `visibility_status` 表达。

## 4. 本地验证

- [x] 4.1 运行清理命令及受影响发送/群组/公司流程的后端测试子集。
- [x] 4.2 在本地 `clientget` 对 tenant slug `t-019dc238` 运行 dry-run，并记录预览计数。
- [x] 4.3 只有当预览符合预期后，才在本地 `clientget` 执行清理。用户确认本地 2 个 `muzi` 候选均为手工测试数据后，已通过显式候选 ID `1147,1148` 执行。
- [x] 4.4 清理后验证本地 tenant company、group、sending plan、dashboard、发送计划创建流程。

## 5. 证据与交接

- [x] 5.1 仅在本 change 进入执行阶段后，将 dry-run 与删除后核验输出记录到 `_control/evidence/`。
- [x] 5.2 记录剩余生产手工执行步骤，包括所需备份/快照确认。
