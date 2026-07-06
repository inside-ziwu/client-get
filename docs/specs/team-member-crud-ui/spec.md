# team-member-crud-ui Specification

## Purpose
TBD - created by archiving change team-management-crud-completion. Update Purpose after archive.
## Requirements
### Requirement: 系统 SHALL 允许管理员编辑团队成员

管理员 SHALL 能够通过编辑弹窗修改团队成员的姓名和角色。角色选项为：管理员、运营、只读。系统 MUST 禁止用户编辑自己的角色。

#### Scenario: 成功编辑成员

- **GIVEN** 管理员已登录并在团队管理页面
- **WHEN** 管理员点击某成员行的「编辑」按钮
- **THEN** 弹出编辑弹窗，预填该成员当前姓名和角色
- **WHEN** 管理员修改姓名或角色后点击「保存」
- **THEN** 系统调用 `PATCH /api/v1/team/users/{id}` 提交变更，成功后列表刷新并显示更新值

#### Scenario: 不允许编辑自身角色

- **GIVEN** 管理员已登录
- **WHEN** 管理员查看自己所在行
- **THEN** 该行操作列显示「当前账号」标识，不显示编辑/删除/禁用按钮

### Requirement: 系统 SHALL 允许管理员删除团队成员

管理员 SHALL 能够删除其他团队成员。系统 MUST 在删除前弹出确认对话框。系统 MUST 禁止用户删除自己。

#### Scenario: 成功删除成员

- **GIVEN** 管理员已登录并在团队管理页面
- **WHEN** 管理员点击某成员行的「删除」按钮
- **THEN** 弹出确认对话框，显示确认文案
- **WHEN** 管理员确认删除
- **THEN** 系统调用 `DELETE /api/v1/team/users/{id}`，成功后列表刷新，该成员从列表中移除

#### Scenario: 取消删除

- **GIVEN** 删除确认对话框已打开
- **WHEN** 管理员点击「取消」
- **THEN** 对话框关闭，不执行删除操作

### Requirement: 系统 SHALL 允许管理员切换成员启用/禁用状态

管理员 SHALL 能够启用或禁用其他团队成员。系统 MUST 禁止用户禁用自己。

#### Scenario: 禁用已激活成员

- **GIVEN** 某成员状态为「已激活」
- **WHEN** 管理员点击该成员行的「禁用」按钮
- **THEN** 系统调用 `PATCH /api/v1/team/users/{id}` 提交 `{ status: 'disabled' }`，成功后列表刷新，该成员状态变为「已禁用」

#### Scenario: 启用已禁用成员

- **GIVEN** 某成员状态为「已禁用」
- **WHEN** 管理员点击该成员行的「启用」按钮
- **THEN** 系统调用 `PATCH /api/v1/team/users/{id}` 提交 `{ status: 'active' }`，成功后列表刷新，该成员状态变为「已激活」

### Requirement: 系统 SHALL 以中文显示角色名称

角色列 MUST 按以下映射显示中文：
- `admin` → 管理员
- `operator` → 运营
- `viewer` → 只读

#### Scenario: 角色中文显示

- **GIVEN** 成员列表已加载
- **WHEN** 某成员角色为 `admin`
- **THEN** 角色列显示「管理员」

#### Scenario: 多角色显示

- **GIVEN** 某成员拥有多个角色
- **WHEN** 列表渲染该成员
- **THEN** 角色列以中文逗号分隔显示所有角色（如「管理员、运营」）

### Requirement: 系统 SHALL 以中文显示成员状态

状态列 MUST 按以下映射显示中文：
- `active` → 已激活
- `disabled` → 已禁用

#### Scenario: 状态中文显示

- **GIVEN** 成员列表已加载
- **WHEN** 某成员状态为 `active`
- **THEN** 状态列显示「已激活」

### Requirement: 系统 SHALL 以日期+时间格式显示最近登录

最近登录列 MUST 显示格式为 `YYYY-MM-DD HH:mm` 的本地时间。未登录过的成员显示 `-`。

#### Scenario: 有登录记录

- **GIVEN** 某成员 `last_login_at` 为 `2026-05-23T14:30:00+08:00`
- **WHEN** 列表渲染该成员
- **THEN** 最近登录列显示 `2026-05-23 14:30`

#### Scenario: 无登录记录

- **GIVEN** 某成员 `last_login_at` 为 null
- **WHEN** 列表渲染该成员
- **THEN** 最近登录列显示 `-`

### Requirement: 创建表单 SHALL 支持角色选择

创建成员表单 MUST 包含角色下拉选择，选项为：管理员、运营、只读。默认选中「运营」。

#### Scenario: 使用默认角色创建

- **GIVEN** 管理员打开创建表单
- **WHEN** 仅填写姓名和邮箱后点击「邀请/创建」
- **THEN** 系统以 `roles: ['operator']` 创建成员

#### Scenario: 选择管理员角色创建

- **GIVEN** 管理员打开创建表单
- **WHEN** 选择角色为「管理员」并填写姓名和邮箱后提交
- **THEN** 系统以 `roles: ['admin']` 创建成员

