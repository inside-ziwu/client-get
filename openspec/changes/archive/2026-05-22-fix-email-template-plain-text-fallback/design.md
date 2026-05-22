## Context

当前 Admin 与 Tenant 邮件模板页都使用 shared-ui 的 TipTap 富文本编辑器。编辑器会同时产出 `body_html` 与 `body_text`，Tenant 端保存时提交了两个字段，但 Admin 端平台模板保存只提交 `body_html`，导致平台模板的 `body_text` 可能为空。发送链路在 `claim_due_emails` 中从模板渲染并写入 queued email，随后 worker 把 queued email 内容传给 EngageLab；该链路目前对空 `body_text` 没有 fallback。线上已经存在的模板记录也可能缺失 `body_text`，仅靠代码兜底不能修复数据质量本身。

这个 change 同时触及 Admin 前端、后端 sending worker 入口和一次性数据修复脚本，属于跨模块修复；但不需要 schema 迁移，也不需要改变外部 provider 协议。线上数据修复属于生产副作用，必须由用户显式触发。

## Goals / Non-Goals

**Goals:**

- Admin 端平台邮件模板保存 payload 与 Tenant 端一致，包含 `body_html`、`body_text`、`body_design: null`。
- 发送入队时保证 `body_text` 为空的 HTML 模板也能产生可读纯文本。
- 提供可 dry-run 的存量模板回填脚本，修复线上 `platform_email_templates` 和 `email_templates` 中缺失的 `body_text`。
- HTML 转纯文本逻辑进入正式后端工具模块，并通过单元测试固定换行行为。

**Non-Goals:**

- 不新增纯文本编辑 UI。
- 不修改 EngageLab API 封装的请求结构。
- 不扩大到平台模板同步能力或其它发送策略调整。
- 不在普通实施过程中自动连接或修改线上数据库；执行线上回填必须另行获得用户明确确认。
- 不回填 `emails` 表中已生成的测试邮件记录；当前线上尚未正式运营，历史邮件数据可忽略。

## Decisions

### Decision 1: Admin 端直接复用编辑器输出的 body_text

Admin 页面已经在 `EmailRichEditor.onUpdate` 中拿到 `text`，只需把状态变量从未使用状态改为正式 `bodyText`，并加入 create/update payload。

替代方案：在后端 Admin create/update 接口收到缺失 `body_text` 时从 `body_html` 生成。暂不采用，因为前端编辑器已有准确纯文本输出，Admin 与 Tenant 行为一致更简单，也能满足既有 `richtext-email-editor` 规格。

### Decision 2: fallback 放在邮件入队渲染阶段

`tenant_messaging_service.claim_due_emails` 已经负责把模板变量渲染成具体邮件内容，并写入 `emails` 表。fallback 在这里执行，可以保证 queued email、worker payload、provider payload 三者看到同一份 `body_text`。

替代方案：在 EngageLab client 的 `_build_request_body` 中 fallback。暂不采用，因为 provider 层只应负责通道请求，不应承担模板语义；并且 queued email 中仍会保留空纯文本，影响审计和后续排查。

### Decision 3: HTML 转纯文本工具不从 scripts 目录复用

`backend/scripts/migrate_email_templates_html.py` 已有一次性迁移用的 `text_from_html()`，但生产代码不应 import 迁移脚本。实现时将提取逻辑放入正式 util 模块，例如 `backend/app/utils/email_text.py`，迁移脚本可保持不动。

替代方案：把迁移脚本函数移动到 util 并修改脚本 import。可行，但会扩大改动面；本次让生产发送链路、数据修复脚本和测试使用正式 util。

### Decision 4: 数据修复用脚本执行，不用 Alembic schema 迁移

存量问题是内容字段缺失，不是 schema 演进。实现时提供一个显式脚本，例如 `backend/scripts/backfill_email_template_body_text.py`，默认 dry-run，只有传入明确执行参数时才更新 `platform_email_templates` 与 `email_templates`。

替代方案：写 Alembic 数据迁移自动执行。暂不采用，因为线上数据修复需要可预览、可控触发；自动随部署执行会把生产副作用隐藏在 schema 升级里。

### Decision 5: 不修复已生成的 emails 测试记录

当前线上尚未正式运营，`emails` 表中的历史记录均可视为测试数据。修复重点放在模板源数据和未来发送链路：模板回填修复未来复制/编辑的基础数据，发送 fallback 兜住遗漏模板。

替代方案：同时回填 `emails` 表中 queued/failed 等未发送记录。暂不采用，因为会扩大数据修复范围，且当前业务前提下收益很低。

## Risks / Trade-offs

- [Risk] HTML 提取纯文本可能与编辑器原生 `getText()` 的空白细节略有差异 → Mitigation: 只在 `body_text` 缺失时使用 fallback；已有 `body_text` 永远优先。
- [Risk] 提取逻辑处理复杂邮件 HTML 时不完整 → Mitigation: 目标是可读纯文本兜底，不追求像浏览器一样完整渲染；覆盖段落、换行、列表、HTML 标签剥离即可。
- [Risk] Admin 前端测试如果只做静态契约，可能漏掉真实编辑器回调 → Mitigation: 至少增加 payload 包含 `body_text` 的契约断言；必要时补组件级测试。
- [Risk] 线上回填误覆盖人工维护的纯文本 → Mitigation: 脚本只更新 NULL、空字符串或仅空白的 `body_text`，非空值绝不覆盖。
- [Risk] 线上回填属于生产副作用 → Mitigation: 默认 dry-run，输出统计；正式执行必须由用户显式触发，并记录执行命令与结果。

## Migration Plan

1. 发布前或发布后先运行回填脚本 dry-run，确认 `platform_email_templates` 与 `email_templates` 待修复数量。
2. 用户明确确认后，在目标环境执行回填脚本正式模式，只更新缺失 `body_text` 的模板记录。
3. 发布后新建或编辑的 Admin 平台模板会保存 `body_text`。
4. 即使个别存量记录未回填，发送时 fallback 仍会生成纯文本，避免发送空 `text/plain`。
5. 回滚代码时移除前端 payload 字段和后端 fallback 即可；数据回填只填充原本缺失的 `body_text`，通常不需要回滚。如需回滚数据，只能基于执行前备份或 dry-run 记录人工处理。

## Open Questions

无。
