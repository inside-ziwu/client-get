## 1. 后端纯文本 fallback

- [x] 1.1 新增正式 HTML 转纯文本工具模块，支持段落、`<br>`、列表项等常见邮件 HTML 的可读换行，并剥离 HTML 标签。
- [x] 1.2 为 HTML 转纯文本工具增加单元测试，覆盖段落换行、`<br>`、列表项、空 HTML、HTML 实体解码。
- [x] 1.3 修改 `tenant_messaging_service.claim_due_emails`：模板 `body_text` 为空或空白时，从渲染后的 `body_html` 生成 fallback，再执行现有纯文本清洗。
- [x] 1.4 增加后端发送链路测试：缺失 `body_text` 时 queued email 与 provider payload 使用 fallback 文本。
- [x] 1.5 增加后端发送链路测试：已有非空 `body_text` 时优先使用模板纯文本，不被 HTML fallback 覆盖。

## 2. 存量数据回填脚本

- [x] 2.1 新增可 dry-run 的回填脚本，扫描 `platform_email_templates` 与 `email_templates` 中 `body_text` 缺失且 `body_html` 可提取文本的记录。
- [x] 2.2 脚本默认 dry-run，只输出每张表待回填、可回填、跳过数量，不更新数据库。
- [x] 2.3 脚本执行模式只更新 NULL、空字符串或仅空白的 `body_text`，绝不覆盖已有非空纯文本。
- [x] 2.4 为回填脚本增加测试或可重复的本地验证，覆盖 dry-run 不写库、执行模式写库、已有 `body_text` 不覆盖、无可提取文本跳过。
- [x] 2.5 在实施记录中保留本地 dry-run 输出摘要；线上 dry-run 与正式执行必须等待用户明确触发。

## 3. Admin 前端保存 body_text

- [x] 3.1 修改 Admin 平台邮件模板页面，将编辑器输出的 `bodyText` 作为正式状态变量保存。
- [x] 3.2 修改 Admin 平台邮件模板 create/update payload，加入 `body_text: bodyText`，并继续传 `body_design: null`。
- [x] 3.3 增加或更新 Admin 前端契约测试，断言邮件模板保存逻辑包含 `body_text` 字段。
- [x] 3.4 快速核对 Tenant 端保存逻辑保持不变，避免引入双端行为差异。

## 4. 验证

- [x] 4.1 运行匹配的后端测试，至少覆盖 HTML 转纯文本工具、发送 fallback 与回填脚本。
- [x] 4.2 运行匹配的 Admin 前端测试或 lint，覆盖平台邮件模板页面 payload 契约。
- [x] 4.3 手工或测试记录一条验收：Admin 保存富文本平台模板后，请求 payload 含 `body_html`、`body_text`、`body_design: null`。
- [x] 4.4 手工或测试记录一条验收：`body_text` 为空的 HTML 模板入队后 queued email 的 `body_text` 非空且无 HTML 标签。
- [x] 4.5 手工或测试记录一条验收：回填脚本 dry-run 不写库，正式模式只更新缺失 `body_text` 的模板。

## 5. 线上数据修复与收尾

- [x] 5.1 确认本 change 未新增 schema 迁移、未修改 EngageLab 请求结构、未影响 `sync-platform-email-templates` change 范围。
- [x] 5.2 记录线上 dry-run 命令与输出摘要；若用户未授权线上操作，明确标注未执行原因。
- [x] 5.3 若用户明确授权，则执行线上模板回填，并记录正式执行命令、更新时间、每张表更新数量；未授权时记录“线上正式回填未执行”，不阻塞代码修复完成。
- [x] 5.4 更新本 `tasks.md` 勾选状态，明确任何未完成项和原因。
- [x] 5.5 调用 `verification-before-completion` skill，并输出“原始需求 → 已实现/未实现”对照。

## 执行记录

- 本地 dry-run：`cd backend && .venv/bin/python scripts/backfill_email_template_body_text.py`
- 本地 dry-run 输出：`database_name=clientget`，`user_name=postgres`，`platform_email_templates total=36 missing_body_text=36 backfillable=36 updated=0`，`email_templates total=587 missing_body_text=587 backfillable=587 updated=0`。
- 线上 dry-run：未执行，原因是用户尚未明确授权线上生产副作用。
- 线上正式回填：未执行，原因是用户尚未明确授权线上生产副作用；不阻塞代码修复完成。
