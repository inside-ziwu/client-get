## Why

租户端新建发送计划当前存在失败风险：前端按“创建计划 -> 创建步骤 -> 预览/锁定收件人”多次请求串行提交，后端又直接读取必填字段，任一环节异常都会让用户只看到泛化失败提示，并可能留下没有步骤或没有收件人的半成品草稿。

现在需要先把创建链路收敛成可诊断、可恢复、不会产生脏草稿的最小闭环，保证运营人员可以稳定创建发送计划，并在配置不完整时拿到明确原因。

## What Changes

- 新增发送计划创建的服务端校验：必填字段、收件人来源配置、首封步骤、模板归属、发件域名归属必须在写入前明确校验；未验证域名允许保存草稿，但锁定收件人或启动前必须拦截。
- 新增原子创建入口或等价服务层事务：计划、步骤、可选收件人锁定必须整体成功或整体失败，避免失败后留下不可用草稿。
- 调整租户端新建发送计划页面：提交前做必要校验，提交时调用稳定创建流程，失败时展示后端返回的具体错误信息。
- 保留现有发送计划列表、详情、启动、暂停、恢复、取消等既有能力，不扩大到真实邮件投递、EngageLab 事件回写或 worker 部署。
- 增加后端与前端验证覆盖，确保创建成功、配置缺失、步骤创建失败、锁定收件人失败等场景行为清晰。

## Capabilities

### New Capabilities

- `tenant-sending-plan-creation`: 租户端发送计划创建流程的输入校验、原子写入、错误反馈与最小验收契约。

### Modified Capabilities

- `tenant-company-status-semantics`: 明确创建草稿发送计划本身不得改变公司运营阶段，只有收件人锁定或进入计划的既有链路才可触发 `in_plan` 语义。

## Impact

- 后端：`backend/app/api/tenant/messaging.py`、`backend/app/services/tenant_messaging_service.py`，以及相关测试。
- 前端：`frontend/apps/tenant/src/pages/SendPlans/New.tsx`、`frontend/packages/shared-api/src/tenant/sending-plans.ts`，以及相关表单/请求错误处理。
- 数据库：优先不新增表和迁移；若实现时发现必须依赖约束补齐，应先更新本 change 的 design/tasks 再实施。
- 外部服务：不触发正式发信、不推送镜像、不改 EngageLab 或 Sealos 配置。
