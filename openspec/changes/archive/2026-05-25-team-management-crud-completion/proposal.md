## Why

租户端团队管理页面目前只实现了「创建」和「列表」，编辑、删除、状态切换等操作缺失，管理员无法修改成员角色或移除离职人员。同时角色（admin/operator/viewer）和状态（active/disabled）以英文原值展示，最近登录只显示日期不含时间，体验不完整。后端 CRUD 四个接口和前端 API 客户端均已就绪，只需补齐前端 UI。

## What Changes

- 表格增加「操作」列：编辑（弹窗修改姓名/角色）、删除（确认对话框）、启用/禁用切换
- 当前登录账号的操作按钮做自保护（不允许编辑自身角色、删除自身、禁用自身）
- 角色列中文化：admin→管理员、operator→运营、viewer→只读
- 状态列中文化：active→已激活、disabled→已禁用
- 最近登录格式改为 `YYYY-MM-DD HH:mm`
- 创建表单增加角色下拉选择，默认「运营」，替换硬编码

## Capabilities

### New Capabilities

- `team-member-crud-ui`: 团队成员的编辑弹窗、删除确认、状态切换等前端交互，以及角色/状态中文化和时间格式优化

### Modified Capabilities

无。后端接口无变更，前端 API 客户端已封装好 update/delete 方法。

## Impact

| 维度 | 影响 |
|------|------|
| 前端代码 | `frontend/apps/tenant/src/app/(dashboard)/settings/team/page.tsx` — 主要改动文件 |
| 后端代码 | 无改动 |
| 数据库 | 无改动 |
| API 接口 | 无改动（使用已有 PATCH/DELETE 接口） |
| 依赖 | 无新增依赖 |

## Non-Goals

- 不改后端接口（已完备）
- 不改表格整体布局和列结构
- 不加角色权限说明卡片
- 不加用户头像
- 不做批量操作
