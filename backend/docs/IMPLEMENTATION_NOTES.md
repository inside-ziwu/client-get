# Implementation Notes

## Scoring jobs

- `scoring_jobs` 仅用于 worker 协调，不复制评分业务真相。
- `trigger(mode=inline)` 保留同步兼容；`trigger(mode=enqueue)`、`claim`、`submit-result` 走队列合同。
- 租户余额账本已移除；LLM 维度在 OpenRouter 未配置、余额不足或状态未知时会标记为 `pending`，不会再进入“充值后重试”的分支。

## Sending integration

- `EngageLabClient` 使用可配置 `base_url + send_path + auth header/scheme` 发送。
- worker 通过 `claim_due_emails -> provider send -> mark_email_sent/mark_email_failed` 串联现有发送主链。
- webhook 继续作为最终状态回写真源。

## Sanitization

- 平台模板、租户模板、AI 生成模板以及发送渲染内容都经过 allowlist sanitizer。
- `subject` 和 `body_text` 视为纯文本，`body_html` 允许有限标签与属性。

## Pagination

- `/emails` 使用 `created_at DESC, id DESC` 的稳定 cursor 分页。
- cursor 编码内容固定为 `created_at + id`。

## Auth writebacks

- 登录成功与失败计数使用独立事务记录，避免在返回 401/423 时被请求事务回滚。
