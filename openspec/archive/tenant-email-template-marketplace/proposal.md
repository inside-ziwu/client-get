## Summary

重做 Tenant 端邮件模板页面，废弃 Admin 推送同步机制，改为「模板市场」模式——租户从平台模板库自主浏览挑选。页面分「平台模板库」和「我的模板」两个 Tab，支持 GrapesJS 可视化编辑器和简单版 AI 生成。

## Why

Tenant 端邮件模板页面当前仅 72 行（`frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`），只有最基础的内联创建表单 + 列表展示。而后端 API（CRUD / clone / preview / ai-generate）和前端 API 层（`frontend/packages/shared-api/src/tenant/email-templates.ts`）均已齐备，Admin 端也有完整的 GrapesJS 可视化编辑器，设计 mock（`docs/mock/tenant-templates.html`）早已画好——前端页面从未真正实现过。

同时，现有的 Admin「同步到租户」机制（`POST /email-templates/{id}/sync`）与租户端模板管理存在语义冲突：同步已在 `email_templates` 表中创建副本，再要求租户「只读 + 复制」会产生冗余的双层副本。改为模板市场模式后，租户主动挑选，数据流更清晰。

## What Changes

### Tenant 前端

- **页面重写**：`frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx` 全面重做
- **双 Tab 布局**：
  - 「平台模板库」Tab：展示 `platform_email_templates` 中匹配租户行业的模板（只读），操作：预览 + 复制到我的模板
  - 「我的模板」Tab：展示租户自己的 `email_templates`，操作：预览 / 编辑 / 复制 / 删除
- **Drawer 编辑器**：侧滑抽屉式编辑，包含名称、分类、主题、变量 chips、正文编辑
- **GrapesJS 可视化编辑器**：复用 Admin 端组件（`frontend/apps/admin/src/components/grapes-email-editor.tsx`），提取到共享包或在 Tenant 端引入，支持可视化 / HTML 源码 / 纯文本三种编辑模式
- **AI 生成模板**：弹窗表单（名称、分类、公司描述、生成要求、主题偏好），生成后结果直接进入编辑器供用户微调
- **预览 Modal**：变量替换后的真实邮件预览

### Tenant 后端

- **新增 API**：Tenant 端浏览平台模板库的接口（按租户行业筛选 `platform_email_templates`）
- **新增 API**：Tenant 端从平台模板库复制模板的接口（创建 `email_templates` 记录，`source_type='platform_copy'`）

### 数据库

- **新增列**：`email_templates` 表增加 `body_design jsonb` 列（存储 GrapesJS 设计数据）
- **Alembic 迁移**：一个 revision，新增 `body_design` 列

### Admin 端

- **废弃同步功能**：移除 Admin 邮件模板列表的「同步到租户」按钮
- **废弃同步 API**：移除或标记废弃 `POST /admin/api/v1/email-templates/{template_id}/sync`

### 存量数据处理

- 已存在的 `source_type='platform_copy'` 记录归入「我的模板」，租户可继续编辑使用
- 不做数据清理或迁移，仅调整前端展示逻辑

## Key Decisions

- **模板市场替代推送同步**：租户主动挑选而非被动接收。原因：同步副本 + 只读复制产生冗余双层副本，模板市场语义更清晰。代价：废弃刚完成的 sync 功能。
- **平台模板只读**：租户不能直接编辑平台模板，想用必须先复制到自己的模板列表。原因：保持平台模板的权威性和一致性。
- **AI 生成用简单表单**：不暴露后端支持的全部参数（tone / language / purpose 等），只用 mock 中的基础字段。原因：降低用户认知负担，后续按需增强。
- **存量 platform_copy 记录保留**：不清理，归入「我的模板」。原因：用户可能已在发送计划中使用这些模板。

## Non-Goals

- 不做模板列表的使用统计（发送数、打开率等，留在邮件监控页）
- 不做模板搜索、筛选、标签等高级管理能力
- 不做 AI 生成的高级参数（tone / language / purpose）
- 不做模板与发送计划的关联体验优化
- 不做模板版本管理或变更历史
- 不做平台模板更新后的通知或差异对比

## Capabilities

### New Capabilities

- `tenant-email-template-marketplace`：Tenant 端完整的邮件模板管理 + 平台模板市场浏览与复制
- `tenant-grapes-editor`：Tenant 端 GrapesJS 可视化邮件编辑器

### Modified Capabilities

- `platform-email-template-sync`：废弃 Admin 端推送同步能力

## Impact

| 路径 | 变更类型 | 说明 |
|------|----------|------|
| `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx` | 重写 | 全面重做模板管理页面 |
| `frontend/apps/admin/src/components/grapes-email-editor.tsx` | 提取/复用 | 移至共享包或 Tenant 端引入 |
| `frontend/packages/shared-api/src/tenant/email-templates.ts` | 修改 | 新增浏览平台模板、复制平台模板的 API 封装 |
| `backend/app/api/tenant/messaging.py` | 修改 | 新增浏览/复制平台模板的路由 |
| `backend/app/services/tenant_messaging_service.py` | 修改 | 新增浏览/复制平台模板的业务逻辑 |
| `backend/app/api/admin/config.py` | 修改 | 移除同步接口 |
| `backend/app/services/admin_config_service.py` | 修改 | 移除同步逻辑 |
| `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx` | 修改 | 移除同步按钮 |
| `frontend/packages/shared-api/src/admin/email-templates.ts` | 修改 | 移除 sync 方法 |
| `backend/alembic/versions/` | 新增 | email_templates 表增加 body_design 列 |

- 数据库：新增 `body_design` 列（jsonb），一个 Alembic revision
- API：新增 Tenant 浏览/复制平台模板接口；废弃 Admin 同步接口
- 前后端依赖顺序：先 migration → 后端 API → shared-api → Tenant 前端 → Admin 废弃清理
- `_control/` 决策编号与能力域：当前仓库未发现 `_control/` 目录；本 change 暂无可关联 D-xxx / C-xxx

## Dependencies / Assumptions

- Admin 端 GrapesJS 组件（`grapes-email-editor.tsx`）可被提取到共享包或在 Tenant 端复用
- `platform_email_templates` 表已有 `body_design` 列（迁移 `20260423_0006` 已添加）
- 租户行业信息可从 `tenants` 表获取，用于筛选平台模板库
- 已有 `source_type='platform_copy'` 的记录未在发送计划中大量使用（若有，归入「我的模板」不影响使用）

## Outstanding Questions

### Deferred to Planning

- [Affects GrapesJS 复用][Technical] GrapesJS 编辑器组件是提取到 `frontend/packages/` 共享包，还是直接在 Tenant 端新建副本？需评估两种方案的工作量和维护成本
- [Affects 分类管理][Needs research] 模板分类当前是前端硬编码 4 个值（首次触达 / 跟进 / 推广 / 节日问候），后端 `category` 字段是 varchar，是否需要统一为枚举或配置化？
- [Affects 存量数据][Technical] 已存在的 `platform_copy` 记录在「我的模板」Tab 中是否需要特殊标记来源？
