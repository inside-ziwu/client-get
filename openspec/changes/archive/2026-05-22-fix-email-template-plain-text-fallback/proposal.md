## Why

富文本邮件模板已经切到单一 TipTap 编辑器，但 Admin 端保存平台模板时没有提交 `body_text`，导致由平台模板复制或发送的邮件缺少 `text/plain` 内容。邮件发送链路也没有在 `body_text` 为空时从 `body_html` 生成兜底纯文本，纯文本客户端、企业邮箱安全网关或反垃圾系统读取纯文本部分时可能得到空内容。

## What Changes

- Admin 端平台邮件模板保存时提交富文本编辑器输出的 `body_text`，与 Tenant 端行为一致。
- 后端邮件入队发送时，当模板 `body_text` 为空时，从已渲染的 `body_html` 提取纯文本作为 fallback。
- 提供一次性存量模板修复脚本/命令，支持 dry-run，回填线上 `platform_email_templates` 与 `email_templates` 中缺失的 `body_text`。
- 将 HTML 提取纯文本逻辑放入正式后端工具模块，供发送链路和测试复用；迁移脚本中的同类逻辑仅作为参考，不作为生产 import 来源。
- 增加覆盖 Admin payload、发送 fallback、存量模板回填的验证，确保换行类 HTML 标签能转换为可读纯文本。

## Non-Goals

- 不恢复或新增纯文本编辑模式，前端仍保持单一富文本编辑器。
- 不改变 EngageLab provider API 结构，只保证传入 provider 的 `text` 字段不因模板缺失 `body_text` 而为空。
- 不改变平台模板同步能力，不合并到 `sync-platform-email-templates` change。
- 不新增数据库表、字段或索引。
- 不自动执行线上修复；线上数据修复必须由用户显式触发。
- 不回填 `emails` 表中已生成的测试邮件记录；当前线上尚未正式运营，历史邮件数据可忽略，后续发送由模板回填和发送 fallback 覆盖。

## Capabilities

### New Capabilities

- `email-plain-text-fallback`: 邮件发送链路在模板缺失纯文本时，从 HTML 自动生成可读 `text/plain` 内容。
- `email-template-plain-text-backfill`: 存量平台与租户邮件模板缺失 `body_text` 时，可通过受控脚本从 `body_html` 回填。

### Modified Capabilities

- `richtext-email-editor`: Admin 端平台邮件模板保存必须与 Tenant 端一样提交编辑器输出的 `body_text`。

## Impact

| 路径 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx` | 修改 | 保存平台邮件模板时将编辑器输出的 `body_text` 放入 create/update payload |
| `frontend/apps/admin/test/` | 修改 | 增加或补强 Admin 邮件模板页保存 payload 契约测试 |
| `backend/app/services/tenant_messaging_service.py` | 修改 | 邮件入队时 `body_text` 为空则从 `body_html` 生成 fallback |
| `backend/app/utils/` 或等价正式工具模块 | 修改/新增 | 提供 HTML 转纯文本工具，避免从 `backend/scripts/` 引用迁移脚本 |
| `backend/scripts/` | 修改/新增 | 提供可 dry-run 的存量模板 `body_text` 回填脚本 |
| `backend/tests/` | 修改 | 覆盖 HTML fallback、换行提取、已有 `body_text` 优先等发送链路行为 |

- 数据库：不新增 schema 迁移；新增数据修复脚本，执行时只更新 `platform_email_templates` 与 `email_templates` 中 `body_text` 为空且 `body_html` 可提取文本的模板记录，不处理 `emails` 历史记录。
- API：不新增接口；Admin create/update payload 补齐既有可选字段 `body_text`。
- 外部服务：不改变 EngageLab 调用结构，只改善 `text` 字段内容。
- 前后端依赖顺序：先实现并测试后端兜底工具，再实现 dry-run 数据修复脚本，随后补 Admin 保存 payload 与前端契约测试。
- `_control/` 决策编号与能力域：当前仓库未发现 `_control/` 目录；本 change 暂无可关联 D-xxx / C-xxx。
