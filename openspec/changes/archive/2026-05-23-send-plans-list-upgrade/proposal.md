## Why

发送计划列表页目前只有新建和查看能力，缺少筛选、编辑、删除。随着计划数量增多，无法快速定位目标；草稿无法修改只能重建；已结束计划无法清理；时间精度不够；进度条信息价值低。

## What Changes

- 列表顶部增加三维筛选：状态下拉、名称搜索、日期范围
- 列表增加分页
- 每行末尾增加操作菜单（「...」），按状态动态展示可用操作：
  - 草稿：查看详情、编辑、删除
  - 已完成/已取消：查看详情、删除
  - 已排期/执行中/已暂停：仅查看详情
- 点击行本身进入详情页
- 编辑草稿跳转到向导页面并预填数据（复用新建向导）
- 删除操作增加二次确认弹窗
- 创建时间显示日期+时间（如 2026-05-22 14:30）
- 移除进度条列

## Non-Goals

- 批量操作（批量删除、批量取消）
- 列头点击排序
- 导出功能

## Capabilities

### New Capabilities

- `send-plan-list-filter`: 列表三维筛选（状态 + 名称搜索 + 日期范围）
- `send-plan-list-actions`: 行末操作菜单（按状态动态展示编辑/删除）
- `send-plan-list-pagination`: 列表分页
- `send-plan-edit-wizard`: 编辑草稿计划（复用向导页预填数据）

### Modified Capabilities

- `send-plan-list-display`: 时间列格式改为日期+时间，移除进度条列

## Key Decisions (eng-review D1-D7)

- D1: 编辑草稿通过后端新增 `complete-update` 端点原子替换 plan+steps+recipients，与 `complete-create` 对称
- D2: 后端 PATCH/DELETE/complete-update 强制检查 plan 状态，不符合则 403
- D3: 分页采用 page/page_size 模式（与 companies 页面一致），非 cursor
- D5: scheduled 状态与 running/paused 同级，操作菜单仅允许查看详情；筛选下拉新增「已排期」选项
- D6: 编辑草稿时收件人步骤预填 recipient_config（来源配置），而非已锁定的具体收件人列表
- D7: 技术改进全部纳入——缓存键统一、complete-update 加 FOR UPDATE 锁、分页 COUNT(*) 单独查询、日期范围 date_to 包含当天

## Impact

| 路径 | 变更类型 | 说明 |
|------|---------|------|
| `frontend/apps/tenant/src/app/(dashboard)/send-plans/page.tsx` | 修改 | 列表页增加筛选、操作菜单、分页、时间格式、移除进度条 |
| `frontend/apps/tenant/src/app/(dashboard)/send-plans/new/page.tsx` | 修改 | 向导支持编辑模式（加载现有计划数据预填） |
| `frontend/apps/tenant/src/app/(dashboard)/send-plans/[id]/edit/page.tsx` | 新增 | 编辑路由，加载现有数据后渲染向导 |
| `frontend/packages/shared-types/src/api.ts` | 修改 | PlanFilters 增加 date_from/date_to/page/page_size |
| `backend/app/api/tenant/messaging.py` | 修改 | 列表接口增加筛选+分页参数；新增 complete-update 端点 |
| `backend/app/services/tenant_messaging_service.py` | 修改 | 列表查询增加筛选条件；新增 complete_update 方法；PATCH/DELETE 增加状态检查 |
