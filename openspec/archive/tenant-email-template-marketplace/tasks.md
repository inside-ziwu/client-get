## U1. 数据库迁移

- [ ] 1.1 新增 Alembic 迁移：`email_templates` 表增加 `body_design jsonb` 列（可 NULL，无默认值）
- [ ] 1.2 迁移文件命名：`20260522_xxxx_email_template_body_design.py`
- [ ] 1.3 验证：运行 `alembic upgrade head`，确认列已添加

## U2. 后端：更新现有 CRUD 支持 body_design

- [ ] 2.1 `TenantMessagingService.create_email_template`：INSERT SQL 增加 `body_design` 字段
- [ ] 2.2 `TenantMessagingService.update_email_template`：UPDATE SQL 增加 `body_design = :body_design`（**不用 COALESCE**，直接赋值，支持前端传 null 清空设计数据）
- [ ] 2.3 `TenantMessagingService.get_email_template`：SELECT 增加 `body_design`
- [ ] 2.4 `TenantMessagingService.list_email_templates`：**不增加** `body_design`（列表页不需要设计数据，避免响应体膨胀）
- [ ] 2.5 `TenantMessagingService._serialize_template`：返回字典增加 `"body_design": row["body_design"]`
- [ ] 2.6 `html_sanitizer.py`：扩展白名单加入邮件标签（table/img/style/td/tr/th 等），始终执行清洗（安全审查修正）
- [ ] 2.7 `TenantMessagingService.preview_email_template`：调用 get_email_template，无需独立修改
- [ ] 2.8 验证：手动测试现有 CRUD 接口，确认 body_design 字段正确存取

## U3. 后端：新增平台模板浏览/复制 API

- [ ] 3.1 `TenantMessagingService` 新增 `list_platform_templates(conn, tenant_id)` 方法：
  - 从 `tenants` 表查询当前租户 `industry`
  - 查询 `platform_email_templates WHERE industry = :industry AND is_active = true ORDER BY updated_at DESC`
  - 返回序列化后的平台模板列表
- [ ] 3.2 `TenantMessagingService` 新增 `copy_platform_template(conn, tenant_id, template_id, user_id)` 方法：
  - 查询当前租户 `industry`
  - 从 `platform_email_templates` 获取目标模板（验证 `is_active = true AND industry = :industry`）
  - 调用 `create_email_template`，payload 从平台模板复制所有字段
  - `source_type='platform_copy'`，`platform_template_id` 指向原模板
  - 审计记录
- [ ] 3.5 `TenantService._copy_platform_email_templates`：SELECT 和 INSERT 补齐 `body_design` 字段（修复创建租户时自动复制遗漏 body_design 的问题）
- [ ] 3.3 `backend/app/api/tenant/messaging.py` 新增路由：
  - `GET /platform-templates` → `list_platform_templates`
  - `POST /platform-templates/{template_id}/copy` → `copy_platform_template`
  - 权限：list 用 `get_current_tenant_user`，copy 用 `require_tenant_roles("admin", "operator")`
- [ ] 3.4 验证：手动测试两个新接口，确认按行业筛选和复制逻辑正确

## U4. 共享包：GrapesJS 组件提取

- [ ] 4.1 将 `frontend/apps/admin/src/components/grapes-email-editor.tsx` 移动到 `frontend/packages/shared-ui/src/components/grapes-email-editor.tsx`
- [ ] 4.2 `frontend/packages/shared-ui/package.json` 新增依赖：`grapesjs@^0.22.15`、`grapesjs-preset-newsletter@^1.0.2`
- [ ] 4.3 `frontend/packages/shared-ui/src/index.ts` 增加导出：`GrapesEmailEditor`、`GrapesEmailEditorHandle`
- [ ] 4.4 `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx` 更新导入路径为 `import { GrapesEmailEditor, type GrapesEmailEditorHandle } from '@shared/ui'`
- [ ] 4.5 删除 `frontend/apps/admin/src/components/grapes-email-editor.tsx`
- [ ] 4.6 `frontend/apps/admin/package.json` 移除 `grapesjs` 和 `grapesjs-preset-newsletter` 直接依赖
- [ ] 4.7 运行 `pnpm install`
- [ ] 4.8 验证：Admin 端邮件模板编辑页面 GrapesJS 编辑器正常加载和保存

## U5. 共享包：Tenant API 层扩展

- [ ] 5.1 `frontend/packages/shared-api/src/tenant/email-templates.ts`：
  - `EmailTemplate` 接口增加 `body_design?: unknown`
  - 新增 `PlatformTemplate` 接口
  - `emailTemplatesApi` 增加 `platformList()` 和 `platformCopy(id)` 方法
- [ ] 5.2 `frontend/packages/shared-api/src/admin/email-templates.ts`：
  - 移除 `sync` 方法
  - 移除 `SyncEmailTemplateResult` 类型
