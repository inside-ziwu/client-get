## 1. 显示优化

- [ ] 1.1 定义角色和状态的中文映射常量（`ROLE_LABELS`、`STATUS_LABELS`），替换表格中角色列和状态列的英文显示
- [ ] 1.2 修改最近登录列，使用 `new Date(iso)` 解析后格式化为 `YYYY-MM-DD HH:mm` 本地时间

## 2. 创建表单增强

- [ ] 2.1 创建表单增加角色下拉选择（管理员/运营/只读），默认选中「运营」，替换硬编码的 `roles: ['operator']`

## 3. 操作列 — 编辑功能

- [ ] 3.1 表格增加「操作」列，当前用户行显示「当前账号」，其他行按三级样式显示操作按钮（编辑=link、禁用=outline、删除=destructive）
- [ ] 3.2 实现编辑弹窗（Dialog），包含姓名输入框和角色 Select 下拉，预填当前值，保存失败在弹窗内展示错误
- [ ] 3.3 接入 `tenantApi.team.update()` mutation，isPending 时禁用保存按钮，成功后 toast.success + 刷新列表 + 关闭弹窗

## 4. 操作列 — 删除功能

- [ ] 4.1 实现删除按钮（destructive 样式）+ AlertDialog 确认对话框
- [ ] 4.2 接入 `tenantApi.team.delete()` mutation，isPending 时禁用确认按钮，成功 toast.success / 失败 toast.error

## 5. 操作列 — 状态切换

- [ ] 5.1 实现「启用/禁用」按钮（outline 样式），根据当前状态显示对应文案
- [ ] 5.2 接入 `tenantApi.team.update()` mutation，isPending 时禁用按钮，成功 toast.success / 失败 toast.error

## 6. 验证

- [ ] 6.1 启动 dev server，手动验证全部 7 项验收标准：编辑保存、删除确认、状态切换、角色中文、状态中文、时间格式、角色选择创建
- [ ] 6.2 验证自保护逻辑：当前账号行不显示编辑/删除/禁用按钮
