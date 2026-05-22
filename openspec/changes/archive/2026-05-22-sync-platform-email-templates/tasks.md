## 0. 数据库迁移

- [ ] 0.1 新增 Alembic 迁移：创建 partial unique index `ix_email_templates_tenant_platform_active ON email_templates (tenant_id, platform_template_id) WHERE deleted_at IS NULL`，防止并发同步创建重复副本。

## 1. 后端同步能力

- [ ] 1.1 在 Admin 配置路由中新增 `POST /email-templates/{template_id}/sync` 接口，要求平台管理员认证。
- [ ] 1.2 在 Admin 配置服务中实现同步逻辑：读取启用的平台模板、查询同行业 **active** 租户、批量查询已有有效副本（`deleted_at IS NULL`）、为缺失租户循环 INSERT `platform_copy` 副本（`ON CONFLICT DO NOTHING`）。
- [ ] 1.3 同步接口返回完整结果摘要：模板信息、目标租户数、新增数、跳过数、新增明细和跳过明细。
- [ ] 1.4 对未启用或不存在的平台模板返回明确错误，且不创建租户副本。
- [ ] 1.5 为同步动作写入审计记录，记录平台用户、平台模板和同步摘要。

## 2. Admin 前端接入

- [ ] 2.1 在 shared-api 的 Admin 邮件模板 API 中增加同步方法与响应类型。
- [ ] 2.2 在 Admin 邮件模板列表的每行操作中增加同步按钮（点击后直接调用 API，无确认弹窗）。
- [ ] 2.3 同步成功后展示新增/跳过数量摘要（toast），并保持页面可继续操作。
- [ ] 2.4 同步失败时展示错误提示，不误报成功。

## 3. 验证

- [ ] 3.1 增加后端测试：缺失租户被创建副本。
- [ ] 3.2 增加后端测试：已有副本被跳过且内容不被覆盖。
- [ ] 3.3 增加后端测试：重复同步幂等，不创建重复副本。
- [ ] 3.4 增加后端测试：未启用模板不可同步。
- [ ] 3.5 增加后端测试：suspended/archived 租户不参与同步。
- [ ] 3.6 增加后端测试：软删除的副本不阻止新同步（`deleted_at IS NOT NULL` 的副本视为不存在）。
- [ ] 3.7 增加后端测试：并发同步不创建重复副本（依赖 partial unique index）。
- [ ] 3.8 增加后端测试：同步动作写入审计记录。
- [ ] 3.9 增加 Admin 前端契约测试或页面测试：同步按钮/API 封装/结果提示路径可用。
- [ ] 3.10 运行匹配的后端测试、前端测试或 lint；记录无法运行的原因。

## 4. 收尾

- [ ] 4.1 确认迁移只有 partial unique index，且没有修改邮件发送链路。
- [ ] 4.2 更新本 change 的任务勾选状态。
- [ ] 4.3 调用 `verification-before-completion` skill，并输出”原始需求 → 已实现/未实现”对照。
