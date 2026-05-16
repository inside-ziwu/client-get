## Context

采集 worker 在 provider 抛出 `CredentialExpiredError` 后，会以 `CREDENTIAL_EXPIRED` 调用 `CollectionService.mark_failed()`。当前任务进入最终失败分支后还会触发 `_notify_credential_expired()`，该方法根据 `collection_task_keywords` 查找 tenant 内 `role='admin'` 的用户，并向 tenant `notifications` 表写入 tenant 可见通知。

本次变更要调整的是可见性边界：采集凭证由平台 admin 维护，凭证过期不属于 tenant 可操作问题，因此不应进入 tenant 的通知中心，也不应通过 tenant 可见的任务错误面暴露原始平台凭证错误。任务失败状态与错误信息仍要保留在平台 admin 可见的采集任务记录中，方便管理侧发现和处理。

## Goals / Non-Goals

**Goals:**

- 阻止平台 admin 采集凭证源 `CREDENTIAL_EXPIRED` 事件写入 tenant 可见的 `notifications`。
- 保留采集任务失败状态与错误信息，确保平台 admin 可通过既有 admin 采集任务入口排查。
- 确认 tenant 可见的 API/UI/通知面不会暴露原始 `CREDENTIAL_EXPIRED` 平台凭证错误。
- 用自动化测试覆盖 `CREDENTIAL_EXPIRED` 不产生 tenant 通知的行为。

**Non-Goals:**

- 不新增新的外部告警渠道。
- 不新增或改造平台 admin 站内信、admin UI 或数据源凭证错误写入链路。
- 不改变 tenant 自身配置问题、发送域名问题、AI key 问题等 tenant 责任域通知。
- 不重构整个通知系统或采集任务状态机。

## Decisions

1. 在采集失败处理路径中抑制 tenant 通知写入。

   `CREDENTIAL_EXPIRED` 仍然作为失败原因保存在平台 admin 可见的 `collection_tasks.error_message`，但不再调用会写入 tenant `notifications` 的逻辑。相比增加“通知接收方过滤器”，直接移除该特定 tenant 通知路径更简单，也更符合本次只修边界错误的目标。

2. 保留任务失败与错误文案。

   worker/provider 层的 `CredentialExpiredError` 不需要改语义；平台 admin 后台仍可通过采集任务状态与错误信息看到问题。相比吞掉异常或把任务标记为成功，失败状态更能反映真实采集能力不可用。

3. 测试以服务层行为为主。

   重点验证 `CollectionService.mark_failed(error_code="CREDENTIAL_EXPIRED")` 在最终失败分支不会新增 `notifications` 记录，同时任务仍进入 failed 并保留错误信息。测试必须构造会触发旧通知路径的前置条件：有效 lease、任务关联 `collection_task_keywords`，以及 active tenant user + `user_roles(role='admin')`。相比端到端 UI 测试，服务层测试能更直接覆盖通知写入边界。

## Risks / Trade-offs

- 凭证过期后 tenant 不再收到提醒，可能降低 tenant 对采集停滞的即时感知。→ 该事件不是 tenant 可处理事项，平台 admin 采集任务状态应承担处理入口。
- 如果未来存在 admin 专属通知表或告警渠道，本次不新增对接。→ 先保持 KISS，后续有明确运维通知需求再建独立 change。
- 旧通知记录不会自动删除。→ 本次只改变新事件行为，不做历史数据迁移，避免误删 tenant 历史通知。

## Migration Plan

- 无数据库迁移。
- 部署后新发生的平台 admin 采集凭证源 `CREDENTIAL_EXPIRED` 事件不再生成 tenant 通知。
- 回滚方式：恢复原有 `CREDENTIAL_EXPIRED` 通知调用逻辑即可。

## Open Questions

无。
