## 1. 数据库迁移

- [ ] 1.1 Alembic 迁移：`domain_warmup_status` 表新增 `sender_email varchar(255)` 可空字段

## 2. 后端 — Admin 域名 API

- [ ] 2.1 `create_tenant_domain` 服务方法支持 `sender_email` 参数写入
- [ ] 2.2 新增 `update_tenant_domain` 服务方法：更新 `sender_email`、`warmup_rule_id`、`warmup_level`（暖机变更时重算 `daily_limit`，并记录 `warmup_history`）
- [ ] 2.3 新增 `delete_tenant_domain` 服务方法：检查 `domain_daily_usage` 和 `sending_plans` 是否有任何记录引用该 domain_id，有则返回 409（任何 FK 关联都禁止删除）
- [ ] 2.4 路由层新增 `PATCH /tenants/{tenant_id}/domains/{domain_id}` 端点
- [ ] 2.5 路由层新增 `DELETE /tenants/{tenant_id}/domains/{domain_id}` 端点
- [ ] 2.6 `list_tenant_domains` 和 `get_tenant_domain` 查询结果确认包含 `sender_email` 字段

## 3. 后端 — Tenant API

- [ ] 3.1 tenant 端 `list_domains` 查询结果确认包含 `sender_email` 字段
- [ ] 3.2 `/me` 端点响应新增 `tenant_name` 字段（从 `tenants.name` 读取）
- [ ] 3.3 `TenantMeResponse` schema 和前端 `CurrentUser` 类型新增 `tenant_name`

## 4. Admin 前端 — 域名管理增强

- [ ] 4.1 `TenantDomain` 类型新增 `sender_email` 字段
- [ ] 4.2 域名添加表单新增发件邮箱输入框
- [ ] 4.3 `createDomain` API 方法参数新增 `sender_email`
- [ ] 4.4 域名列表表格新增"发件邮箱"列
- [ ] 4.5 域名行操作新增"编辑"按钮，弹出编辑表单（发件邮箱 + 暖机配置，域名只读）
- [ ] 4.6 新增 `updateDomain` API 方法（PATCH）
- [ ] 4.7 域名行操作新增"删除"按钮，确认弹窗后调用 DELETE，处理 409 错误提示
- [ ] 4.8 新增 `deleteDomain` API 方法（DELETE）

## 5. Tenant 前端 — 新建计划默认值

- [ ] 5.1 `TenantDomainInfo` 类型新增 `sender_email` 字段
- [ ] 5.2 改造 `new/page.tsx`：预加载 `/me`（获取 `tenant_name`）和 verified 域名列表，构造 `initialData` 传入向导（与 edit/page.tsx 模式对称）
- [ ] 5.3 `initialData` 构造逻辑：`sender_name` 取 `tenant_name`，`domain_id` 取 verified 域名按 `created_at` 升序第一个，`sender_email` 取选中域名的 `sender_email`（无则留空）
- [ ] 5.5 `StepBasicInfo` 域名下拉 `onValueChange` 增加联动逻辑：切换域名时自动更新 `sender_email`

## 6. 后端测试

- [ ] 6.1 `test_domain_crud_routes.py`：PATCH/DELETE 路由级测试（正常更新、无效暖机、域名不存在、FK 引用 409）
- [ ] 6.2 `test_domain_crud_service.py`：服务层逻辑测试（sender_email 写入、暖机重算+history、FK 检查、domain 字段忽略）
- [ ] 6.3 `test_tenant_me.py`：/me 端点返回 tenant_name

## 7. 验证

- [ ] 7.1 后端验证：创建域名传入 sender_email 后查询确认写入
- [ ] 7.2 后端验证：PATCH 域名修改 sender_email 和暖机配置，确认 daily_limit 重算 + warmup_history 记录
- [ ] 7.3 后端验证：DELETE 域名时有任何 FK 引用返回 409，无引用正常删除
- [ ] 6.4 Admin 前端验证：添加、编辑、删除域名功能完整
- [ ] 6.5 Tenant 前端验证：新建计划时三个字段默认值正确填入
- [ ] 6.6 Tenant 前端验证：切换域名时发件邮箱联动更新
- [ ] 6.7 Tenant 前端验证：编辑已有 draft 计划时默认值不覆盖已有数据
