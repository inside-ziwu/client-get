## Why

平台 admin 管理的采集凭证源失效属于平台侧/管理侧运维问题，不应打扰 tenant 用户或造成 tenant 误判自身业务配置异常。现在需要明确通知边界，避免 `CREDENTIAL_EXPIRED` 事件被错误下发给 tenant。

## What Changes

- 当平台 admin 管理的采集凭证源以 `CREDENTIAL_EXPIRED` 失败时，系统不得创建任何 tenant 可见通知；tenant admin 也属于 tenant 用户，不应收到该通知。
- 采集凭证源失效事件仍应保留既有采集任务失败状态与错误信息，供平台 admin 在 admin 后台排查。
- 明确该事件的可见性边界：平台 admin 可通过既有 admin 采集任务入口查看；tenant 用户、tenant admin 与 tenant 通知中心不可见。
- 不改变 tenant 自有配置异常、tenant 发起任务失败等 tenant 责任域事件的通知规则。

## Capabilities

### New Capabilities

- `credential-source-expiry-notification-boundary`: 约束平台 admin 采集凭证源 `CREDENTIAL_EXPIRED` 事件的 tenant 可见性边界。

### Modified Capabilities

无。

## Impact

- 影响后端采集任务失败处理与 tenant 通知写入逻辑。
- 不新增或改造平台 admin 告警渠道、admin UI 或外部通知。
- 不应新增外部依赖，不应改变 tenant API 的业务语义。
