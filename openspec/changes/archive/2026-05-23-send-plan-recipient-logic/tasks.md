## 1. 后端：修改收件人选取逻辑

- [x] 1.0 **前置检查**：查询生产数据确认是否存在 `tenant_contacts.is_sendable = false` 的记录，评估是否需要兼顾该字段
- [x] 1.1 修改 `_recipients_from_group()` SQL：LEFT JOIN `v_tenant_contact_classified` 和 `position_classification_levels`，排除过滤（blacklist、unsubscribed、bounced、is_sendable=false、无邮箱）在 SQL 层面 ROW_NUMBER 之前完成，按 `(tenant_company_id, email)` 去重保留最高等级记录，添加 `ROW_NUMBER() OVER (PARTITION BY tenant_company_id ORDER BY is_sendable DESC NULLS LAST, sort_order DESC NULLS LAST, shc.id ASC)` 窗口函数，外层 WHERE 筛选 `rn <= 8`
- [x] 1.2 将返回行的 `is_sendable` 字段改为取自 `position_classification_levels.is_sendable`（COALESCE 为 true），同时返回 `level_display_name` 字段供前端展示

## 2. 后端：新增预览 API

- [x] 2.1 在 `tenant_messaging_service` 新增 `preview_recipients_for_group(conn, tenant_id, group_id)` 方法：调用 `_build_recipient_candidates()` 获取候选人，按 `tenant_company_id` 分组，返回 `{ companies: [...], summary: { company_count, recipient_count } }` 结构
- [x] 2.2 在 `backend/app/api/tenant/messaging.py` 新增路由 `GET /api/v1/send-plans/preview-recipients`，接收 `group_id` 查询参数，调用上述方法并返回结果

## 3. 前端：群组显示和预览更新

- [x] 3.1 `step-recipients.tsx`：群组选择器下拉项文本从 `{g.member_count} 人` 改为 `{g.member_count} 家公司`
- [x] 3.2 `step-recipients.tsx`：收件人预览改为调用新的 `preview-recipients` API，替换当前的 `listMembers` 调用
- [x] 3.3 `step-recipients.tsx`：预览表格改为按公司汇总展示（每公司一行，显示公司名和收件人数量），支持展开查看明细（联系人姓名、邮箱、分类等级）
- [x] 3.4 `step-recipients.tsx`：底部合计改为"合计 X 家公司，Y 位收件人"
- [x] 3.5 `step-confirmation.tsx`：确认步骤"预估收件人数"显示改为使用新 API 的 summary 数据
- [x] 3.6 在 `frontend/packages/shared-api/` 中添加 `preview-recipients` API 类型定义和调用方法

## 4. 后端测试

- [x] 4.1 为 `_recipients_from_group()` 编写测试：验证混合等级排序（A > B > 未分类）、X 级排除、每公司 8 人上限、邮箱去重
- [x] 4.2 为 `preview_recipients_for_group()` 编写测试：验证按公司分组返回、summary 统计正确
- [x] 4.3 边界场景测试：全部未分类联系人、无有效联系人的公司、超过 8 人的公司、同一邮箱多条记录

## 5. 验证

- [ ] 5.1 后端验证：手动测试 `preview-recipients` API，确认返回按公司分组、按等级排序、每公司上限 8 人
- [ ] 5.2 前端验证：启动 dev server，创建发送计划走到收件人步骤，确认群组显示"X 家公司"、预览按公司汇总、合计正确
- [ ] 5.3 边界验证：测试全部未分类联系人的公司、无有效联系人的公司、超过 8 人的公司三种场景

> 注：5.1-5.3 为用户手动验证步骤，需启动 dev server 后操作
