## Context

当前租户端发送计划新建页由前端编排多次请求：

1. `POST /api/v1/sending-plans` 创建草稿计划。
2. `POST /api/v1/sending-plans/{id}/steps` 创建首封步骤。
3. 为序列步骤重复调用创建步骤接口。
4. 在“创建并锁定收件人”模式下，再调用预览与锁定收件人接口。

这个流程的问题是失败边界分散：后端创建计划时直接读取 `payload["name"]`、`payload["recipient_source"]` 等字段，缺少统一业务校验；前端任一后续请求失败后只能显示泛化错误，且已创建的草稿不会自动回滚。对运营用户而言，结果就是“创建发送计划失败”但不知道是模板、域名、收件人分组还是接口状态导致。

本 change 聚焦创建可靠性，不改变发送 worker、真实投递、域名接入和监控事件。

## Goals / Non-Goals

**Goals:**

- 让发送计划创建成为一个可验证、可诊断、不会产生半成品的闭环。
- 在后端集中校验创建所需的计划字段、步骤字段、模板归属、域名归属/验证边界与收件人来源。
- 支持前端一次提交完整创建 payload，包括首封步骤、序列步骤和是否锁定收件人。
- 失败时返回明确的业务错误，前端直接展示可行动的错误信息。
- 保持既有列表、详情、步骤管理、启动等接口兼容。

**Non-Goals:**

- 不实现真实邮件投递、EngageLab 事件回写、worker 部署或 Sealos 发布。
- 不重做发送计划 UI 信息架构。
- 不迁移历史发送计划数据。
- 不改变 `tenant_companies.business_status` 的现有阶段定义。

## Decisions

### 1. 新增组合创建入口，保留既有低层接口

新增一个面向新建页的组合创建 API，例如 `POST /api/v1/sending-plans/create-with-steps`，由服务层一次接收：

- `plan`: 名称、描述、收件人来源、发件人、域名、发送策略。
- `steps`: 至少一个步骤，第一步必须是 `step_number=1`、`delay_days=0`、`condition_type=always`。
- `lock_recipients`: 是否在创建成功后立即锁定收件人。

服务层在同一个请求生命周期内完成校验、插入计划、插入步骤、可选锁定收件人与审计记录。既有 `create_sending_plan`、`create_plan_step` 等接口继续保留给详情页编辑或内部流程使用。

备选方案是只在前端失败后删除草稿。这个方案不能解决后端输入校验分散，也会让恢复逻辑依赖多次网络请求，因此不作为主路径。

### 2. 后端先校验，后写入

创建前先完成以下校验：

- `name`、`recipient_source`、`recipient_config`、`sender_name`、`sender_email`、`domain_id` 必须满足创建要求。
- `domain_id` 必须属于当前租户；未验证域名允许保存草稿，但 `lock_recipients=true` 时必须拒绝。
- 每个步骤的 `template_id` 必须属于当前租户。
- 步骤编号不得重复，且必须从 1 开始连续。
- 当 `recipient_source=group` 时，`recipient_config.group_id` 必须存在并属于当前租户。
- 当 `lock_recipients=true` 时，发件域名必须已验证，且可锁定收件人必须大于 0；否则返回明确错误并回滚整个创建请求。

校验失败统一抛出 `AppError(code="VALIDATION_ERROR", status_code=422, message="<具体原因>")`，避免 KeyError、数据库约束错误或前端泛化错误成为用户看到的主反馈。

### 3. 创建流程使用同一数据库事务语义

FastAPI 当前通过 tenant auth context 注入 connection。实现时应确认该 connection 的请求事务边界；若框架已在异常时回滚，则组合服务方法只需要在异常前不提交。若没有自动事务边界，组合创建方法必须显式使用事务，确保步骤或锁定失败时计划插入也回滚。

不通过软删除补偿来伪造原子性，因为补偿会留下审计噪音和用户不可见数据。

### 4. 前端提交完整 payload 并显示服务端错误

`SendPlans/New.tsx` 改为：

- 在提交前校验序列步骤都已选择模板。
- 调用组合创建 API，而不是在页面组件内编排多次创建请求。
- 成功后沿用现有跳转、缓存失效与成功提示。
- 失败时优先展示响应中的业务 `message`，没有业务 message 时再使用兜底文案。

共享 API 包增加组合创建 payload 类型与方法，避免页面内继续使用松散 `Partial<SendingPlan>` 拼装关键字段。

## Risks / Trade-offs

- [Risk] 现有请求事务边界不清，组合方法异常后仍可能留下数据。→ 实施第一步确认 tenant DB session/connection 的提交与回滚机制，并用测试覆盖“步骤失败不留下计划”。
- [Risk] 新增组合 API 与既有 API 并存，短期有两条创建路径。→ 新建页只使用组合 API；既有 API 暂保留兼容详情页编辑与脚本，后续可单独提 change 收敛。
- [Risk] `lock_recipients=true` 时收件人预览依赖较多表数据，可能暴露原先隐藏的数据质量问题。→ 可锁定收件人为 0 时直接失败并提示“该分组没有可发送收件人”，不在本 change 中自动修复数据。
- [Risk] 未验证域名草稿可保存，用户可能误以为计划已可发送。→ 创建页和后端只允许保存草稿；锁定收件人和启动计划前必须返回明确的域名未验证错误。

## Migration Plan

- 不需要数据库迁移。
- 部署后新建页走组合创建 API；已有草稿计划不做批量变更。
- 如出现回退，需要前端恢复调用既有多请求流程，后端新增 API 可保留不影响旧接口。

## Open Questions

- 无。