- [ ] 5.3 验证：TypeScript 编译通过，无类型错误

## U6. 前端：Tenant 模板页面重写

- [ ] 6.1 重写 `frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`：
  - 双 Tab 布局（平台模板库 / 我的模板）
  - 平台模板库 Tab：DataTable + 预览/复制操作
  - 我的模板 Tab：DataTable + 预览/编辑/复制/删除操作
  - 来源 Badge 标记（platform_copy 显示「平台」）
- [ ] 6.2 实现 Drawer 编辑器：
  - Sheet 组件（760px 宽）
  - 表单字段：名称、分类（Select）、主题
  - 变量 chips（点击复制到剪贴板）
  - 编辑器三种模式 Tab：可视化（GrapesJS）/ HTML 源码（Textarea）/ 纯文本（Textarea）
  - 保存逻辑：根据当前模式取值，创建或更新模板
- [ ] 6.3 实现预览 Modal：
  - Dialog 组件（860px 宽）
  - iframe srcdoc 渲染变量替换后的 HTML（`sandbox="allow-same-origin"` 禁止脚本执行）
  - 变量示例值提示栏
- [ ] 6.4 实现 AI 生成 Modal：
  - Dialog 组件（520px 宽）
  - 表单：名称（可选）、分类、公司描述、生成要求、主题偏好（可选）
  - 提交后调用 `aiGenerate` → 关闭 Modal → 打开 Drawer 填充生成内容
- [ ] 6.5 实现删除确认（AlertDialog）
- [ ] 6.6 `frontend/apps/tenant/package.json`：确认 `@shared/ui` 已包含 GrapesJS 依赖（通过 workspace 传递）
- [ ] 6.7 验证：本地启动 Tenant 端，完整测试以下流程：
  - 平台模板库浏览和预览
  - 复制平台模板到我的模板
  - 新建自有模板（可视化编辑器 / HTML 编辑）
  - 编辑已有模板
  - 克隆模板
  - 删除模板
  - AI 生成模板 → 编辑器微调 → 保存
  - 预览模板（变量替换）

## U7. Admin：废弃同步功能

- [ ] 7.1 `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx`：
  - 移除 `syncing` 状态和 `syncTemplate` 方法
  - 移除同步按钮（`<RefreshCw>` 图标按钮，约第 245 行）
  - 移除相关 import（`RefreshCw`）
- [ ] 7.2 `backend/app/api/admin/config.py`：移除 `POST /email-templates/{template_id}/sync` 路由
- [ ] 7.3 `backend/app/services/admin_config_service.py`：移除 `sync_platform_email_template` 方法
- [ ] 7.4 移除相关测试：`backend/tests/test_admin_email_template_sync.py`
- [ ] 7.5 验证：Admin 端邮件模板列表页正常，无同步按钮；后端无同步接口

## U8. 后端测试

新建 `backend/tests/test_tenant_email_templates.py`，参考 `test_admin_email_template_sync.py` 的模式。

- [ ] 8.1 `test_list_platform_templates_returns_matching_industry`：按行业筛选返回匹配模板
- [ ] 8.2 `test_list_platform_templates_empty_when_no_match`：无匹配行业返回空列表
- [ ] 8.3 `test_list_platform_templates_excludes_inactive`：排除未启用的模板
- [ ] 8.4 `test_copy_platform_template_success`：正常复制含 body_design
- [ ] 8.5 `test_copy_platform_template_industry_mismatch`：跨行业复制被拒绝
- [ ] 8.6 `test_copy_platform_template_inactive_returns_error`：复制未启用模板报错
- [ ] 8.7 `test_copy_platform_template_not_found`：模板不存在返回 404
- [ ] 8.8 `test_create_template_with_body_design`：创建含 body_design 的模板
- [ ] 8.9 `test_create_template_without_body_design`：创建不含 body_design（向后兼容）
- [ ] 8.10 `test_update_template_body_design`：更新 body_design 字段
- [ ] 8.11 `test_update_template_clear_body_design`：传 null 清空 body_design
- [ ] 8.12 `test_sanitize_skips_html_when_body_design_present`：body_design 存在时跳过 HTML 清洗
- [ ] 8.13 `test_sanitize_applies_html_when_no_body_design`：body_design 不存在时正常清洗
- [ ] 8.14 `test_copy_platform_templates_on_tenant_creation_includes_body_design`：创建租户时复制包含 body_design

## U9. 收尾

- [ ] 9.1 运行后端测试，确认无回归
- [ ] 9.2 运行前端 lint / typecheck，确认无错误
- [ ] 9.3 更新本 change 的任务勾选状态
- [ ] 9.4 调用 `verification-before-completion` skill，输出「原始需求 → 已实现/未实现」对照
