## Context

`v3-email-delivery` 覆盖完整邮件投递链路，但当前最紧急目标是首封真实邮件拨测。现有后端发送链路已具备基础结构：

- 发送计划启动后创建 `sequence_enrollments`。
- `SendingWorker.run_once()` 调 `claim_due_emails()` 领取到期邮件，写入 `emails.status='queued'`。
- worker 调 `EngageLabClient.send_email()`，成功后写 `emails.status='sent'` 与 `engagelab_message_id`，失败后写 `error_code` / `error_message`。

探索中确认原项目 `aoqi-ai/sysdev-ft-marketing` 的 EngageLab 适配器使用 HTTP Basic Auth，且请求体为 `from` / `to` / `body.content` / `body.settings` 结构。当前项目已实现 Basic Auth，但请求体仍是 `from_email` / `to_email` / `body_html` 扁平结构，存在真实 provider 不接受的风险。

重新调研原项目后确认：`flows/utils/engagelab.py` 返回配置时读取 `mail.engagelab_api_url` / `ENGAGELAB_API_URL`，但 SQL 只查询了 `mail.engagelab_api_user`、`mail.engagelab_api_key`、`mail.engagelab_sender`；原项目环境说明只明确 EngageLab Email stats API base 为 `https://email.api.engagelab.cc`，没有给出 send URL 的数据库 key。因此本 change 不能假设能从原项目 `system_config.mail.engagelab_api_url` 取得完整发送 URL，实施时必须显式配置当前项目的 `ENGAGELAB_BASE_URL` 与 `ENGAGELAB_SEND_PATH`。

## Goals / Non-Goals

**Goals:**

- 让一个已验证发件域名通过 EngageLab 成功发出 1 封测试邮件。
- 首封拨测使用发件邮箱 `aoqi@xapcb.com`，收件邮箱 `aip.lazy@gmail.com`。
- 对齐原项目 EngageLab 请求适配器格式，保留当前 worker 的内部 payload 接口。
- 使用环境变量或 Secret 注入 EngageLab 凭证，不把真实 key 写入仓库。
- 为失败路径提供可诊断错误：provider status、响应体摘要、email 错误字段。
- 用最小测试和一次真实拨测证明链路可用。

**Non-Goals:**

- 不实现 EngageLab Domain API 的新增域名、DNS 记录生成和自动验证。
- 不实现完整 webhook 回写、退信分级、监控大屏增强。
- 不实现时区窗口、批量发送策略、多轮序列优化。
- 不自动推送镜像、不修改生产配置、不批量触发发送；生产 Sealos Secret 变更必须由用户单独确认。
- 不在文档或代码中保存真实 EngageLab key。

## Decisions

### 1. EngageLab adapter 对外请求继承原项目格式

实施时保留当前 worker 调用 `send_email(payload)` 的内部字段名，但在 `EngageLabClient` 内转换为 provider 请求体：

```json
{
  "from": "sender@verified-domain.com",
  "to": ["test@example.com"],
  "body": {
    "subject": "subject",
    "content": {
      "html": "<p>body</p>",
      "text": "body"
    },
    "settings": {
      "send_mode": 0,
      "return_email_id": true,
      "open_tracking": true,
      "click_tracking": false,
      "unsubscribe_tracking": false
    }
  }
}
```

理由：原项目已被用户确认是继承来源，且其适配器已包含生产发送经验。保留当前内部 payload 可减少 worker、service 和测试的改动面。

备选方案：让 worker 直接产出 provider 格式。放弃原因是会把外部服务协议泄漏到 worker，后续换 provider 或调整协议时影响更大。

### 2. 凭证使用 `ENGAGELAB_API_USER` + `ENGAGELAB_CREDENTIAL`

`mail.engagelab_api_user` 映射为 `ENGAGELAB_API_USER`，`mail.engagelab_api_key` 映射为 `ENGAGELAB_CREDENTIAL`。适配器继续生成：

```text
Authorization: Basic base64(api_user:credential)
```

理由：与原项目一致，也避免继续使用旧 `ENGAGELAB_API_KEY` Bearer 语义造成混淆。

备选方案：在数据库建 `system_config` 或 `email_providers` 保存凭证。放弃原因是首封拨测不需要新增凭证存储面，Secret 更适合当前最小闭环。

### 3. Send URL/path 由当前项目显式配置

原项目没有可复用的 `mail.engagelab_api_url` 当前值；它只在代码中尝试读取该 key，但没有在 SQL 查询和环境说明中完整落地。因此当前项目实施时必须显式配置：

