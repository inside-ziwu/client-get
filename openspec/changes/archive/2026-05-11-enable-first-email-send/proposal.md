## Why

当前 V3 邮件投递目标被完整链路范围拖住，但业务此刻最关键的验收是“第一封真实邮件能发出去”。前期探索确认：发送计划启动链路已经能生成待发 enrollment，主要风险集中在 EngageLab 请求适配器格式、真实凭证配置、已验证域名和 sending worker 拨测闭环。

## What Changes

- 将本次实施收敛为“首封真实邮件拨测”最小闭环：已验证域名 + 单测试收件人 + 单步骤发送计划 + sending worker 跑一次 + EngageLab 返回 message id。
- 调整 EngageLab 发送适配器，使请求格式继承 `aoqi-ai/sysdev-ft-marketing` 的真实适配器：HTTP Basic Auth，`from` / `to` / `body.content` / `body.settings` 结构，开启 `open_tracking`。
- 明确 EngageLab 凭证映射：原项目 `mail.engagelab_api_user` 对应 `ENGAGELAB_API_USER`，`mail.engagelab_api_key` 对应 `ENGAGELAB_CREDENTIAL`；凭证只进入环境变量或 Secret，不写入代码或文档。
- 增加首封拨测所需的诊断验证：worker 单次运行、`emails.status`、`engagelab_message_id`、失败错误落库、测试收件箱人工验收。
- 首封拨测验收口径采用“测试收件箱真实收到邮件”：`emails.status='sent'` 与 `engagelab_message_id` 非空只是中间证据，不单独视为通过。
- 使用 `aoqi@xapcb.com` 作为发件邮箱、`aip.lazy@gmail.com` 作为首封拨测收件箱；实施前必须确认 `aoqi@xapcb.com` 所属域名在当前租户 `domain_warmup_status` 中为 `verified` 且有可用日限额。
- 不扩大到完整域名验证 UI、webhook 全量回写、监控大屏、多轮序列优化、时区窗口或正式上线发布。

## Capabilities

### New Capabilities

- `first-email-send`: 首封真实邮件拨测闭环，覆盖 EngageLab 请求适配器、配置门槛、单封 worker 投递和验收记录。

### Modified Capabilities

- `tenant-sending-plan-creation`: 明确已创建发送计划进入真实发送前的启动/锁定诊断边界，不改变创建契约。
- `admin-domain-warmup-level`: 明确首封拨测依赖一个已验证且有日限额的租户发件域名，不改变 warmup level 创建规则。

## Impact

- 后端：`backend/app/integrations/engagelab.py`、`backend/app/workers/sending.py`、`backend/app/core/config.py`、相关测试。
- 运维配置：Sealos/backend/sending-worker 环境变量或 Secret 中的 EngageLab API_USER、credential、发送 URL/path；本 change 实施阶段只更新非密钥文档/示例和本地或测试环境配置，生产 Sealos Secret 变更必须由用户单独确认。
- 数据库：优先不新增迁移；使用现有 `domain_warmup_status`、`sending_plans`、`sequence_enrollments`、`email_send_locks`、`emails`。
- 验收：需要一个真实 verified 发件域名、一个测试收件邮箱、一次 sending worker 单次运行和收件箱确认。
- 首封拨测数据：发件邮箱 `aoqi@xapcb.com`，收件邮箱 `aip.lazy@gmail.com`；不得在文档中记录真实 EngageLab key。
- 外部服务：会在实施验收阶段真实调用 EngageLab 发出 1 封测试邮件；正式批量发送、镜像推送、线上发布仍需用户明确触发。
