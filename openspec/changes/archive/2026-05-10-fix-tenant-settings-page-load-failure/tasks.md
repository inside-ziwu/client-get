## 1. 复现与定位

- [x] 1.1 确认 `frontend/` 子仓库当前分支和工作区状态，避免覆盖无关改动。
- [x] 1.2 运行 Tenant 前端现有检查命令，记录设置页加载失败的编译、类型或运行时错误。
- [x] 1.3 启动 Tenant 本地页面并打开 `/settings`、`/settings/keywords`、`/settings/scoring`、`/settings/ai-provider`、`/settings/team`，定位失败页面、控制台异常和相关网络请求。
- [x] 1.4 判断根因属于路由懒加载、菜单/权限 key、页面状态处理、共享 API 契约还是后端响应不兼容。

## 2. 最小修复

- [x] 2.1 修复导致 Tenant 设置子路由无法渲染的前端问题，范围限定在 layout、router、Settings 页面或共享 hooks/API 的必要文件。
- [x] 2.2 为受影响设置页补齐加载态、空态或错误态，确保接口失败不会导致白屏、未捕获异常或无限加载。
- [x] 2.3 确保 `/settings` 根入口重定向到默认设置子页，或渲染有效设置首页。
- [x] 2.4 如确认根因来自后端设置 API 响应契约不兼容，最小范围修复对应 schema、service 或 route，并保持现有业务语义不变。（未触及后端，判定不适用）
- [x] 2.5 确认修复没有新增设置入口、调整权限模型或改变保存规则。

## 3. 验证

- [x] 3.1 运行 Tenant 前端类型检查、lint 或构建中与本仓库现有脚本匹配的验证命令。
- [x] 3.2 逐一打开 `/settings` 与现有 Tenant 设置子路由，确认页面可渲染、可在子页面间切换且不会白屏。
- [x] 3.3 验证受影响页面在空数据或接口失败时展示可恢复状态。
- [x] 3.4 如修改后端，运行对应后端测试或最小 API smoke 验证。（未修改后端，判定不适用）

## 4. 收尾

- [x] 4.1 更新本 change 的任务勾选状态，明确任何未完成项及原因。
- [x] 4.2 运行 `openspec status --change "fix-tenant-settings-page-load-failure"` 确认 artifacts apply-ready。
- [x] 4.3 运行 `openspec validate "fix-tenant-settings-page-load-failure" --strict` 确认 spec 与 change 格式有效。
- [x] 4.4 汇报前调用 `verification-before-completion` skill，并输出原始需求到实现结果的对照清单。