```text
ENGAGELAB_BASE_URL=https://email.api.engagelab.cc
ENGAGELAB_SEND_PATH=/v1/mail/send
```

如果真实账号区域或 EngageLab 后台文档给出不同地址，以拨测前确认的地址为准，并同步记录到非密钥文档和部署配置。

理由：避免继续沿用当前默认 `/v1/email/send` 或臆造原项目数据库 key，导致 worker 真实调用 404。

备选方案：兼容完整 `ENGAGELAB_API_URL`。可作为后续增强；本次保持当前项目 base URL + path 配置模型，降低改动面。

### 4. 首封拨测复用现有 domain gate

启动计划仍要求 `domain_warmup_status.verification_status='verified'`。如果真实 EngageLab 域名验证尚未通过，本 change 不绕过后端 gate；只允许使用已验证域名做测试。

理由：首封邮件的价值是验证真实生产路径，不应通过手动绕过验证制造假阳性。

备选方案：临时把某个本地域名改成 verified。仅可用于本地 dry run，不可作为真实拨测验收。

### 5. 真实发送只通过 worker 触发

不新增临时“一键发送”API。验收路径为创建计划、启动计划、运行 sending worker `--once --limit 1`。

理由：这正是最终生产链路，能同时验证 enrollment、锁、emails 记录、quota 和 provider 调用。

备选方案：写独立脚本直接调用 EngageLab。可作为诊断 spike，但不能替代产品链路验收。

## Risks / Trade-offs

- EngageLab URL/path 与账号区域不匹配 → 实施前用配置显式记录 base URL/path；失败时落 provider status 和响应体摘要。
- 发件邮箱不属于 verified 域名 → 启动前查询 `sending_plans.sender_email` 与 `domain_warmup_status.domain`，验收只使用匹配邮箱。
- 发件域名日限额为 0 或当日额度耗尽 → 拨测前查询 `domain_warmup_status.daily_limit` 与 `domain_daily_usage`，没有额度则停止并记录 blocker。
- claim 过程中 quota reserve 失败可能发生在 lock 写入之后 → 增加测试或手工验证，确保不会留下阻塞后续重试的 `email_send_locks` 状态；如果现有实现不满足，记录为首封拨测 blocker。
- worker 重试可能重复发送 → 继续依赖 `email_send_locks` 与 provider idempotency key，拨测限制 `--limit 1`。
- 真实 key 泄露 → 不写入仓库；最终部署使用 Secret；聊天中出现过的 key 建议正式上线前轮换。
- 测试邮箱收不到但 provider 返回成功 → 记录为“provider accepted but inbox not received”，并按诊断清单检查 Gmail 垃圾邮件/促销分类、EngageLab 后台事件、provider response、SPF/DKIM/DMARC 状态。

## Migration Plan

1. 修改适配器和测试后先跑单元测试，确认请求体、Basic Auth、返回 message id 解析正确。
2. 在本地或测试环境配置 EngageLab 环境变量，显式配置 base URL/path，使用 mock 或 dry run 验证 worker 可领取 1 封 queued 邮件。
3. 确认 `aoqi@xapcb.com` 的域名在当前租户已 verified 且有可用 quota，收件人为 `aip.lazy@gmail.com`，启动 1 个单步骤计划。
4. 验证 quota reserve 失败路径不会留下阻塞后续重试的锁状态。
5. 执行 `python scripts/run_sending_worker.py --once --limit 1`。
6. 验证 `emails.status='sent'`、`engagelab_message_id` 非空、测试收件箱真实收到邮件；只有收件箱收到才视为首封拨测通过。
7. 若 provider 成功但收件箱未收到，检查 Gmail 垃圾邮件/促销分类、EngageLab 后台事件、provider response、SPF/DKIM/DMARC 状态，并记录为未通过。
8. 若 provider 失败，保留失败 email 记录和 response 摘要，不继续扩大改动范围。

Rollback：如适配器改动导致 provider 全部失败，恢复旧适配器代码并暂停 sending worker；由于本 change 不做迁移，数据库无需回滚。

## Open Questions

- `aoqi@xapcb.com` 在当前测试租户下对应的 `domain_warmup_status` 记录是否已经 `verified`，以及当日 quota 是否可用。
- EngageLab 当前账号是否要求除 `from` / `to` / `body` 外的额外字段；如 provider 返回 4xx，以返回体为准调整适配器。
